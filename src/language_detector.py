"""
AI Code Reviewer - 语言检测与路由模块.

根据文件扩展名自动识别编程语言，返回对应的语言类型和
tree-sitter Language 对象（用于 AST 解析和调用图分析）。

核心函数:
    detect_language(file_path) -> LanguageInfo
    get_parser_for_file(file_path) -> Parser | None
"""

import logging
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)

# tree-sitter 语言 grammars（延迟导入）
_TS_LANGUAGES: dict[str, object] = {}
_PARSER_CACHE: dict[str, object] = {}

# ---------- 语言信息 ----------


@dataclass
class LanguageInfo:
    """语言检测结果."""
    name: str           # 语言名称（如 "Python", "Java"）
    extension: str      # 文件扩展名（如 ".py", ".java"）
    uses_ts: bool       # 是否使用 tree-sitter 解析（False = 标准库 ast）
    ts_module_name: str # tree-sitter 模块的导入路径


# 语言映射表
_LANGUAGE_MAP: dict[str, LanguageInfo] = {
    ".py": LanguageInfo("Python", ".py", False, ""),
    ".pyi": LanguageInfo("Python", ".pyi", False, ""),
    ".java": LanguageInfo("Java", ".java", True, "tree_sitter_java"),
    ".js": LanguageInfo("JavaScript", ".js", True, "tree_sitter_javascript"),
    ".jsx": LanguageInfo("JavaScript", ".jsx", True, "tree_sitter_javascript"),
    ".mjs": LanguageInfo("JavaScript", ".mjs", True, "tree_sitter_javascript"),
    ".cjs": LanguageInfo("JavaScript", ".cjs", True, "tree_sitter_javascript"),
    ".ts": LanguageInfo("TypeScript", ".ts", True, "tree_sitter_typescript"),
    ".tsx": LanguageInfo("TypeScript", ".tsx", True, "tree_sitter_typescript"),
    ".vue": LanguageInfo("Vue", ".vue", True, "tree_sitter_javascript"),
}


def detect_language(file_path: str) -> LanguageInfo:
    """根据文件路径检测编程语言.

    对 .vue 文件特殊处理：返回 JavaScript parser（Vue 的 <script> 块
    在 pipeline 层单独提取解析），但显示名称为 "Vue".

    Args:
        file_path: 文件路径（如 "src/UserService.java"）

    Returns:
        LanguageInfo 对象；未识别的扩展名返回默认值（通用文本）
    """
    import os
    ext = os.path.splitext(file_path)[1].lower()
    if ext in _LANGUAGE_MAP:
        return _LANGUAGE_MAP[ext]

    # 未知扩展名：默认返回通用信息
    logger.debug("未识别的文件扩展名: %s，使用通用模式", ext)
    return LanguageInfo("General", ext, False, "")


def is_python(file_path: str) -> bool:
    """判断文件是否为 Python 代码."""
    return file_path.endswith((".py", ".pyi"))


def get_language_name(file_path: str) -> str:
    """返回人类可读的语言名称."""
    return detect_language(file_path).name


def get_ts_language(file_path: str) -> Optional[object]:
    """获取 tree-sitter Language 对象（仅对非 Python 语言有效）.

    返回 None 表示应使用 Python 标准库 ast 模块.

    Args:
        file_path: 文件路径

    Returns:
        tree-sitter Language 对象，或 None
    """
    info = detect_language(file_path)
    if not info.uses_ts:
        return None

    if info.extension not in _TS_LANGUAGES:
        _TS_LANGUAGES[info.extension] = _load_ts_language(info)

    return _TS_LANGUAGES[info.extension]


def get_parser_for_file(file_path: str) -> Optional[object]:
    """获取 tree-sitter Parser（含缓存）.

    对 Python 文件返回 None.

    Args:
        file_path: 文件路径

    Returns:
        tree-sitter Parser 对象，或 None
    """
    ext = detect_language(file_path).extension
    if ext in _PARSER_CACHE:
        return _PARSER_CACHE[ext]

    ts_lang = get_ts_language(file_path)
    if ts_lang is None:
        return None

    from tree_sitter import Parser
    parser = Parser(ts_lang)
    _PARSER_CACHE[ext] = parser
    return parser


def _load_ts_language(info: LanguageInfo) -> object:
    """加载 tree-sitter 语言 grammar."""
    from tree_sitter import Language

    if info.extension in (".ts", ".tsx"):
        # TypeScript 使用 language_typescript()
        import tree_sitter_typescript as tsts
        return Language(tsts.language_typescript())

    if info.extension in (".js", ".jsx", ".mjs", ".cjs"):
        import tree_sitter_javascript as tsjs
        return Language(tsjs.language())

    if info.extension == ".java":
        import tree_sitter_java as tsjava
        return Language(tsjava.language())

    if info.extension == ".vue":
        # Vue 用 JavaScript parser 解析 <script> 块
        import tree_sitter_javascript as tsjs
        return Language(tsjs.language())

    raise ValueError(f"不支持的语言: {info.name} ({info.extension})")


# ---------- Vue SFC 特殊处理 ----------

_VUE_SCRIPT_RE = __import__("re").compile(
    r"<script(?:\s+setup)?(?:\s+lang=['\"]ts['\"])?\s*>(.*?)</script>",
    __import__("re").DOTALL,
)


def extract_vue_script(source_code: str) -> Optional[str]:
    """从 Vue SFC 中提取 <script> 块内容.

    Args:
        source_code: Vue 单文件组件源码

    Returns:
        script 块文本（去掉了 <script> 标签），没有 script 时返回 None
    """
    match = _VUE_SCRIPT_RE.search(source_code)
    if match:
        return match.group(1).strip()
    return None


# ---------- 调试入口 ----------

if __name__ == "__main__":
    test_files = [
        "src/main.py",
        "backend/UserController.java",
        "frontend/src/App.vue",
        "ai-server/index.js",
        "src/utils.ts",
        "README.md",
    ]
    for f in test_files:
        info = detect_language(f)
        ts_lang = get_ts_language(f)
        print(f"  {f:40s} → {info.name:12s} (ts={info.uses_ts}, obj={'✅' if ts_lang else '❌'})")
