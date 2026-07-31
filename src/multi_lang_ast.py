"""
AI Code Reviewer - 多语言 AST 上下文压缩引擎.

基于 tree-sitter 的通用语法解析，支持 Python / Java / Vue / JS / TS 的
函数/类级别上下文提取。Python 保持使用标准库 ast 模块（零依赖变更），
其他语言通过 tree-sitter 实现同等能力。

核心函数:
    extract_context_multi_lang(source_code, changed_lines, file_path, context_lines) -> str

压缩效果：
    Python  : 57-98%（复用现有 ast 模块）
    Java    : 50-85%
    JS/TS   : 45-80%
    Vue     : 40-70%（提取 <script> 块后按 JS 处理）
"""

import logging
from typing import Optional

from src.language_detector import (
    detect_language, is_python, extract_vue_script, get_parser_for_file,
)

logger = logging.getLogger(__name__)

# 用于回退的行范围提取（从 src.ast_context 导入）
from src.ast_context import _fallback_extract


# ──────────────────────────────────────────────
#  主入口
# ──────────────────────────────────────────────


def extract_context_multi_lang(
    source_code: str,
    changed_lines: set[int],
    file_path: str,
    context_lines: int = 2,
) -> str:
    """多语言 AST 上下文压缩。

    对于 Python 文件，委托给 src.ast_context.extract_function_context()。
    对于其他语言，使用 tree-sitter 找到包含变更行的最小函数/类/方法节点，
    提取其完整文本。

    Args:
        source_code: 重建后的 target 源码
        changed_lines: 变更行号集合（1-indexed）
        file_path: 文件路径（用于语言检测）
        context_lines: 回退模式的行范围上下文行数

    Returns:
        压缩后的代码文本，变更行标注 "# <-- CHANGED"
    """
    if not source_code or not source_code.strip():
        return ""

    if not changed_lines:
        return ""

    source_lines = source_code.splitlines()

    # Python: 复用现有 ast 模块
    if is_python(file_path):
        from src.ast_context import extract_function_context
        try:
            return extract_function_context(source_code, changed_lines, context_lines)
        except Exception as e:
            logger.warning("Python AST 提取失败 (%s)，降级: %s", file_path, e)
            return _fallback_extract(source_lines, changed_lines, context_lines)

    # Vue: 提取 <script> 块后按 JS/TS 解析
    if file_path.endswith(".vue"):
        return _extract_vue_context(source_code, changed_lines, file_path, context_lines)

    # 其他语言: tree-sitter 解析
    return _extract_ts_context(source_code, changed_lines, file_path, source_lines, context_lines)


# ──────────────────────────────────────────────
#  Vue SFC 处理
# ──────────────────────────────────────────────


def _extract_vue_context(
    source_code: str,
    changed_lines: set[int],
    file_path: str,
    context_lines: int,
) -> str:
    """提取 Vue SFC 中 <script> 块的变更上下文。

    策略:
    1. 提取 <script> 块
    2. 将变更行映射到 script 块内的行号
    3. 用 JS/TS parser 找到包含变更行的函数/组件定义
    """
    script_code = extract_vue_script(source_code)
    if not script_code:
        logger.debug("Vue 文件无 <script> 块，使用行范围提取: %s", file_path)
        source_lines = source_code.splitlines()
        return _fallback_extract(source_lines, changed_lines, context_lines)

    # 计算 script 块在源文件中的起始行号
    source_lines = source_code.splitlines()
    script_start_line = 0
    for i, line in enumerate(source_lines):
        if "<script" in line:
            script_start_line = i + 1  # 1-indexed
            break

    # 将源文件行号映射到 script 内部行号
    script_lines = script_code.split("\n")
    script_changed: set[int] = set()
    for cl in changed_lines:
        relative = cl - script_start_line
        if 1 <= relative <= len(script_lines):
            script_changed.add(relative)

    if not script_changed:
        logger.debug("Vue 变更行不在 <script> 内，使用行范围提取: %s", file_path)
        return _fallback_extract(source_lines, changed_lines, context_lines)

    # 用 JS parser 解析 script 块
    # 创建一个虚拟的 JS 文件路径用于语言检测
    js_file_path = file_path.replace(".vue", ".js")
    return _extract_ts_context(
        script_code, script_changed, js_file_path, script_lines, context_lines,
    )


# ──────────────────────────────────────────────
#  tree-sitter 通用上下文提取
# ──────────────────────────────────────────────


def _extract_ts_context(
    source_code: str,
    changed_lines: set[int],
    file_path: str,
    source_lines: list[str],
    context_lines: int,
) -> str:
    """使用 tree-sitter 提取变更上下文。

    对所有非 Python 语言通用。步骤:
    1. tree-sitter 解析源码
    2. 遍历节点树，找到包含变更行的最小"函数/类/方法"节点
    3. 合并重叠节点，提取文本

    Args:
        source_code: 待解析的源码
        changed_lines: 变更行号（1-indexed）
        file_path: 文件路径
        source_lines: 源码按行拆分
        context_lines: 回退模式上下文行数

    Returns:
        压缩后的代码文本
    """
    parser = get_parser_for_file(file_path)
    if parser is None:
        logger.warning("tree-sitter parser 不可用 (%s)，降级为行范围提取", file_path)
        return _fallback_extract(source_lines, changed_lines, context_lines)

    try:
        tree = parser.parse(source_code.encode("utf-8"))
    except Exception as e:
        logger.warning("tree-sitter 解析失败 (%s): %s", file_path, e)
        return _fallback_extract(source_lines, changed_lines, context_lines)

    root = tree.root_node
    if root.has_error:
        logger.debug("tree-sitter 解析有语法错误 (%s)，继续提取", file_path)

    # 找到包含变更行的最小函数/类节点
    enclosing_nodes = _find_enclosing_nodes(root, changed_lines, source_code)

    if not enclosing_nodes:
        logger.debug("tree-sitter 未找到包含变更行的函数/类 (%s)，降级", file_path)
        return _fallback_extract(source_lines, changed_lines, context_lines)

    # 合并重叠节点、排序
    merged = _merge_overlapping_nodes(enclosing_nodes)

    # 提取并标记
    return _render_compressed(merged, source_code, changed_lines)


# ──────────────────────────────────────────────
#  节点查找
# ──────────────────────────────────────────────

# 各语言中表示"函数/类/方法"的 tree-sitter 节点类型
_FUNCTION_NODE_TYPES: set[str] = {
    # Java
    "class_declaration", "interface_declaration", "enum_declaration",
    "method_declaration", "constructor_declaration",
    # JavaScript
    "function_declaration", "generator_function_declaration",
    "class_declaration", "method_definition",
    "arrow_function",
    # TypeScript（与 JS 共享，额外类型）
    "abstract_class_declaration",
    "function",  # 某些 grammar 版本
    "class",     # 某些 grammar 版本
}


def _find_enclosing_nodes(root, changed_lines: set[int], source_code: str) -> list[tuple[int, int, str]]:
    """遍历 tree-sitter 树，找到包含变更行的所有函数/类节点。

    返回:
        [(start_byte, end_byte, node_type), ...] 去重后的节点列表
    """
    # 构建变更行到字节范围的映射
    line_starts: list[int] = [0]
    for i, ch in enumerate(source_code):
        if ch == "\n":
            line_starts.append(i + 1)
    # 确保数组长度足够
    while len(line_starts) <= max(changed_lines, default=0):
        line_starts.append(len(source_code))

    changed_ranges: list[tuple[int, int]] = []
    for cl in changed_lines:
        if 1 <= cl <= len(line_starts):
            start_byte = line_starts[cl - 1]
            # end_byte = 下一行开始，或到文件末尾
            end_byte = line_starts[cl] if cl < len(line_starts) else len(source_code)
            changed_ranges.append((start_byte - 1, end_byte))  # 兼容 0-indexed byte

    # 找到包含变更范围的最小函数节点
    result: dict[tuple[int, int], str] = {}  # (start_byte, end_byte) -> node_type

    def _walk(node):
        """递归遍历，找到包含变更行的最内层函数节点."""
        if node.type in _FUNCTION_NODE_TYPES:
            ns, ne = node.start_byte, node.end_byte
            # 检查此节点是否包含任何变更范围
            for cs, ce in changed_ranges:
                if ns <= cs < ne or ns < ce <= ne:
                    # 包含变更：记录此节点
                    key = (ns, ne)
                    # 覆盖策略：如果已有相同范围且当前节点更具体（子节点），覆盖
                    result[key] = node.type
                    return

        # 递归子节点
        for child in node.children:
            _walk(child)

    _walk(root)

    return [(k[0], k[1], v) for k, v in result.items()]


def _merge_overlapping_nodes(
    nodes: list[tuple[int, int, str]],
) -> list[tuple[int, int, str]]:
    """合并重叠的节点范围。

    例如 class + 内部 method → 合并为 class（范围更大）.
    但保留不重叠的独立节点（如两个独立的 class）。
    """
    if not nodes:
        return []

    # 按起始位置排序
    sorted_nodes = sorted(nodes, key=lambda x: x[0])

    merged: list[tuple[int, int, str]] = []
    current = sorted_nodes[0]

    for node in sorted_nodes[1:]:
        # 如果当前节点完全包含下一个节点 → 保留当前（更大的）
        if current[0] <= node[0] and current[1] >= node[1]:
            continue
        # 如果重叠但不完全包含 → 扩展范围
        elif current[1] >= node[0]:
            current = (current[0], max(current[1], node[1]), current[2])
        else:
            merged.append(current)
            current = node

    merged.append(current)
    return merged


def _render_compressed(
    nodes: list[tuple[int, int, str]],
    source_code: str,
    changed_lines: set[int],
) -> str:
    """将压缩后的节点渲染为带标记的文本。

    每个节点输出:
      1. 一行分隔注释（标注节点类型）
      2. 节点文本（变更行用 "# <-- CHANGED" 标记）
    """
    lines = source_code.split("\n")
    # 构建每个节点覆盖的行号范围
    byte_to_line: list[int] = [1]  # byte → line (1-indexed)
    for i, ch in enumerate(source_code):
        if ch == "\n":
            byte_to_line.append(byte_to_line[-1] + 1)
        else:
            byte_to_line.append(byte_to_line[-1])

    result_parts: list[str] = []

    for i, (start_byte, end_byte, node_type) in enumerate(nodes):
        # 节点分隔
        if i > 0:
            result_parts.append("")
        result_parts.append(f"# --- [{node_type}] ---")

        # 提取节点覆盖的行
        start_line = byte_to_line[start_byte] if start_byte < len(byte_to_line) else 1
        end_line = byte_to_line[min(end_byte, len(byte_to_line) - 1)]

        for line_no in range(start_line, end_line + 1):
            if line_no > len(lines):
                break
            line = lines[line_no - 1]
            marker = "  # <-- CHANGED" if line_no in changed_lines else ""
            result_parts.append(line + marker)

    return "\n".join(result_parts)


# ──────────────────────────────────────────────
#  文件级上下文注入（第 1 层防御：减少截断误报）
# ──────────────────────────────────────────────

_INJECTION_HEADER = "\n# === Injected File-Level Context (auto) ===\n"
_INJECTION_FOOTER = "\n# === End Injected Context ===\n\n"


def inject_file_context(
    compressed: str,
    full_source: str,
    file_path: str,
) -> str:
    """向压缩结果注入文件级声明（import + 全局变量/常量 + 函数签名）。

    解决 AST 压缩后 LLM 看不到文件顶部 import 和全局声明导致 "未定义变量" 误报的问题。

    Args:
        compressed: AST 压缩后的代码片段
        full_source: 重建后的完整源码
        file_path: 文件路径（用于语言检测）

    Returns:
        注入了文件级声明的压缩结果
    """
    if not full_source or not full_source.strip():
        return compressed

    imports_block = _extract_imports_block(full_source, file_path)
    global_decls = _extract_global_declarations(full_source, file_path)

    injected_parts = []
    if imports_block:
        injected_parts.append(imports_block)
    if global_decls:
        injected_parts.append(global_decls)

    if not injected_parts:
        return compressed

    return _INJECTION_HEADER + "\n".join(injected_parts) + _INJECTION_FOOTER + compressed


def _extract_imports_block(full_source: str, file_path: str) -> str:
    """从完整源码中提取 import/require 语句块。

    按语言策略:
    - Python: `import xxx` / `from xxx import yyy`
    - Java: `import com.xxx.yyy;`
    - JS/TS: `import xxx from 'xxx'` / `const xxx = require('xxx')`
    """
    lines = full_source.split("\n")
    import_lines: list[str] = []
    info = detect_language(file_path)

    for line in lines:
        stripped = line.strip()

        if info.name == "Python":
            if stripped.startswith(("import ", "from ")):
                import_lines.append(line)
            elif import_lines and stripped and not stripped.startswith("#"):
                break  # Python import 块结束
        elif info.name == "Java":
            if stripped.startswith("import "):
                import_lines.append(line)
            elif stripped.startswith("package "):
                import_lines.append(line)
        elif info.name in ("JavaScript", "TypeScript", "Vue"):
            if any(
                stripped.startswith(prefix)
                for prefix in ("import ", "const ", "let ", "var ", "export ")
            ):
                if "require(" in stripped or "from " in stripped:
                    import_lines.append(line)
                elif import_lines and "require(" not in stripped:
                    # 非 import 声明，如果 import 块已经开始则停止
                    break
            elif import_lines and not stripped.startswith("//"):
                break

    return "\n".join(import_lines) if import_lines else ""


def _extract_global_declarations(full_source: str, file_path: str) -> str:
    """从完整源码中提取全局常量/变量/函数签名声明。

    策略：提取文件顶层的 const/let/var/function/class 等，
    但只保留签名（不保留实现体），以控制 token 开销。
    """
    lines = full_source.split("\n")
    info = detect_language(file_path)

    if info.name in ("Python", "Java"):
        return ""  # Python/Java 的全局声明通常在类体中，不需要

    # JS/TS/Vue: 提取顶层声明签名
    decl_lines: list[str] = []
    in_function = False
    brace_count = 0

    for line in lines:
        stripped = line.strip()

        # 跳过 import 和注释
        if stripped.startswith(("import ", "//", "/*", "*", "export {")):
            continue
        if not stripped:
            if in_function and brace_count == 0:
                # 空行后如果不在函数内，加入
                pass
            continue

        if in_function:
            brace_count += stripped.count("{") - stripped.count("}")
            if brace_count <= 0:
                in_function = False
                brace_count = 0
            continue

        # 检查是否为顶层声明
        is_decl = any(
            stripped.startswith(prefix)
            for prefix in ("const ", "let ", "var ", "function ", "async function ",
                           "class ", "export const ", "export let ", "export function ")
        )
        if is_decl:
            # 如果是函数/类声明，只取签名行
            if ("{" in stripped and any(kw in stripped for kw in ("function ", "class ", "=>"))):
                in_function = True
                brace_count = stripped.count("{") - stripped.count("}")
                if brace_count <= 0:
                    in_function = False
                    brace_count = 0
                    decl_lines.append(stripped + ";  // (global)")
                else:
                    decl_lines.append(stripped.split("{")[0].strip() + " { ... }  // (global)")
            else:
                decl_lines.append(stripped + "  // (global)")

    return "\n".join(decl_lines) if decl_lines else ""


# ──────────────────────────────────────────────
#  局部调用图注入（第 2 层防御：同文件调用关系）
# ──────────────────────────────────────────────

_LOCAL_CALL_HEADER = (
    "\n\n"
    "---- 8< ----\n"
    "[Local Call Graph: 同文件调用关系（由 AST 分析自动生成）]\n"
)
_LOCAL_CALL_FOOTER = "\n---- 8< ----\n"


def build_local_call_graph(
    full_source: str,
    file_path: str,
) -> dict:
    """分析同文件内的函数调用关系。

    Args:
        full_source: 完整源码
        file_path: 文件路径

    Returns:
        {
            "exports": [func_name, ...],      # 文件内所有顶层函数
            "edges": [                          # 同文件调用边
                {"caller": "buildReply", "callee": "normalizeDraftLab", "line": 650},
            ]
        }
    """
    parser = get_parser_for_file(file_path)
    if parser is None:
        return {"exports": [], "edges": []}

    try:
        tree = parser.parse(full_source.encode("utf-8"))
    except Exception:
        return {"exports": [], "edges": []}

    root = tree.root_node

    # 1. 收集所有顶层函数/类导出
    exports = _collect_top_level_exports(root, file_path)

    # 2. 收集所有调用
    info = detect_language(file_path)
    calls = _collect_all_calls(root, full_source, info.name)

    # 3. 匹配调用到导出 → 构建边
    edges = []
    export_set = set(exports)
    for call in calls:
        call_name = call.get("name", "")
        # 直调匹配
        if call["type"] == "direct" and call_name in export_set:
            edges.append({
                "caller": "?",
                "callee": call_name,
                "line": call.get("line", 0),
            })
        # 属性调用也尝试匹配（module.func → func）
        elif call["type"] == "attribute":
            attr = call.get("attr", "")
            if attr and attr in export_set:
                edges.append({
                    "caller": "?",
                    "callee": attr,
                    "line": call.get("line", 0),
                })

    # 4. 标注每个调用边属于哪个函数（caller）
    _assign_callers_to_edges(root, edges, full_source)

    return {"exports": exports, "edges": edges}


def inject_local_call_graph(
    compressed: str,
    full_source: str,
    file_path: str,
    changed_function_names: list[str],
) -> str:
    """向压缩结果注入同文件调用关系上下文。

    Args:
        compressed: AST 压缩后的代码片段
        full_source: 完整源码
        file_path: 文件路径
        changed_function_names: 变更涉及的函数名列表

    Returns:
        注入了局部调用图的压缩结果
    """
    if not changed_function_names:
        return compressed

    call_graph = build_local_call_graph(full_source, file_path)
    edges = call_graph.get("edges", [])

    if not edges:
        return compressed

    changed_set = set(changed_function_names)

    # 找出：谁调了变更函数
    callers_of_changed: list[tuple[str, int]] = []
    for edge in edges:
        if edge.get("callee") in changed_set:
            caller = edge.get("caller", "?")
            if caller and caller != "?" and caller not in changed_set:
                callers_of_changed.append((caller, edge.get("line", 0)))

    # 找出：变更函数调了谁
    callees_of_changed: list[tuple[str, int]] = []
    for edge in edges:
        if edge.get("caller") in changed_set:
            callee = edge.get("callee", "")
            if callee and callee not in changed_set:
                callees_of_changed.append((callee, edge.get("line", 0)))

    if not callers_of_changed and not callees_of_changed:
        return compressed

    # 构建注入块
    parts: list[str] = []

    if callers_of_changed:
        unique_callers = list(dict.fromkeys(callers_of_changed))[:5]
        caller_strs = [f"{c}(第 {l} 行)" for c, l in unique_callers]
        parts.append(f"  → 被同文件调用: {', '.join(caller_strs)}")

    if callees_of_changed:
        unique_callees = list(dict.fromkeys(callees_of_changed))[:5]
        callee_strs = [f"{c}()(第 {l} 行)" for c, l in unique_callees]
        parts.append(f"  → 调用了同文件函数: {', '.join(callee_strs)}")

    if not parts:
        return compressed

    return (
        compressed.rstrip()
        + _LOCAL_CALL_HEADER
        + "\n".join(parts)
        + _LOCAL_CALL_FOOTER
    )


# ──────────────────────────────────────────────
#  tree-sitter 辅助函数
# ──────────────────────────────────────────────


def _collect_top_level_exports(root, file_path: str) -> list[str]:
    """收集顶层导出符号名称。处理 export statement 包装."""
    exports = []
    for child in root.children:
        # 处理 export function name / export const name 等
        unwrapped = child
        if child.type == "export_statement":
            # 找到 export 内部的声明节点
            for inner in child.children:
                if inner.type not in ("export", "default", ";", ","):
                    unwrapped = inner
                    break
        name = _get_ts_node_name(unwrapped)
        if name:
            exports.append(name)
    return exports


def _get_ts_node_name(node) -> Optional[str]:
    """从 tree-sitter 节点提取名称."""
    if hasattr(node, "child_by_field_name"):
        name_node = node.child_by_field_name("name")
        if name_node and hasattr(name_node, "text"):
            return name_node.text.decode("utf-8")
    # Fallback: check children
    for child in node.children:
        if child.type in ("identifier", "property_identifier") and hasattr(child, "text"):
            return child.text.decode("utf-8")
    return None


def _collect_all_calls(root, source: str, lang_name: str) -> list[dict]:
    """收集文件中所有函数调用（内联版本，避免循环导入）."""
    calls: list[dict] = []

    # 递归遍历所有 call_expression 和 method_invocation 节点
    def _walk_collect(node):
        if node.type in ("call_expression", "new_expression", "method_invocation"):
            line = node.start_point[0] + 1
            # 查找被调函数名
            for child in node.children:
                if child.type == "identifier":
                    call_name = child.text.decode("utf-8") if hasattr(child, "text") else ""
                    if call_name and call_name not in ("if", "for", "while", "return", "console"):
                        calls.append({"line": line, "name": call_name, "type": "direct"})
                    break
                elif child.type == "member_expression":
                    # obj.method()
                    obj = None
                    prop = None
                    for mc in child.children:
                        mc_text = mc.text.decode("utf-8") if hasattr(mc, "text") else ""
                        if mc.type == "identifier" and obj is None:
                            obj = mc_text
                        elif mc.type == "property_identifier":
                            prop = mc_text
                    if prop:
                        calls.append({
                            "line": line,
                            "name": f"{obj}.{prop}" if obj else prop,
                            "type": "attribute",
                            "module": obj or "",
                            "attr": prop,
                        })
                    break
        for child in node.children:
            _walk_collect(child)

    _walk_collect(root)
    return calls


def _assign_callers_to_edges(root, edges: list[dict], source: str) -> None:
    """为每条调用边标注它所在的函数名（直接修改 edges）."""
    for child in root.children:
        # 使用 export_statement 的 start_byte（包含 export 关键字）
        # 而非内部 function_declaration 的 start_byte（不包含）
        container = child
        func_node = child

        if child.type == "export_statement":
            for inner in child.children:
                if inner.type not in ("export", "default", ";", ","):
                    func_node = inner
                    break

        caller_name = _get_ts_node_name(func_node)
        if not caller_name:
            continue

        # 使用 container 的 start_byte（覆盖 export 前缀）
        func_start = container.start_byte if hasattr(container, "start_byte") else 0
        func_end = container.end_byte if hasattr(container, "end_byte") else 0

        if func_start == 0:
            continue

        for edge in edges:
            edge_line = edge.get("line", 0)
            line_start = _line_to_byte(source, edge_line)
            if func_start <= line_start < func_end:
                edge["caller"] = caller_name


def _line_to_byte(source: str, line_no: int) -> int:
    """将 1-indexed 行号转换为字节偏移."""
    lines = source.split("\n")
    offset = 0
    for i in range(min(line_no - 1, len(lines))):
        offset += len(lines[i]) + 1
    return offset


# ── CLI 测试入口 ──

if __name__ == "__main__":
    import argparse

    logging.basicConfig(level=logging.DEBUG)

    # 测试 Java 源码
    java_code = """
public class UserService {
    private UserRepository repo;

    public UserService(UserRepository repo) {
        this.repo = repo;
    }

    public User createUser(String name, String email) {
        // NEW CODE: validate email
        if (!email.contains("@")) {
            throw new IllegalArgumentException("Invalid email");
        }
        User user = new User(name, email);
        return repo.save(user);
    }

    public void deleteUser(Long id) {
        repo.deleteById(id);
    }
}
""".strip()

    print("Java 测试:")
    changed = {8, 9}  # email validation lines
    result = extract_context_multi_lang(java_code, changed, "UserService.java")
    print(result)
    print()

    # 测试 JS 源码
    js_code = """
import axios from 'axios';

export function fetchLabData(labId) {
    return axios.get(`/api/labs/${labId}`);
}

export function createReservation(data) {
    // NEW: conflict check
    if (!data.labId) {
        throw new Error('labId is required');
    }
    return axios.post('/api/reservations', data);
}
""".strip()

    print("JavaScript 测试:")
    result2 = extract_context_multi_lang(js_code, {12, 13, 14}, "api.js")
    print(result2)
