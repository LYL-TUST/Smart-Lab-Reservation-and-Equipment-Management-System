"""
AI Code Reviewer - Diff 文件解析模块

使用 unidiff 库将 Git diff 解析为结构化字典。
是整个审查管线的第一段：diff → 结构化数据。
"""

import os
import re
import logging
from typing import Optional

import unidiff

logger = logging.getLogger(__name__)


class DiffParseError(Exception):
    """自定义异常：diff 解析失败时抛出。"""

    def __init__(self, message: str, source: Optional[str] = None):
        self.source = source
        super().__init__(f"[DiffParseError] {message}" + (f" (source: {source})" if source else ""))


def _extract_pr_id(source: str) -> str:
    """
    从文件路径或字符串中提取 PR 标识符。

    规则：
    - test_data/pr_a.diff → pr_a
    - pr_123.diff → pr_123
    - diff-2024-01-01 → diff-2024-01-01
    - 无法提取时返回 "unknown"
    """
    basename = os.path.basename(source)
    # 去掉 .diff / .patch 后缀
    name, ext = os.path.splitext(basename)
    if ext in (".diff", ".patch"):
        return name
    # 如果是纯字符串内容，取前 20 个字符做标识
    if len(source) > 20:
        return "unknown"
    return source


def _determine_file_status(patched_file: unidiff.PatchedFile) -> str:
    """根据 PatchedFile 的属性确定文件变更状态。"""
    if patched_file.is_added_file:
        return "added"
    if patched_file.is_removed_file:
        return "deleted"
    if patched_file.is_modified_file:
        return "modified"
    # rename 实际上也是 modified 的一种
    if patched_file.is_rename:
        return "modified"
    return "modified"


def parse_diff(diff_content: str, source: Optional[str] = None) -> dict:
    """
    将 diff 文本解析为结构化字典。

    Args:
        diff_content: Git diff 的完整文本内容（或 .diff 文件路径 —— 函数会自动检测并读取）
        source: 可选的来源标识（文件路径等），用于错误提示和 PR ID 提取

    Returns:
        符合以下结构的字典：
        {
            "files": [
                {
                    "path": "fastapi/app.py",
                    "status": "modified",
                    "additions": 45,
                    "deletions": 12,
                    "hunks": [
                        {
                            "source_start": 100,
                            "source_len": 30,
                            "target_start": 100,
                            "target_len": 45,
                            "content": "@@ -100,30 +100,45 @@\\n ..."
                        }
                    ]
                }
            ],
            "stats": {
                "total_files": 5,
                "total_additions": 200,
                "total_deletions": 80,
                "pr_id": "pr_a"
            },
            "pr_title": "",
            "pr_description": ""
        }

    Raises:
        DiffParseError: 当解析失败时抛出
    """
    # ---- 参数校验 ----
    if not diff_content or not diff_content.strip():
        raise DiffParseError("输入的 diff 内容为空", source=source)

    # ---- 解析 diff ----
    try:
        patch_set = unidiff.PatchSet.from_string(diff_content)
    except Exception as e:
        raise DiffParseError(f"unidiff 解析失败: {e}", source=source) from e

    # ---- 校验解析结果 ----
    if len(patch_set) == 0:
        raise DiffParseError("解析结果为空，输入可能不是有效的 diff 格式", source=source)

    # ---- 提取 PR ID ----
    pr_id = "unknown"
    if source:
        pr_id = _extract_pr_id(source)

    # ---- 构建结构化输出 ----
    files = []
    total_additions = 0
    total_deletions = 0

    for patched_file in patch_set:
        hunks = []
        for hunk in patched_file:
            hunks.append({
                "source_start": hunk.source_start,
                "source_len": hunk.source_length,
                "target_start": hunk.target_start,
                "target_len": hunk.target_length,
                "content": str(hunk),
            })

        file_info = {
            "path": patched_file.path,
            "status": _determine_file_status(patched_file),
            "additions": patched_file.added,
            "deletions": patched_file.removed,
            "hunks": hunks,
        }
        files.append(file_info)
        total_additions += patched_file.added
        total_deletions += patched_file.removed

    return {
        "files": files,
        "stats": {
            "total_files": len(files),
            "total_additions": total_additions,
            "total_deletions": total_deletions,
            "pr_id": pr_id,
        },
        "pr_title": "",
        "pr_description": "",
    }


def parse_diff_file(file_path: str) -> dict:
    """
    便利函数：直接读取 .diff 文件并解析。

    Args:
        file_path: .diff 文件的路径

    Returns:
        与 parse_diff() 相同的结构化字典
    """
    if not os.path.isfile(file_path):
        raise DiffParseError(f"文件不存在: {file_path}", source=file_path)

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception as e:
        raise DiffParseError(f"读取文件失败: {e}", source=file_path) from e

    return parse_diff(content, source=file_path)


# ---- CLI 快捷入口 ----
if __name__ == "__main__":
    import argparse
    import json

    parser = argparse.ArgumentParser(description="解析 Git diff 文件")
    parser.add_argument("diff_file", help=".diff 文件路径")
    parser.add_argument("--pretty", action="store_true", help="美化 JSON 输出")
    args = parser.parse_args()

    try:
        result = parse_diff_file(args.diff_file)
        indent = 2 if args.pretty else None
        # 确保中文等字符正常显示
        print(json.dumps(result, indent=indent, ensure_ascii=False))
    except DiffParseError as e:
        print(f"错误: {e}")
        exit(1)
