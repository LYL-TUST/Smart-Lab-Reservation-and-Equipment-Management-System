"""
AI Code Reviewer — 基于 AST 的跨文件调用图构建器.

核心价值：突破"单文件独立审查"的限制，为 LLM 提供跨文件的调用上下文，
使审查能理解函数间的依赖关系和调用链影响。

面试金句：
"下一个版本我要从'基于单文件的上下文压缩'，升级到'基于依赖图的全局分析'。"

核心函数:
    build_call_graph(files_source: dict[str, str]) -> dict
"""

import ast
import logging
from typing import Any

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────
#  数据结构
# ──────────────────────────────────────────────

# 文件分析结果
_FILE_ANALYSIS = dict[str, Any]


def build_call_graph(files_source: dict[str, str]) -> dict:
    """分析 PR 涉及文件的跨文件调用关系，构建调用图。

    Args:
        files_source: {文件路径: 源码字符串}，.py 之外的文件会被自动跳过

    Returns:
        {
          "files": {
            "utils.py": {
              "exports": ["validate_email", "send_mail"],
              "imports": [
                {"module": "typing", "names": ["Optional"], "aliases": {}},
              ],
              "calls": [
                {"line": 15, "name": "validate_email", "type": "direct"},
                {"line": 20, "name": "re.match", "type": "attribute", "module": "re"},
              ],
            },
          },
          "edges": [
            {
              "source_file": "app.py",
              "source_line": 10,
              "target_file": "utils.py",
              "target_function": "validate_email",
              "call_name": "validate_email",
            },
          ],
          "changed_functions": {"utils.py": ["validate_email"]},
          "edge_count": 1,
          "file_count": 2,
          "errors": [],
        }
    """
    # Step 1: 逐文件分析
    analyses: dict[str, _FILE_ANALYSIS] = {}
    errors: list[str] = []
    changed_functions: dict[str, list[str]] = {}

    for file_path, source in files_source.items():
        if not file_path.endswith(".py"):
            logger.debug("跳过非 Python 文件: %s", file_path)
            continue

        analysis = _analyze_file(file_path, source)
        if analysis is None:
            errors.append(f"AST 解析失败: {file_path}")
            continue

        analyses[file_path] = analysis
        changed_functions[file_path] = analysis["exports"]

    # Step 2: 跨文件匹配调用 → 构建边
    edges: list[dict] = []

    for file_path, analysis in analyses.items():
        imports = analysis["imports"]
        calls = analysis["calls"]
        module_map = _build_module_map(file_path, imports)

        for call in calls:
            edge = _resolve_call(
                call, file_path, module_map, analyses,
            )
            if edge is not None:
                edges.append(edge)

    return {
        "files": analyses,
        "edges": edges,
        "changed_functions": changed_functions,
        "edge_count": len(edges),
        "file_count": len(analyses),
        "errors": errors,
    }


# ──────────────────────────────────────────────
#  单文件分析
# ──────────────────────────────────────────────


def _analyze_file(file_path: str, source: str) -> _FILE_ANALYSIS | None:
    """解析单个 Python 文件，提取导出符号、导入声明和调用表达式。"""
    try:
        tree = ast.parse(source)
    except SyntaxError as e:
        logger.warning("AST 解析失败: %s — %s", file_path, e)
        return None

    exports = _collect_exports(tree)
    imports = _collect_imports(tree)
    calls = _collect_calls(tree)

    return {
        "file_path": file_path,
        "exports": exports,
        "imports": imports,
        "calls": calls,
    }


# ── 导出符号 ──


def _collect_exports(tree: ast.AST) -> list[str]:
    """收集顶级导出符号：函数、异步函数、类的名称。"""
    exports: list[str] = []
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            exports.append(node.name)
        # 如果是 'from X import Y as Z' 这种重导出，暂不处理
    return exports


# ── 导入声明 ──


def _collect_imports(tree: ast.AST) -> list[dict]:
    """收集导入声明。

    返回:
        [
            {"module": "os", "names": [], "aliases": {}},
            {"module": "typing", "names": ["Optional", "List"], "aliases": {}},
            {"module": "utils", "names": ["validate_email"],
             "aliases": {"validate_email": "val_email"}},
        ]
    """
    imports: list[dict] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append({
                    "module": alias.name,
                    "names": [],
                    "aliases": {},
                    "asname": alias.asname or "",
                })

        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            names: list[str] = []
            aliases: dict[str, str] = {}
            for alias in node.names:
                names.append(alias.name)
                if alias.asname:
                    aliases[alias.name] = alias.asname

            imports.append({
                "module": module,
                "names": names,
                "aliases": aliases,
                "asname": "",
            })

    return imports


def _build_module_map(file_path: str, imports: list[dict]) -> dict[str, str]:
    """构建本文件中的"短名 → 完整模块名"映射。

    例如:
        from utils import validate_email
        → {"validate_email": "utils"}

        import os
        → {"os": "os"}

        from typing import Optional
        → {"Optional": "typing"}
    """
    module_map: dict[str, str] = {}

    for imp in imports:
        # import X → {"X": "X"}
        if not imp["names"]:
            # 从模块名中取第一部分
            top_module = imp["module"].split(".")[0]
            module_map[top_module] = imp["module"]
            if imp["asname"]:
                module_map[imp["asname"]] = imp["module"]
        else:
            # from X import Y → {"Y": "X"}
            for name in imp["names"]:
                actual_name = imp["aliases"].get(name, name)
                module_map[actual_name] = imp["module"]
            if imp["asname"]:
                module_map[imp["asname"]] = imp["module"]

    return module_map


# ── 调用表达式 ──


def _collect_calls(tree: ast.AST) -> list[dict]:
    """收集文件中所有函数调用表达式。

    返回:
        [
            {"line": 10, "name": "validate_email", "type": "direct"},
            {"line": 15, "name": "os.path.join", "type": "attribute",
             "module": "os", "attr": "join"},
            {"line": 20, "name": "app.run", "type": "attribute",
             "module": "app", "attr": "run"},
        ]
    """
    calls: list[dict] = []

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue

        line = getattr(node, "lineno", 0)
        call_info = _parse_call_expr(node.func, line)
        if call_info:
            calls.append(call_info)

    return calls


def _parse_call_expr(func: ast.AST, line: int) -> dict | None:
    """解析调用表达式，提取调用名和类型。"""
    # 直调: foo("bar")
    if isinstance(func, ast.Name):
        return {
            "line": line,
            "name": func.id,
            "type": "direct",
        }

    # 属性调用: module.foo()
    if isinstance(func, ast.Attribute):
        # 提取链条
        chain = _extract_attr_chain(func)
        if chain and len(chain) >= 2:
            return {
                "line": line,
                "name": ".".join(chain),
                "type": "attribute",
                "module": chain[0],
                "attr": ".".join(chain[1:]),
            }

    return None


def _extract_attr_chain(node: ast.AST) -> list[str]:
    """将属性访问链条展开为字符串列表。

    os.path.join → ["os", "path", "join"]
    self.client.get → 返回空（跳过 self/type 内部调用）
    """
    parts: list[str] = []

    while isinstance(node, ast.Attribute):
        parts.append(node.attr)
        node = node.value

    if isinstance(node, ast.Name):
        parts.append(node.id)
    else:
        # self.xxx 或链上包含非 Name 节点 → 跳过
        return []

    parts.reverse()
    return parts


# ──────────────────────────────────────────────
#  跨文件匹配
# ──────────────────────────────────────────────


def _resolve_call(
    call: dict,
    source_file: str,
    module_map: dict[str, str],
    analyses: dict[str, _FILE_ANALYSIS],
) -> dict | None:
    """将一个调用表达式匹配到目标文件的目标函数。

    匹配逻辑:
    - 直调 (foo): 在 module_map 中查找 foo → 找到模块 → 在 analyses 中找目标文件
    - 属性调用 (module.foo): 用 module 名匹配目标文件名
    """
    call_name = call.get("name", "")
    call_line = call.get("line", 0)

    if call["type"] == "direct":
        # 直调: 检查是否是导入的名字
        if call_name in module_map:
            target_module = module_map[call_name]
            # 尝试匹配导入的某个特定名字
            target_file, target_func = _match_imported_name(
                call_name, target_module, analyses,
            )
            if target_file:
                return {
                    "source_file": source_file,
                    "source_line": call_line,
                    "target_file": target_file,
                    "target_function": target_func or call_name,
                    "call_name": call_name,
                }

        # 直调名字不在导入中 → 可能跨模块调用，需要与所有文件的导出匹配
        for candidate_file, analysis in analyses.items():
            if candidate_file == source_file:
                continue
            if call_name in analysis["exports"]:
                return {
                    "source_file": source_file,
                    "source_line": call_line,
                    "target_file": candidate_file,
                    "target_function": call_name,
                    "call_name": call_name,
                }

    elif call["type"] == "attribute":
        # 属性调用: module.attr
        call_module = call.get("module", "")
        chain_attr = call.get("attr", "")

        # 检查 module 名是否在导入中
        resolved_module = module_map.get(call_module, call_module)
        # 尝试匹配文件
        for candidate_file in analyses:
            if candidate_file == source_file:
                continue
            # 文件路径匹配模块名: "utils.py" → "utils"
            file_stem = candidate_file.replace("\\", "/").replace(".py", "").split("/")[-1]
            if file_stem == resolved_module or file_stem == resolved_module.split(".")[0]:
                # 找到目标文件，检查函数是否在导出中
                target_func = chain_attr.split(".")[0]  # 只取第一段属性
                if target_func in analyses[candidate_file]["exports"]:
                    return {
                        "source_file": source_file,
                        "source_line": call_line,
                        "target_file": candidate_file,
                        "target_function": target_func,
                        "call_name": call_name,
                    }

    return None


def _match_imported_name(
    name: str,
    module: str,
    analyses: dict[str, _FILE_ANALYSIS],
) -> tuple[str | None, str | None]:
    """将导入名 {name} 匹配到目标文件和目标函数。

    查找 module 对应的文件，并检查该文件是否导出 name。
    """
    for candidate_file, analysis in analyses.items():
        file_stem = candidate_file.replace("\\", "/").replace(".py", "").split("/")[-1]

        # 支持多层模块: "utils" 匹配 "utils.py"；"a.b" 匹配 "a/b.py"
        module_path = module.replace(".", "/")
        if file_stem == module_path or module_path.endswith("/" + file_stem):
            if name in analysis["exports"]:
                return candidate_file, name

    return None, None


# ── CLI 测试入口 ──

if __name__ == "__main__":
    import json
    import sys

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    if len(sys.argv) < 2:
        print("用法: python src/call_graph_builder.py <file1.py> <file2.py> ...")
        sys.exit(1)

    files_source = {}
    for path in sys.argv[1:]:
        try:
            with open(path, "r", encoding="utf-8") as f:
                files_source[path] = f.read()
        except FileNotFoundError:
            logger.error("文件不存在: %s", path)

    result = build_call_graph(files_source)
    print(json.dumps(result, indent=2, ensure_ascii=False))
