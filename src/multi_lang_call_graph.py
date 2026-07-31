"""
AI Code Reviewer - 多语言调用图分析引擎.

基于 tree-sitter 的跨文件调用关系分析，支持 Python / Java / Vue / JS / TS。
每种语言有独立的 import 解析和调用表达式提取逻辑，
最终输出统一的 CallGraph 数据结构。

Python 委托给 src.call_graph_builder（保持兼容），
其他语言通过 tree-sitter 实现。

核心函数:
    build_multi_lang_call_graph(files_source) -> dict
"""

import ast as py_ast
import logging
import os
import re
from typing import Any, Optional

from src.language_detector import (
    detect_language, is_python, extract_vue_script, get_parser_for_file,
)

logger = logging.getLogger(__name__)

_FILE_ANALYSIS = dict[str, Any]


# ──────────────────────────────────────────────
#  主入口
# ──────────────────────────────────────────────


def build_multi_lang_call_graph(files_source: dict[str, str]) -> dict:
    """分析 PR 涉及文件的跨文件调用关系。

    对 Python 文件委托给现有 build_call_graph，
    对其他语言使用 tree-sitter 独立分析，
    最后合并所有语言的 results。

    Args:
        files_source: {文件路径: 源码字符串}

    Returns:
        {
          "files": { file_path: FileAnalysis },
          "edges": [ CrossFileEdge ],
          "changed_functions": { file_path: [func_name] },
          "edge_count": int,
          "file_count": int,
          "errors": [str],
        }
    """
    all_analyses: dict[str, _FILE_ANALYSIS] = {}
    all_changed_functions: dict[str, list[str]] = {}
    all_edges: list[dict] = []
    all_errors: list[str] = []

    # 分离 Python 和非 Python 文件
    py_files = {}
    non_py_files = {}

    for fp, src in files_source.items():
        if not src or not src.strip():
            continue
        if is_python(fp):
            py_files[fp] = src
        else:
            non_py_files[fp] = src

    # Python: 委托给现有模块
    if py_files:
        from src.call_graph_builder import build_call_graph
        py_result = build_call_graph(py_files)
        all_analyses.update(py_result.get("files", {}))
        all_changed_functions.update(py_result.get("changed_functions", {}))
        all_edges.extend(py_result.get("edges", []))
        all_errors.extend(py_result.get("errors", []))

    # 非 Python: tree-sitter 分析
    for fp, src in non_py_files.items():
        info = detect_language(fp)

        if info.name == "Vue":
            analysis, edges = _analyze_vue_file(fp, src, non_py_files)
        elif info.uses_ts:
            analysis, edges = _analyze_ts_file(fp, src)
        else:
            logger.debug("跳过不支持的语言: %s (%s)", fp, info.name)
            continue

        if analysis is None:
            all_errors.append(f"解析失败: {fp}")
            continue

        all_analyses[fp] = analysis
        if analysis.get("exports"):
            all_changed_functions[fp] = analysis["exports"]
        all_edges.extend(edges)

    # 跨语言边：TS/JS 文件之间也需要匹配
    ts_edges = _resolve_ts_cross_file_edges(all_analyses)
    all_edges.extend(ts_edges)

    return {
        "files": all_analyses,
        "edges": all_edges,
        "changed_functions": all_changed_functions,
        "edge_count": len(all_edges),
        "file_count": len(all_analyses),
        "errors": all_errors,
    }


# ──────────────────────────────────────────────
#  tree-sitter 文件分析 (Java/JS/TS)
# ──────────────────────────────────────────────


def _analyze_ts_file(file_path: str, source: str) -> tuple[Optional[_FILE_ANALYSIS], list[dict]]:
    """使用 tree-sitter 分析单个文件（Java/JS/TS）."""
    parser = get_parser_for_file(file_path)
    if parser is None:
        return None, []

    try:
        tree = parser.parse(source.encode("utf-8"))
    except Exception as e:
        logger.warning("tree-sitter 解析失败: %s — %s", file_path, e)
        return None, []

    root = tree.root_node
    info = detect_language(file_path)

    exports = _ts_collect_exports(root, info.name)
    imports = _ts_collect_imports(root, source, info.name)
    calls = _ts_collect_calls(root, source, info.name)

    analysis = {
        "file_path": file_path,
        "exports": exports,
        "imports": imports,
        "calls": calls,
    }

    # 本文件内的调用边（同一文件不同函数之间，暂不生成——只关注跨文件）
    return analysis, []


def _analyze_vue_file(
    file_path: str,
    source: str,
    all_files: dict[str, str],
) -> tuple[Optional[_FILE_ANALYSIS], list[dict]]:
    """分析 Vue SFC 文件：提取 <script> 块后按 JS/TS 分析."""
    script_code = extract_vue_script(source)
    if not script_code:
        return {"file_path": file_path, "exports": [], "imports": [], "calls": []}, []

    # 创建虚拟 JS 文件路径
    js_path = file_path.replace(".vue", ".js")
    return _analyze_ts_file(js_path, script_code)


# ──────────────────────────────────────────────
#  tree-sitter 导出符号提取
# ──────────────────────────────────────────────


def _ts_collect_exports(root, lang_name: str) -> list[str]:
    """从 tree-sitter 树中提取导出符号（函数/类/方法名称）."""
    exports: list[str] = []
    _ts_walk_exports(root, exports, lang_name)
    return exports


def _ts_walk_exports(node, exports: list[str], lang_name: str):
    """递归遍历，收集顶级导出符号."""
    for child in node.children:
        name = _get_node_name(child, lang_name)
        if name:
            exports.append(name)
        # 仅递归顶级节点（class/function 级别）
        if child.type in ("class_declaration", "class", "interface_declaration"):
            # 类不继续递归——方法不算独立导出
            pass
        else:
            _ts_walk_exports(child, exports, lang_name)


def _get_node_name(node, lang_name: str) -> Optional[str]:
    """从节点中提取名称."""
    if node.type in (
        "function_declaration", "generator_function_declaration",
        "method_definition", "class_declaration", "interface_declaration",
        "constructor_declaration", "arrow_function",
    ):
        # 查找 name 字段
        name_node = _find_child_by_field(node, "name")
        if name_node:
            return name_node.text.decode("utf-8") if hasattr(name_node, "text") else ""

    return None


# ──────────────────────────────────────────────
#  tree-sitter import 解析
# ──────────────────────────────────────────────


def _ts_collect_imports(root, source: str, lang_name: str) -> list[dict]:
    """收集导入声明。

    返回格式（与 call_graph_builder 兼容）:
        [
            {"module": "./utils", "names": ["fetchData"], "aliases": {}},
            {"module": "java.util", "names": ["List"], "aliases": {}},
        ]
    """
    if lang_name == "Java":
        return _java_collect_imports(root)
    else:
        return _js_collect_imports(root, source)


def _java_collect_imports(root) -> list[dict]:
    """Java import 解析。

    处理: import com.example.Service; → {module: "com.example", names: ["Service"]}
          import com.example.*;           → {module: "com.example", names: ["*"]}
          import static com.example.Util.method; → 暂不支持
    """
    imports: list[dict] = []
    for node in _walk_nodes(root, "import_declaration"):
        text = node.text.decode("utf-8") if hasattr(node, "text") else ""

        # 提取导入路径
        scope_node = _find_child_by_field(node, "scope")
        if not scope_node:
            continue

        import_path = ""
        name_node = _find_child_by_field(node, "name")
        star = False
        for child in scope_node.children:
            child_text = child.text.decode("utf-8") if hasattr(child, "text") else ""
            if child.type == "asterisk" or child_text == "*":
                star = True
            elif child.type in ("identifier", "scoped_identifier"):
                import_path = child_text if child.type == "scoped_identifier" else child_text

        if star:
            # 通配符 import: 只记录模块，不解析具体名称
            imports.append({
                "module": import_path.replace(".", "/"),
                "names": [],
                "aliases": {},
            })
        elif name_node:
            class_name = name_node.text.decode("utf-8") if hasattr(name_node, "text") else ""
            imports.append({
                "module": import_path.replace(".", "/"),
                "names": [class_name],
                "aliases": {},
            })

    return imports


def _js_collect_imports(root, source: str) -> list[dict]:
    """JS/TS import 解析。

    处理:
        import { foo, bar } from './utils'    → names: ["foo", "bar"]
        import Foo from './foo'                → names: ["Foo"] (default)
        import * as X from './x'              → names: ["*"]
        const X = require('./x')              → names: ["X"]
    """
    imports: list[dict] = []

    for node in _walk_nodes(root, "import_statement"):
        source_node = _find_child_by_field(node, "source")
        if not source_node:
            continue
        module = _extract_module_path(source_node)

        names: list[str] = []
        aliases: dict[str, str] = {}

        # import specifiers: { foo, bar as baz }
        for child in node.children:
            if child.type == "import_specifier":
                spec_name = ""
                spec_alias = ""
                for sc in child.children:
                    sc_text = sc.text.decode("utf-8") if hasattr(sc, "text") else ""
                    if sc.type == "identifier" and not spec_name:
                        spec_name = sc_text
                    elif sc.type == "identifier":
                        spec_alias = sc_text
                if spec_name:
                    names.append(spec_name)
                    if spec_alias:
                        aliases[spec_name] = spec_alias

            # default import: import Foo from './foo'
            elif child.type == "import_clause":
                for cc in child.children:
                    if cc.type == "identifier":
                        cc_text = cc.text.decode("utf-8") if hasattr(cc, "text") else ""
                        names.append(cc_text)

            # namespace import: import * as X
            elif child.type == "namespace_import":
                for nc in child.children:
                    nc_text = nc.text.decode("utf-8") if hasattr(nc, "text") else ""
                    if nc.type == "identifier" and nc_text not in ("*", "as"):
                        names.append(nc_text)

        if module:
            imports.append({
                "module": module,
                "names": names,
                "aliases": aliases,
            })

    # require() 调用（CommonJS）
    for node in _walk_nodes(root, "lexical_declaration"):
        for child in node.children:
            if child.type == "variable_declarator":
                name = ""
                call = None
                for dc in child.children:
                    dc_text = dc.text.decode("utf-8") if hasattr(dc, "text") else ""
                    if dc.type == "identifier":
                        name = dc_text
                    elif dc.type == "call_expression":
                        call = dc
                if name and call:
                    fn = _find_child_by_field(call, "function")
                    if fn and fn.text.decode("utf-8") if hasattr(fn, "text") else "" == "require":
                        args = _find_child_by_field(call, "arguments")
                        if args:
                            for arg in args.children:
                                if arg.type == "string":
                                    arg_text = arg.text.decode("utf-8") if hasattr(arg, "text") else ""
                                    module_path = arg_text.strip("'\"")
                                    imports.append({
                                        "module": module_path,
                                        "names": [name],
                                        "aliases": {},
                                    })

    return imports


# ──────────────────────────────────────────────
#  tree-sitter 调用表达式提取
# ──────────────────────────────────────────────


def _ts_collect_calls(root, source: str, lang_name: str) -> list[dict]:
    """收集所有函数调用表达式。

    返回:
        [
            {"line": 10, "name": "validateEmail", "type": "direct"},
            {"line": 15, "name": "userService.create", "type": "attribute",
             "module": "userService", "attr": "create"},
        ]
    """
    calls: list[dict] = []
    for node in _walk_nodes(root, None):
        if node.type in ("method_invocation",):  # Java
            calls.extend(_extract_java_call(node))
        elif node.type in ("call_expression", "new_expression"):  # JS/TS
            calls.extend(_extract_js_call(node, source))
    return calls


def _extract_java_call(node) -> list[dict]:
    """提取 Java 方法调用."""
    calls = []
    line = node.start_point[0] + 1

    # method_invocation: obj.method() or static Method()
    name_node = _find_child_by_field(node, "name")
    obj_node = _find_child_by_field(node, "object")

    if name_node:
        call_name = name_node.text.decode("utf-8") if hasattr(name_node, "text") else ""
        if obj_node:
            obj_text = obj_node.text.decode("utf-8") if hasattr(obj_node, "text") else ""
            calls.append({
                "line": line,
                "name": f"{obj_text}.{call_name}",
                "type": "attribute",
                "module": obj_text,
                "attr": call_name,
            })
        else:
            calls.append({
                "line": line,
                "name": call_name,
                "type": "direct",
            })

    return calls


def _extract_js_call(node, source: str) -> list[dict]:
    """提取 JS/TS 函数调用."""
    calls = []
    line = node.start_point[0] + 1
    func_node = _find_child_by_field(node, "function")

    if not func_node:
        # 尝试从 children 中查找
        for child in node.children:
            if child.type in ("identifier", "member_expression"):
                func_node = child
                break

    if not func_node:
        return calls

    if func_node.type == "identifier":
        call_name = func_node.text.decode("utf-8") if hasattr(func_node, "text") else ""
        calls.append({
            "line": line,
            "name": call_name,
            "type": "direct",
        })
    elif func_node.type == "member_expression":
        obj_node = _find_child_by_field(func_node, "object")
        prop_node = _find_child_by_field(func_node, "property")
        if obj_node and prop_node:
            obj_text = obj_node.text.decode("utf-8") if hasattr(obj_node, "text") else ""
            prop_text = prop_node.text.decode("utf-8") if hasattr(prop_node, "text") else ""
            calls.append({
                "line": line,
                "name": f"{obj_text}.{prop_text}",
                "type": "attribute",
                "module": obj_text,
                "attr": prop_text,
            })

    return calls


# ──────────────────────────────────────────────
#  跨文件边解析
# ──────────────────────────────────────────────


def _resolve_ts_cross_file_edges(analyses: dict[str, _FILE_ANALYSIS]) -> list[dict]:
    """解析 tree-sitter 分析的文件的跨文件调用边。

    对非 Python 文件执行：
    1. 构建每个文件的 import → file 映射
    2. 匹配调用表达式到目标文件的导出
    """
    edges: list[dict] = []

    for source_file, analysis in analyses.items():
        # 跳过 Python 文件（已由 call_graph_builder 处理）
        if source_file.endswith(".py"):
            continue

        imports = analysis.get("imports", [])
        calls = analysis.get("calls", [])
        exports = analysis.get("exports", [])

        # 构建 import 映射
        import_map = _build_ts_import_map(source_file, imports, analyses)

        for call in calls:
            edge = _resolve_ts_call(call, source_file, import_map, analyses)
            if edge:
                edges.append(edge)

    return edges


def _build_ts_import_map(
    source_file: str,
    imports: list[dict],
    analyses: dict[str, _FILE_ANALYSIS],
) -> dict[str, str]:
    """构建名 → 文件路径的映射。

    Java: import com.example.Service → {"Service": "backend/.../Service.java"}
    JS:   import { foo } from './utils' → {"foo": "src/utils.js"}
    """
    imap: dict[str, str] = {}

    for imp in imports:
        module = imp.get("module", "")
        names = imp.get("names", [])

        if not names:
            continue

        target_file = _resolve_import_to_file(source_file, module, list(analyses.keys()))

        if target_file:
            for name in names:
                actual_name = imp.get("aliases", {}).get(name, name)
                imap[actual_name] = target_file

    return imap


def _resolve_import_to_file(
    source_file: str,
    module_path: str,
    all_file_paths: list[str],
) -> Optional[str]:
    """将 import 路径解析为实际文件路径.

    Java: "com/example/Service" → 查找含 "com/example/Service.java" 的文件
    JS:   "./utils"             → 查找相对路径的 utils.js/ts/index.js 等
    """
    # Java: 包名路径匹配
    if module_path and "/" in module_path and not module_path.startswith("."):
        # 尝试匹配路径后缀
        path_suffix = module_path + ".java"
        for fp in all_file_paths:
            normalized = fp.replace("\\", "/")
            if normalized.endswith(path_suffix):
                return fp
            # 也尝试只匹配类名
            class_name = module_path.split("/")[-1]
            if normalized.endswith("/" + class_name + ".java"):
                return fp
        return None

    # JS/TS: 相对路径解析
    if module_path.startswith("./") or module_path.startswith("../"):
        source_dir = os.path.dirname(source_file).replace("\\", "/")
        resolved = os.path.normpath(os.path.join(source_dir, module_path)).replace("\\", "/")

        # 尝试多种扩展名
        candidates = [
            resolved + ".js", resolved + ".ts", resolved + ".jsx", resolved + ".tsx",
            resolved + "/index.js", resolved + "/index.ts",
            resolved + ".vue",  # Vue import
        ]
        for fp in all_file_paths:
            normalized = fp.replace("\\", "/")
            if normalized in candidates or normalized == resolved:
                return fp

    return None


def _resolve_ts_call(
    call: dict,
    source_file: str,
    import_map: dict[str, str],
    analyses: dict[str, _FILE_ANALYSIS],
) -> Optional[dict]:
    """将单个调用表达式匹配到目标文件的目标函数."""
    call_name = call.get("name", "")
    call_line = call.get("line", 0)

    if call["type"] == "direct":
        # 直接调用: 查找 import_map
        if call_name in import_map:
            target_file = import_map[call_name]
            if target_file in analyses:
                target_exports = analyses[target_file].get("exports", [])
                if call_name in target_exports:
                    return {
                        "source_file": source_file,
                        "source_line": call_line,
                        "target_file": target_file,
                        "target_function": call_name,
                        "call_name": call_name,
                    }

        # 全局匹配（可能是不在 import 中的同名函数）
        for candidate_file, analysis in analyses.items():
            if candidate_file == source_file:
                continue
            if call_name in analysis.get("exports", []):
                return {
                    "source_file": source_file,
                    "source_line": call_line,
                    "target_file": candidate_file,
                    "target_function": call_name,
                    "call_name": call_name,
                }

    elif call["type"] == "attribute":
        call_module = call.get("module", "")
        if call_module in import_map:
            target_file = import_map[call_module]
            if target_file in analyses:
                target_exports = analyses[target_file].get("exports", [])
                call_attr = call.get("attr", "")
                if call_attr in target_exports:
                    return {
                        "source_file": source_file,
                        "source_line": call_line,
                        "target_file": target_file,
                        "target_function": call_attr,
                        "call_name": call_name,
                    }

    return None


# ──────────────────────────────────────────────
#  tree-sitter 树遍历工具
# ──────────────────────────────────────────────


def _walk_nodes(root, target_type: Optional[str] = None):
    """递归遍历 tree-sitter 树，yield 匹配类型的节点."""
    stack = [root]
    while stack:
        node = stack.pop()
        if target_type is None or node.type == target_type:
            yield node
        for child in node.children:
            stack.append(child)


def _find_child_by_field(node, field_name: str):
    """查找节点的指定 field 子节点."""
    # tree-sitter 0.26 API: node.child_by_field_name()
    if hasattr(node, "child_by_field_name"):
        return node.child_by_field_name(field_name)
    # 回退：手动遍历
    for child in node.children:
        if hasattr(child, "field_name") and child.field_name == field_name:
            return child
    return None


def _extract_module_path(source_node) -> str:
    """从 tree-sitter source/string 节点提取模块路径."""
    if hasattr(source_node, "text"):
        text = source_node.text.decode("utf-8")
        return text.strip("'\" ")

    # 回退: 从子节点获取
    for child in source_node.children:
        if child.type == "string_fragment" and hasattr(child, "text"):
            return child.text.decode("utf-8").strip("'\" ")
        elif child.type == "string" and hasattr(child, "text"):
            text = child.text.decode("utf-8")
            return text.strip("'\" ")

    return ""


# ── CLI 测试 ──

if __name__ == "__main__":
    import json

    logging.basicConfig(level=logging.INFO)

    # 模拟多文件项目
    test_files = {
        "UserService.java": """
package com.example.service;
import com.example.repository.UserRepository;
import com.example.model.User;

public class UserService {
    private UserRepository repo;
    public User createUser(String name) {
        return repo.save(new User(name));
    }
}
""".strip(),
        "UserRepository.java": """
package com.example.repository;
import com.example.model.User;

public class UserRepository {
    public User save(User user) {
        // DB save
        return user;
    }
    public User findById(Long id) {
        return new User("test");
    }
}
""".strip(),
        "App.vue": """
<script setup>
import { ref } from 'vue';
import { fetchLabs } from './api';

const labs = ref([]);
fetchLabs().then(data => labs.value = data);
</script>
""".strip(),
        "api.js": """
import axios from 'axios';

export function fetchLabs() {
    return axios.get('/api/labs');
}
""".strip(),
    }

    result = build_multi_lang_call_graph(test_files)
    print(json.dumps(result, indent=2, ensure_ascii=False))
