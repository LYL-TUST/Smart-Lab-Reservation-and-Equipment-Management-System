"""
AI Code Reviewer — 跨文件上下文注入器.

将 build_call_graph() 输出的调用图边信息，注入到各文件的审查 Prompt 中，
使 LLM 在审查单个文件时能感知到它在 PR 其他文件中被调用的上下文。

面试金句：
"从'单文件上下文压缩'升级到'基于依赖图的全局分析'——让 LLM 看到调用链。"

核心函数:
    inject_cross_file_context(file_path, original_content, call_graph, function_sources) -> str
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)

# 注入块的标记
INJECTION_BLOCK_HEADER = (
    "\n\n"
    "---- 8< ----\n"
    "[Cross-File Context: 以下函数/方法来自本 PR 的其他文件，已变更，请注意调用兼容性]\n"
)
INJECTION_BLOCK_FOOTER = "\n---- 8< ----\n"
FALLBACK_PLACEHOLDER = "<该函数已变更，变更内容不可用>"

# 多语言函数/方法定义模式（用于行号提示）
_FUNC_DEF_PATTERNS = [
    r"^\s*(def |async def |public |private |protected |static |function |export function |const \w+ = \()",
    r"^\s*(class |interface |enum )",
]


def inject_cross_file_context(
    file_path: str,
    original_content: str,
    call_graph: dict,
    function_sources: dict[str, dict[str, str]],
) -> str:
    """为当前审查文件注入跨文件调用上下文。

    如果当前文件调用了其他 PR 文件中被修改的函数，
    将被调函数的变更上下文注入到审查 prompt 末尾。

    Args:
        file_path: 当前正在审查的文件路径（如 "fastapi/app.py"）
        original_content: 原始 diff 或 AST 压缩后的内容（将被注入）
        call_graph: build_call_graph() 的输出，含 edges 列表
        function_sources: {文件路径: {函数名: 源码片段}} 的嵌套字典

    Returns:
        注入后的审查内容（无调用时返回原内容不变）
    """
    edges = call_graph.get("edges", [])
    if not edges:
        return original_content

    # 筛选出以当前文件为调用源的边
    relevant_edges = [
        e for e in edges if e.get("source_file") == file_path
    ]
    if not relevant_edges:
        return original_content

    # 构建注入块
    blocks: list[str] = []
    seen_targets: set[tuple[str, str]] = set()  # 去重 (target_file, target_func)

    for edge in relevant_edges:
        target_file = edge.get("target_file", "?")
        target_func = edge.get("target_function", "?")
        key = (target_file, target_func)

        if key in seen_targets:
            continue
        seen_targets.add(key)

        source = _lookup_function_source(
            function_sources, target_file, target_func,
        )
        call_name = edge.get("call_name", target_func)

        block = _format_injection_block(
            target_file, target_func, call_name, source,
        )
        if block:
            blocks.append(block)

    if not blocks:
        return original_content

    # 拼接注入内容
    injected = (
        original_content.rstrip()
        + INJECTION_BLOCK_HEADER
        + "\n".join(blocks)
        + INJECTION_BLOCK_FOOTER
    )

    logger.info(
        "已注入 %d 个跨文件上下文 (file=%s, edges=%d)",
        len(blocks), file_path, len(relevant_edges),
    )

    return injected


# ──────────────────────────────────────────────
#  辅助函数
# ──────────────────────────────────────────────


def _lookup_function_source(
    function_sources: dict[str, dict[str, str]],
    target_file: str,
    target_func: str,
) -> str | None:
    """在 function_sources 中查找目标函数的源码。"""
    file_sources = function_sources.get(target_file)
    if file_sources is None:
        return None
    return file_sources.get(target_func)


def _format_injection_block(
    target_file: str,
    target_func: str,
    call_name: str,
    source: str | None,
) -> str | None:
    """格式化单条注入块。"""
    if source:
        # 只取前 10 行，防止注入内容过大
        source_lines = source.split("\n")
        if len(source_lines) > 10:
            source_lines = source_lines[:10]
            source_lines.append("    ...")
        source_text = "\n".join(source_lines)
    else:
        source_text = FALLBACK_PLACEHOLDER

    # 提取行号（从源码首行推测，非精确）
    line_hint = ""
    if source:
        # 多语言函数定义模式匹配
        import re
        lines = source.split("\n")
        for i, line in enumerate(lines):
            stripped = line.lstrip()
            # Python: def/async def/class
            # Java: public/private/protected/static/class
            # JS/TS: function/export function/const xxx = (/
            if any(
                stripped.startswith(prefix)
                for prefix in ("def ", "async def ", "class ", "public ", "private ",
                               "protected ", "static ", "function ", "export function ",
                               "const ", "let ", "var ", "interface ", "enum ")
            ):
                line_hint = " (附近行)"
                break

    return (
        f"  {target_file} → {target_func}(){line_hint}:\n"
        f"    调用名: {call_name}\n"
        f"    {source_text}\n"
    )


# ── CLI 测试入口 ──

if __name__ == "__main__":
    import json
    import sys

    logging.basicConfig(level=logging.INFO)

    # 构造演示数据
    demo_call_graph = {
        "edges": [
            {
                "source_file": "app.py",
                "source_line": 10,
                "target_file": "utils.py",
                "target_function": "validate_email",
                "call_name": "validate_email",
            },
            {
                "source_file": "app.py",
                "source_line": 25,
                "target_file": "utils.py",
                "target_function": "send_mail",
                "call_name": "send_mail",
            },
        ],
        "file_count": 2,
        "edge_count": 2,
    }

    demo_function_sources = {
        "utils.py": {
            "validate_email": "def validate_email(email: str) -> bool:\n"
                              "    \"\"\"验证邮箱格式。新增域名白名单检查。\"\"\"\n"
                              "    domain = email.split('@')[-1]\n"
                              "    if domain not in ALLOWED_DOMAINS:\n"
                              "        return False\n"
                              "    return bool(re.match(r'\\S+@\\S+', email))\n",
            "send_mail": "def send_mail(to: str, body: str) -> None:\n"
                         "    \"\"\"发送邮件。新增了重试机制。\"\"\"\n"
                         "    for attempt in range(3):\n"
                         "        try:\n"
                         "            _smtp.send(to, body)\n"
                         "            break\n"
                         "        except Exception:\n"
                         "            continue\n",
        },
    }

    original = "def register_user(name, email):\n    if not validate_email(email):\n        raise ValueError('invalid email')"

    result = inject_cross_file_context(
        "app.py", original, demo_call_graph, demo_function_sources,
    )

    print(result)
