"""
AI Code Reviewer - AST 上下文压缩模块

核心价值：将完整文件 diff 压缩为"只包含变更函数/类的代码片段"，
大幅减少传给 LLM 的 token 数量（预期降低 50-65%）。

这是整个项目中最具技术深度的模块——面试金句：
"基于 AST 的变更影响分析，只提取变更函数上下文而非完整文件"

核心函数:
    extract_function_context(source_code, changed_lines) -> str
    compress_diff_with_ast(diff_content, source_code, file_path) -> str
"""

import ast
import logging
import re
from typing import Optional

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────
#  核心提取函数
# ──────────────────────────────────────────────

def extract_function_context(
    source_code: str,
    changed_lines: set[int],
    context_lines: int = 3,
) -> str:
    """
    从源代码中提取包含变更行的函数/类定义。

    这是 AST 压缩的核心函数：
    1. 解析源代码为 AST
    2. 找到所有包含变更行的函数/类定义
    3. 提取其完整源代码（含装饰器、注释、docstring）
    4. 在变更行上标注 `# <-- CHANGED` 标记

    如果 ast.parse 失败（语法错误、Python 3.10+ 联合类型等），
    自动降级为行范围提取（变更行 ±context_lines 行）。

    Args:
        source_code: 完整源代码字符串
        changed_lines: 变更行的行号集合（1-indexed）
        context_lines: 降级时保留的上下文行数

    Returns:
        提取后的代码片段（带标记）
    """
    if not source_code or not source_code.strip():
        return ""
    if not changed_lines:
        return ""

    source_lines = source_code.splitlines()
    max_line = len(source_lines)

    # 过滤掉超出文件范围的行号
    changed_lines = {ln for ln in changed_lines if 1 <= ln <= max_line}
    if not changed_lines:
        return ""

    # 尝试 AST 解析
    try:
        tree = ast.parse(source_code)
    except SyntaxError as e:
        logger.warning("ast.parse 失败 (%s)，降级为行范围提取", e)
        return _fallback_extract(source_lines, changed_lines, context_lines)

    # 找到所有变更行所属的顶层定义
    enclosing_nodes = _find_enclosing_definitions(tree, changed_lines)

    if not enclosing_nodes:
        logger.info("变更行不在任何函数/类定义中，降级为行范围提取")
        return _fallback_extract(source_lines, changed_lines, context_lines)

    # 提取每个定义的源代码并标注变更行
    fragments = []
    for node in enclosing_nodes:
        fragment = _extract_node_with_markers(
            source_lines, node, changed_lines, context_lines,
        )
        if fragment:
            fragments.append(fragment)

    result = "\n\n".join(fragments)

    logger.info(
        "AST 提取完成: %d 个定义, %d 行 -> %d 行",
        len(enclosing_nodes),
        len(source_lines),
        len(result.splitlines()),
    )

    return result


# ──────────────────────────────────────────────
#  AST 遍历与匹配
# ──────────────────────────────────────────────

def _find_enclosing_definitions(
    tree: ast.AST,
    changed_lines: set[int],
) -> list[ast.AST]:
    """
    找到所有包含变更行的顶层定义节点。

    规则:
    - 对于类中的方法变更，返回整个 ClassDef（而非单个方法）
    - 对于顶层函数变更，返回 FunctionDef
    - 多个变更行可能对应同一个定义，自动去重
    """
    # Step 1: 收集所有 FunctionDef 和 AsyncFunctionDef
    # 注意它们的父节点是否是 ClassDef
    candidates: list[ast.AST] = []

    # 用 walk 遍历全树，但我们只对**顶层**定义感兴趣
    # 对于类中的函数，我们返回类，而不是函数
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            # 顶层函数
            if _node_contains_any(node, changed_lines):
                candidates.append(node)
        elif isinstance(node, ast.ClassDef):
            # 类定义：检查类或其方法是否包含变更行
            if _node_contains_any(node, changed_lines):
                candidates.append(node)

    return candidates


def _node_contains_any(node: ast.AST, changed_lines: set[int]) -> bool:
    """检查 AST 节点是否包含任意一个变更行。"""
    if not hasattr(node, "lineno") or not hasattr(node, "end_lineno"):
        return False
    start = node.lineno
    end = node.end_lineno if node.end_lineno is not None else node.lineno
    for ln in changed_lines:
        if start <= ln <= end:
            return True
    return False


# ──────────────────────────────────────────────
#  源代码提取与标注
# ──────────────────────────────────────────────

def _extract_node_with_markers(
    source_lines: list[str],
    node: ast.AST,
    changed_lines: set[int],
    context_lines: int,
) -> str:
    """
    提取 AST 节点的源代码，并在变更行上添加标记。

    使用 ast.get_source_segment 确保保留完整的原始格式
    （装饰器、注释、docstring 等不会被丢失）。
    """
    # 1-indexed from AST — 包含装饰器行
    start = node.lineno
    if hasattr(node, "decorator_list") and node.decorator_list:
        start = min(d.lineno for d in node.decorator_list)
    end = node.end_lineno if node.end_lineno is not None else \
        _find_end_by_indent(source_lines, start - 1)

    if end is None or end < start:
        end = start

    # 确保不超出文件范围
    end = min(end, len(source_lines))

    # 提取代码行
    code_lines = source_lines[start - 1:end]  # 转为 0-indexed

    # 构建节点类型标签
    node_type = _get_node_label(node)
    name = node.name if hasattr(node, "name") else ""
    location = f"第 {start}-{end} 行"
    header = f"# === [{node_type}] {name} ({location}) ==="

    # 标注变更行
    marked = []
    for i, line in enumerate(code_lines):
        abs_line = start + i  # 1-indexed 绝对行号
        if abs_line in changed_lines:
            marked.append(f"{line}  # <-- CHANGED")
        else:
            marked.append(line)

    return header + "\n" + "\n".join(marked)


def _get_node_label(node: ast.AST) -> str:
    """获取节点的中文标签。"""
    if isinstance(node, ast.ClassDef):
        return "类定义"
    elif isinstance(node, ast.AsyncFunctionDef):
        return "异步函数"
    elif isinstance(node, ast.FunctionDef):
        return "函数"
    return type(node).__name__


# ──────────────────────────────────────────────
#  缩进回退算法（end_lineno 为 None 时的 Plan B）
# ──────────────────────────────────────────────

def _find_end_by_indent(lines: list[str], start_idx: int) -> Optional[int]:
    """
    通过缩进匹配找到函数/类定义的结束行。

    从定义行开始，逐行向下查找，直到遇到缩进回到定义层级的行。
    用于 end_lineno 为 None 的防御性编程。
    """
    if start_idx < 0 or start_idx >= len(lines):
        return None

    def_line = lines[start_idx]
    # 定义行的缩进（装饰器可能在上一行，函数自身缩进为基准）
    base_indent = len(def_line) - len(def_line.lstrip())

    # 从定义行的下一行开始扫描
    for i in range(start_idx + 1, len(lines)):
        line = lines[i]
        stripped = line.rstrip()

        # 跳过空行
        if not stripped:
            continue

        # 跳过纯注释行（它们属于当前定义）
        if stripped.lstrip().startswith("#"):
            continue

        # 当前行缩进
        indent = len(line) - len(line.lstrip())

        # 如果缩进回到 <= 定义层级，且不是装饰器，则结束
        if indent <= base_indent and not line.lstrip().startswith("@"):
            return i  # 返回结束行（独占式，不包含此缩进行）

    # 没找到 → 文件末尾
    return len(lines)


# ──────────────────────────────────────────────
#  降级方案：行范围提取
# ──────────────────────────────────────────────

def _fallback_extract(
    source_lines: list[str],
    changed_lines: set[int],
    context_lines: int,
) -> str:
    """
    当 AST 解析失败时，降级为基于行号的上下文提取。

    在变更行周围 ±context_lines 行范围内提取代码。
    这是 Plan B，不如 AST 提取精确，但确保管线不会中断。
    """
    total = len(source_lines)

    # 对每个变更行展开 ±context_lines，然后合并重叠区间
    intervals = []
    for ln in changed_lines:
        start = max(1, ln - context_lines)
        end = min(total, ln + context_lines)
        intervals.append((start, end))

    # 合并重叠/相邻区间
    intervals.sort()
    merged = []
    for start, end in intervals:
        if merged and start <= merged[-1][1] + 1:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))

    # 提取代码
    fragments = []
    for start, end in merged:
        lines = source_lines[start - 1:end]
        # 标注变更行
        marked = []
        for i, line in enumerate(lines):
            abs_line = start + i
            if abs_line in changed_lines:
                marked.append(f"{line}  # <-- CHANGED")
            else:
                marked.append(line)

        header = f"# === [降级提取] 第 {start}-{end} 行 ==="
        fragments.append(header + "\n" + "\n".join(marked))

    return "\n\n".join(fragments)


# ──────────────────────────────────────────────
#  从 Diff 中提取目标文件源码
# ──────────────────────────────────────────────

def reconstruct_target_source(
    source_lines_before: list[str],
    hunks_data: list[dict],
) -> tuple[list[str], set[int]]:
    """
    从原始文件源码和 hunks 数据重建变更后的源码，并返回变更行号。

    这是将 diff 解析和 AST 提取串联的关键函数。
    在无法直接获取目标文件时，用此方法重建。

    Args:
        source_lines_before: 变更前的文件源码（按行分割）
        hunks_data: 来自 diff_parser 的 hunks 列表，
                    每项含 source_start, source_len, target_start, target_len, content

    Returns:
        (target_lines, changed_line_numbers)
        target_lines: 变更后的完整源码（按行）
        changed_line_numbers: 发生变更的行号集合（1-indexed）
    """
    # 解析 hunk 内容获取每行的变更类型
    target_lines: list[str] = []
    changed_lines: set[int] = set()

    # 从第一行开始构建
    # 先把 source_lines_before 转为列表
    source_idx = 0  # 0-indexed

    for hunk in hunks_data:
        content = hunk["content"]
        source_start = hunk["source_start"]
        target_start = hunk["target_start"]

        # 从 source_start 往前添加未变更的行
        while source_idx < source_start - 1:
            target_lines.append(source_lines_before[source_idx])
            source_idx += 1

        # 解析 hunk 内容
        hunk_lines = content.splitlines()[1:]  # 跳过 @@ 头

        target_line_num = target_start
        source_line_num = source_start

        for hunk_line in hunk_lines:
            if not hunk_line:
                continue
            marker = hunk_line[0]

            if marker == " ":
                # 上下文行：两侧都有
                target_lines.append(hunk_line[1:])
                source_idx += 1
                target_line_num += 1
                source_line_num += 1

            elif marker == "-":
                # 删除行：只在 source 中有
                source_idx += 1
                source_line_num += 1

            elif marker == "+":
                # 新增行：只在 target 中有
                target_lines.append(hunk_line[1:])
                changed_lines.add(target_line_num)
                target_line_num += 1

        # hunk 处理完后继续

    # 添加剩余行
    while source_idx < len(source_lines_before):
        target_lines.append(source_lines_before[source_idx])
        source_idx += 1

    return target_lines, changed_lines


# ──────────────────────────────────────────────
#  管线集成便利函数
# ──────────────────────────────────────────────

def compress_diff_with_ast(
    source_code: str,
    changed_lines: set[int],
    context_lines: int = 3,
) -> str:
    """
    高层便利函数：用 AST 压缩 diff 内容。

    这是 Day 10-12 集成到 review_pipeline 时调用的入口。

    Args:
        source_code: 变更后的文件源码
        changed_lines: 变更行的行号集合（1-indexed）
        context_lines: 降级时保留的上下文行数

    Returns:
        压缩后的代码片段
    """
    ast_result = extract_function_context(source_code, changed_lines, context_lines)

    if ast_result:
        return ast_result

    # AST 提取为空 → 返回变更行附近的上下文
    source_lines = source_code.splitlines()
    return _fallback_extract(source_lines, changed_lines, context_lines)


# ──────────────────────────────────────────────
#  文件级上下文注入（减少 AST 压缩截断导致的误报）
# ──────────────────────────────────────────────

_INJECTION_HEADER = "\n# === Injected File-Level Context (auto) ===\n"
_INJECTION_FOOTER = "\n# === End Injected Context ===\n\n"


def inject_python_context(compressed: str, full_source: str) -> str:
    """向 Python 压缩结果注入文件级 import 和全局变量声明。

    Args:
        compressed: AST 压缩后的代码片段
        full_source: 重建后的完整源码

    Returns:
        注入了文件级声明的压缩结果
    """
    if not full_source or not full_source.strip():
        return compressed

    lines = full_source.split("\n")
    import_lines = []
    global_lines = []

    for line in lines:
        stripped = line.strip()
        if stripped.startswith(("import ", "from ")):
            import_lines.append(line)
        elif import_lines and stripped and not stripped.startswith("#"):
            break  # import 块结束

    # 全局常量/变量赋值（在 import 之后、class/def 之前）
    in_top_level = not import_lines or True
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.startswith(("import ", "from ")):
            continue
        if stripped.startswith(("def ", "class ", "async def ", "@")):
            break
        # 顶层赋值语句（如 API_KEY = "...", _cache = {}）
        if "=" in stripped and not stripped.startswith(("if ", "for ", "while ", "try:", "except")):
            global_lines.append(line)

    injected = []
    if import_lines:
        injected.append("\n".join(import_lines))
    if global_lines:
        injected.append("\n".join(global_lines))

    if not injected:
        return compressed

    return _INJECTION_HEADER + "\n".join(injected) + _INJECTION_FOOTER + compressed


def build_python_local_call_graph(full_source: str) -> dict:
    """分析 Python 文件同文件内的函数调用关系。

    Args:
        full_source: 完整源码

    Returns:
        {"exports": [func_name], "edges": [{"caller": "foo", "callee": "bar", "line": 42}]}
    """
    try:
        tree = ast.parse(full_source)
    except SyntaxError:
        return {"exports": [], "edges": []}

    # 收集顶层函数/类
    exports = []
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            exports.append(node.name)

    # 收集所有调用
    edges = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            call_name = _get_call_name(node)
            if not call_name:
                continue
            line = getattr(node, "lineno", 0)

            # 找到包含此调用的顶层函数
            caller = _find_enclosing_function(tree, node.lineno)
            if caller and call_name in exports and call_name != caller:
                edges.append({
                    "caller": caller,
                    "callee": call_name,
                    "line": line,
                })

    return {"exports": exports, "edges": edges}


def _get_call_name(call_node: ast.Call) -> str:
    """从 ast.Call 节点提取被调用的函数名."""
    func = call_node.func
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return ""


def _find_enclosing_function(tree: ast.AST, lineno: int) -> str:
    """找到包含指定行号的顶层函数/类名."""
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            if hasattr(node, "lineno") and hasattr(node, "end_lineno"):
                if node.lineno <= lineno <= node.end_lineno:
                    return node.name
    return ""


def inject_python_local_call_graph(
    compressed: str,
    full_source: str,
    changed_function_names: list[str],
) -> str:
    """向 Python 压缩结果注入同文件调用关系."""
    if not changed_function_names:
        return compressed

    call_graph = build_python_local_call_graph(full_source)
    edges = call_graph.get("edges", [])

    if not edges:
        return compressed

    changed_set = set(changed_function_names)

    callers = []
    callees = []
    seen_callers = set()
    seen_callees = set()

    for edge in edges:
        caller = edge.get("caller", "")
        callee = edge.get("callee", "")
        line = edge.get("line", 0)

        if callee in changed_set and caller not in seen_callers:
            callers.append((caller, line))
            seen_callers.add(caller)
        if caller in changed_set and callee not in seen_callees:
            callees.append((callee, line))
            seen_callees.add(callee)

    if not callers and not callees:
        return compressed

    parts = []
    _LOCAL_CALL_HEADER = (
        "\n\n---- 8< ----\n"
        "[Local Call Graph: 同文件调用关系（由 AST 分析自动生成）]\n"
    )
    _LOCAL_CALL_FOOTER = "\n---- 8< ----\n"

    if callers:
        cs = [f"{c}()(第 {l} 行)" for c, l in callers[:5]]
        parts.append(f"  → 被同文件调用: {', '.join(cs)}")
    if callees:
        cs = [f"{c}()(第 {l} 行)" for c, l in callees[:5]]
        parts.append(f"  → 调用了同文件函数: {', '.join(cs)}")

    return compressed.rstrip() + _LOCAL_CALL_HEADER + "\n".join(parts) + _LOCAL_CALL_FOOTER


# ──────────────────────────────────────────────
#  CLI 测试入口
# ──────────────────────────────────────────────

if __name__ == "__main__":
    import argparse

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    parser = argparse.ArgumentParser(description="AST 上下文压缩测试")
    parser.add_argument("--file", required=True, help="Python 源代码文件路径")
    parser.add_argument("--lines", required=True, help="变更行号（逗号分隔，如 10,15,20-25）")
    args = parser.parse_args()

    # 解析行号
    changed = set()
    for part in args.lines.split(","):
        part = part.strip()
        if "-" in part:
            a, b = part.split("-")
            changed.update(range(int(a), int(b) + 1))
        else:
            changed.add(int(part))

    with open(args.file, "r", encoding="utf-8") as f:
        source = f.read()

    print(f"源文件: {args.file} ({len(source.splitlines())} 行)")
    print(f"变更行: {sorted(changed)}")
    print(f"\n{'='*60}")
    print("AST 压缩结果:")
    print(f"{'='*60}")

    result = extract_function_context(source, changed)

    if result:
        print(result)
        original_tokens = len(source.split())
        compressed_tokens = len(result.split())
        ratio = (1 - compressed_tokens / original_tokens) * 100 if original_tokens else 0
        print(f"\n--- Token 对比 ---")
        print(f"  原始:    {original_tokens} tokens")
        print(f"  压缩后:  {compressed_tokens} tokens")
        print(f"  压缩率:  {ratio:.1f}%")
    else:
        print("  (未提取到内容)")
