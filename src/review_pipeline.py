"""
AI Code Reviewer - 审查管线模块

串联 diff_parser → (AST 压缩) → llm_reviewer → Markdown 报告生成。
是整个 CLI 的中间调度层。

核心函数:
    review_pr(diff_path, config, dry_run, compress) -> str  # 返回 Markdown 报告

AST 压缩模式:
    当 compress="ast" 时，在送审前用 src.ast_context 提取变更函数上下文，
    大幅减少传给 LLM 的 token 数量（预期 50-65%）。
"""

import json
import logging
import os
import re
import time
from typing import Optional

from src.diff_parser import parse_diff_file, DiffParseError
from src.llm_reviewer import review_file
from src.ast_context import extract_function_context, _fallback_extract
from src.rules_engine import filter_issues, load_rules
from src.dedup_cache import ReviewCache
from src.language_detector import is_python, detect_language

logger = logging.getLogger(__name__)

# MCP 模式标记
_MCP_CLIENT = None  # 延迟初始化，避免在没有 MCP 的 env 中导入失败


def _get_mcp_client():
    """延迟加载 MCP 客户端（仅当 use_mcp=True 时）。"""
    global _MCP_CLIENT
    if _MCP_CLIENT is None:
        from src.mcp_client import McpToolClient
        _MCP_CLIENT = McpToolClient
    return _MCP_CLIENT


# ──────────────────────────────────────────────
#  辅助: 从原始 diff 中按文件拆分
# ──────────────────────────────────────────────

def _split_raw_diff(raw_diff: str) -> dict[str, str]:
    """
    将原始 diff 文本按文件拆分成 {file_path: diff_content} 的映射。

    例如:
    {
        "fastapi/app.py": "diff --git a/fastapi/app.py b/fastapi/app.py\n...",
        "tests/test_app.py": "diff --git a/tests/test_app.py b/tests/test_app.py\n...",
    }
    """
    # diff --git 行之前可能有头信息，我们需要从第一个 diff --git 开始切
    parts = re.split(r'\n(?=diff --git )', raw_diff.strip())
    result = {}

    for part in parts:
        part = part.strip()
        if not part:
            continue

        # 从 b/ 路径提取目标文件路径
        match = re.search(r'^diff --git a/(.*?) b/(.*?)$', part, re.MULTILINE)
        if match:
            path = match.group(2)
            result[path] = part
        elif part.startswith("diff --git "):
            logger.warning("无法从 diff 片段中提取文件路径，已跳过")
        # else: commit preamble / email headers → 静默跳过

    return result


# ──────────────────────────────────────────────
#  辅助: Markdown 报告生成
# ──────────────────────────────────────────────

_SEVERITY_ICON = {
    "critical": "🔴",
    "warning": "🟡",
    "suggestion": "💡",
}


# 文件扩展名 → 代码块语言标签映射
_CODE_BLOCK_LANG = {
    ".py": "python", ".pyi": "python",
    ".java": "java",
    ".js": "javascript", ".jsx": "jsx", ".mjs": "javascript", ".cjs": "javascript",
    ".ts": "typescript", ".tsx": "tsx",
    ".vue": "vue",
    ".go": "go", ".rs": "rust", ".cpp": "cpp", ".c": "c", ".h": "c",
}


def _get_code_block_lang(file_path: str) -> str:
    """根据文件扩展名返回 Markdown 代码块语言标签."""
    import os
    ext = os.path.splitext(file_path)[1].lower()
    return _CODE_BLOCK_LANG.get(ext, "")


def _should_skip_review(file_path: str) -> bool:
    """检查是否应跳过审查（自动生成/锁文件/配置模板/二进制等）."""
    basename = os.path.basename(file_path)
    ext = os.path.splitext(file_path)[1].lower()

    # 包管理器锁文件（npm/yarn/pip/cargo 等自动生成）
    if basename in ("package-lock.json", "yarn.lock", "pnpm-lock.yaml",
                    "Gemfile.lock", "Cargo.lock", "poetry.lock",
                    "Pipfile.lock", "composer.lock", "pubspec.lock"):
        return True

    # 环境变量模板 / git 配置 / 开源许可（无审查价值的模板文件）
    if basename in (".env.example", ".env.template", "env.example",
                    ".gitignore", "LICENSE", "LICENSE.md", "NOTICE"):
        return True

    # 二进制/非文本文件
    if ext in (".docx", ".xlsx", ".pptx", ".pdf", ".zip", ".tar", ".gz",
               ".png", ".jpg", ".jpeg", ".gif", ".ico",
               ".woff", ".woff2", ".ttf", ".eot", ".mp4", ".mp3"):
        return True

    # 压缩/编译产物
    if ext in (".min.js", ".min.css", ".map", ".pyc", ".pyo", ".class"):
        return True

    return False


def _generate_markdown_report(
    parsed: dict,
    review_results: list[dict],
    summary_stats: dict,
) -> str:
    """
    生成结构化的 Markdown 审查报告。
    """
    lines = []

    # ── 标题 ──
    pr_id = parsed["stats"]["pr_id"]
    lines.append(f"# AI Code Review Report — {pr_id}")
    lines.append("")

    # ── 概览表 ──
    lines.append("## 概览")
    lines.append("")
    lines.append("| 文件 | 状态 | 变更行数 | 问题数 |")
    lines.append("|------|------|---------|--------|")

    for f in parsed["files"]:
        path = f["path"]
        status = f["status"]
        additions = f["additions"]
        deletions = f["deletions"]
        # 找到对应审查结果
        result = _find_review_result(path, review_results)
        issue_count = len(result.get("issues", [])) if result else 0
        degraded_marker = " ⚠️" if (result and result.get("degraded")) else ""
        cached_marker = " 📦" if (result and result.get("cached")) else ""
        lines.append(f"| `{path}` | {status} | +{additions} / -{deletions} | {issue_count}{degraded_marker}{cached_marker} |")

    lines.append("")
    lines.append(
        f"**总计**: 审查 {summary_stats['files_reviewed']} 个文件，"
        f"共发现 {summary_stats['total_issues']} 个问题 "
        f"(Critical: {summary_stats['critical']}, "
        f"Warning: {summary_stats['warning']}, "
        f"Suggestion: {summary_stats['suggestion']})"
    )
    lines.append("")

    # ── 详细审查结果 ──
    lines.append("---")
    lines.append("")
    lines.append("## 详细审查结果")
    lines.append("")

    has_issues = False
    for f in parsed["files"]:
        path = f["path"]
        result = _find_review_result(path, review_results)
        issues = result.get("issues", []) if result else []

        if not issues:
            if result and result.get("degraded"):
                status_badge = "⚠️ 审查降级 (Mock 模式)"
            elif result and result.get("cached"):
                status_badge = "📦 缓存命中"
            elif result and result.get("error"):
                status_badge = "❌ 审查失败"
            else:
                status_badge = "✅ 未发现问题"
            lines.append(f"### `{path}` — {status_badge}")
            lines.append("")
            continue

        has_issues = True
        # 统计该文件的严重级别分布
        c = sum(1 for i in issues if i.get("severity") == "critical")
        w = sum(1 for i in issues if i.get("severity") == "warning")
        s = sum(1 for i in issues if i.get("severity") == "suggestion")
        sev_labels = []
        if c:
            sev_labels.append(f"Critical: {c}")
        if w:
            sev_labels.append(f"Warning: {w}")
        if s:
            sev_labels.append(f"Suggestion: {s}")

        lines.append(f"### `{path}` ({', '.join(sev_labels)})")
        lines.append("")

        for idx, issue in enumerate(issues):
            severity = issue.get("severity", "suggestion")
            category = issue.get("category", "general")
            title = issue.get("title", "未命名问题")
            icon = _SEVERITY_ICON.get(severity, "•")
            line_num = issue.get("line", "")
            line_str = f"第 {line_num} 行" if line_num else "未知位置"

            lines.append(f"**{icon} [{severity.capitalize()}] [{category.capitalize()}]** {title}")
            lines.append(f"- 位置：{line_str}")
            desc = issue.get("description", "")
            if desc:
                lines.append(f"- 描述：{desc}")
            suggestion = issue.get("suggestion", "")
            if suggestion:
                lines.append(f"- 建议：{suggestion}")
            code = issue.get("code_reference", "")
            if code:
                # 根据文件扩展名选择代码块语言标签
                lang_label = _get_code_block_lang(path)
                lines.append(f"- 代码引用：")
                lines.append(f"  ```{lang_label}")
                lines.append(f"  {code}")
                lines.append(f"  ```")
            # 问题之间空行
            lines.append("")

    if not has_issues:
        lines.append("本次审查未发现任何问题，代码质量良好。 🎉")
        lines.append("")

    # ── 按严重级别统计 ──
    lines.append("---")
    lines.append("")
    lines.append("## 按严重级别统计")
    lines.append("")
    lines.append(f"- 🔴 Critical: {summary_stats['critical']}")
    lines.append(f"- 🟡 Warning: {summary_stats['warning']}")
    lines.append(f"- 💡 Suggestion: {summary_stats['suggestion']}")
    lines.append("")

    # ── 失败文件列表（如有） ──
    failed = [r for r in review_results if r.get("error")]
    if failed:
        lines.append("## ⚠️ 审查失败的文件")
        lines.append("")
        for f in failed:
            lines.append(f"- `{f['file']}`: {f.get('error_info', f.get('summary', '未知错误'))}")
        lines.append("")

    return "\n".join(lines)


def _find_review_result(file_path: str, review_results: list[dict]) -> Optional[dict]:
    """在审查结果列表中查找对应文件的审查结果。"""
    for r in review_results:
        if r.get("file") == file_path:
            return r
    return None


def _aggregate_stats(parsed: dict, review_results: list[dict]) -> dict:
    """汇总审查统计信息。"""
    total_issues = 0
    critical = 0
    warning = 0
    suggestion = 0
    files_reviewed = 0

    for f in parsed["files"]:
        path = f["path"]
        result = _find_review_result(path, review_results)
        if result and not result.get("error"):
            files_reviewed += 1
            issues = result.get("issues", [])
            total_issues += len(issues)
            for issue in issues:
                sev = issue.get("severity", "suggestion")
                if sev == "critical":
                    critical += 1
                elif sev == "warning":
                    warning += 1
                else:
                    suggestion += 1

    return {
        "total_issues": total_issues,
        "critical": critical,
        "warning": warning,
        "suggestion": suggestion,
        "files_reviewed": files_reviewed,
    }


# ──────────────────────────────────────────────
#  核心管线函数
# ──────────────────────────────────────────────

def review_pr(
    diff_path: str,
    config: Optional[dict] = None,
    dry_run: bool = False,
    compress: str = "none",
    use_mcp: bool = False,
    use_cache: bool = True,
    enable_degrade: bool = True,
) -> str:
    """
    审查一个 PR diff 文件，返回 Markdown 报告。

    Args:
        diff_path: .diff 文件路径
        config: LLM 配置（含 api_key 等），dry_run=True 时可传 None
        dry_run: 为 True 时使用模拟审查（不调用实际 API）
        compress: 压缩模式 ("none" | "ast")
        use_mcp: 为 True 时通过 MCP 协议发现和调用工具，
                 而非直接 import。工具在运行时发现而非编译时绑定。

    Returns:
        str: 完整的 Markdown 审查报告

    Raises:
        DiffParseError: diff 文件解析失败
        ValueError: 非 dry_run 但未提供 config
    """
    logger.info(
        "开始审查: %s (dry_run=%s, compress=%s, mcp=%s)",
        diff_path, dry_run, compress, use_mcp,
    )

    if not dry_run and config is None:
        raise ValueError("非 dry-run 模式需要提供 config 参数")

    # ── Step 1: 读取原始 diff 文本 ──
    if not os.path.isfile(diff_path):
        raise FileNotFoundError(f"diff 文件不存在: {diff_path}")

    with open(diff_path, "r", encoding="utf-8") as f:
        raw_diff = f.read()

    # ── Step 2: 解析 diff 获得结构化数据 ──
    if use_mcp:
        # MCP 模式：创建 MCP 客户端 → 发现工具 → 通过路由调用
        from src.mcp_client import create_mcp_client
        mcp_client = create_mcp_client(use_local=True)

        parsed_str = mcp_client.call("parse_git_diff", {"diff_path": diff_path})
        parsed = parsed_str  # LocalRegistryClient 已做 JSON 解析
        if "error" in parsed:
            raise DiffParseError(parsed["error"], source=diff_path)
    else:
        try:
            parsed = parse_diff_file(diff_path)
        except DiffParseError:
            logger.warning("unidiff 解析失败，降级为正则拆分: %s", diff_path)
            parsed = _build_fallback_parsed(raw_diff, diff_path)
    file_count = parsed["stats"]["total_files"]
    logger.info("解析完成: %d 个文件", file_count)

    # ── Step 3: 按文件拆分 diff ──
    file_diffs = _split_raw_diff(raw_diff)

    # ── Step 3.5: 提取本 commit 的文件间兄弟关系（消除 "模块不存在" 误报） ──
    sibling_exports = _build_sibling_exports(parsed["files"], file_diffs)

    # ── Step 4: 逐文件审查 ──
    review_results: list[dict] = []
    compress_stats: list[dict] = []

    # 去重缓存 + 降级状态
    cache = ReviewCache()
    if not use_cache:
        cache.disable()
    degrade_threshold = 0.5
    error_count = 0
    processed_count = 0
    global_degraded = False

    for idx, file_info in enumerate(parsed["files"]):
        file_path = file_info["path"]
        file_diff = file_diffs.get(file_path, "")

        if not file_diff:
            logger.warning("未找到文件 %s 的 diff 内容，跳过", file_path)
            review_results.append({
                "file": file_path,
                "issues": [],
                "summary": "No diff content available",
                "error": True,
                "error_info": "无法从原始 diff 中提取该文件的变更内容",
            })
            continue

        # 跳过自动生成/锁文件（不浪费 token）
        if _should_skip_review(file_path):
            logger.info("  [%d/%d] 跳过自动生成文件: %s", idx + 1, file_count, file_path)
            review_results.append({
                "file": file_path,
                "issues": [],
                "summary": "Skipped (auto-generated file)",
                "error": False,
                "skipped": True,
            })
            compress_stats.append({
                "file": file_path,
                "raw_tokens": _estimate_tokens(file_diff),
                "compressed_tokens": _estimate_tokens(file_diff),
            })
            continue

        # 统计原始 diff token 数
        raw_tokens = _estimate_tokens(file_diff)

        # AST 压缩（可选）
        content_to_review = file_diff
        compressed_tokens = raw_tokens

        if compress == "ast":
            content_to_review, compressed_tokens = _compress_with_ast(
                file_path, file_info, file_diff,
                mcp_client=mcp_client if use_mcp else None,
            )

        logger.info(
            "[%d/%d] 审查文件: %s (tokens: %d->%d)%s",
            idx + 1, file_count, file_path,
            raw_tokens, compressed_tokens,
            " [降级-Mock]" if global_degraded else "",
        )

        # 注入同 commit 兄弟文件上下文（消除 "模块不存在" 误报）
        if sibling_exports and compress == "ast":
            content_to_review = _inject_sibling_context(
                content_to_review, file_path, sibling_exports,
            )

        # 去重缓存检查（仅 live 模式）
        cache_hit = False
        model = config.get("model", "unknown") if config else "mock"
        cache_key = cache.make_key(model, file_path, content_to_review)

        if not dry_run and not global_degraded:
            cached = cache.get(cache_key)
            if cached:
                logger.info("  缓存命中 — 跳过 LLM 调用: %s (%s)", file_path, model)
                review_results.append({
                    "file": file_path,
                    "issues": cached.get("issues", []),
                    "summary": cached.get("summary", ""),
                    "error": False,
                    "cached": True,
                })
                compress_stats.append({
                    "file": file_path,
                    "raw_tokens": raw_tokens,
                    "compressed_tokens": compressed_tokens,
                })
                continue

        if dry_run or global_degraded:
            result = _mock_review(file_path, content_to_review)
            if global_degraded:
                result["degraded"] = True
        else:
            processed_count += 1
            result = review_file(file_path, content_to_review, config)

            if result.get("error"):
                error_count += 1
                # L1 单文件降级
                if enable_degrade:
                    logger.warning(
                        "  LLM 审查失败，降级到 Mock: %s", file_path
                    )
                    mock_result = _mock_review(file_path, content_to_review)
                    mock_result["degraded"] = True
                    mock_result["original_error"] = result.get(
                        "error_info", result.get("summary", "LLM error")
                    )
                    result = mock_result
                # 检查是否需要全局降级
                if (error_count / max(processed_count, 1)) >= degrade_threshold:
                    logger.warning(
                        "  全局降级触发！%d/%d 文件失败 (%.0f%%)，剩余文件走 Mock",
                        error_count, processed_count,
                        error_count / processed_count * 100,
                    )
                    global_degraded = True
            else:
                # 成功 — 写缓存
                cache.set(cache_key, result, file_path=file_path, model=model)

        review_results.append(result)
        compress_stats.append({
            "file": file_path,
            "raw_tokens": raw_tokens,
            "compressed_tokens": compressed_tokens,
        })

        # 避免 API 频率过快
        if not dry_run and idx < file_count - 1:
            time.sleep(0.5)

    # ── Step 4.5: 规则引擎过滤 ──
    if use_mcp:
        # MCP 模式：通过 MCP 客户端路由调用规则引擎
        import json as json_mod
        for result in review_results:
            if result.get("error"):
                continue
            file_path = result.get("file", "")
            issues = result.get("issues", [])
            if not issues:
                continue
            filtered = mcp_client.call("filter_code_review_issues", {
                "issues": json_mod.dumps(issues),
                "file_path": file_path,
            })
            result["issues"] = filtered.get("passed", [])
        summary_stats = _aggregate_stats(parsed, review_results)

    else:
        rules = load_rules()
        total_before = 0
        total_after = 0
        total_filtered = 0
        total_downgraded = 0

        for result in review_results:
            if result.get("error"):
                continue
            file_path = result.get("file", "")
            issues = result.get("issues", [])
            total_before += len(issues)

            filtered = filter_issues(issues, file_path=file_path, rules=rules)
            result["issues"] = filtered["passed"]
            total_after += len(filtered["passed"])
            total_filtered += filtered["filtered_count"]
            total_downgraded += filtered["downgraded_count"]

            if filtered["filtered_count"] > 0 or filtered["downgraded_count"] > 0:
                logger.info(
                    "规则过滤 (file=%s): %d filtered, %d downgraded (rules: %s)",
                    file_path,
                    filtered["filtered_count"],
                    filtered["downgraded_count"],
                    ", ".join(filtered["applied_rules"]) or "-",
                )

        if total_filtered > 0 or total_downgraded > 0:
            logger.info(
                "规则引擎汇总: %d issues → %d (%d filtered, %d downgraded)",
                total_before, total_after, total_filtered, total_downgraded,
            )

        # ── Step 5: 汇总统计 ──
        summary_stats = _aggregate_stats(parsed, review_results)

    # ── Step 6: 生成 Markdown 报告 ──
    report = _generate_markdown_report(parsed, review_results, summary_stats)

    logger.info(
        "审查完成: %d 个文件, %d 个问题 (C:%d W:%d S:%d)",
        summary_stats["files_reviewed"],
        summary_stats["total_issues"],
        summary_stats["critical"],
        summary_stats["warning"],
        summary_stats["suggestion"],
    )

    return report


def _estimate_tokens(text: str) -> int:
    """粗略估算 token 数量（按 4 字符 = 1 token）。"""
    return max(1, len(text) // 4)


def _build_sibling_exports(
    files: list[dict],
    file_diffs: dict[str, str],
) -> dict[str, list[str]]:
    """扫描同 commit 所有文件的导出符号。

    消除 "模块不存在" 误报：当 LLM 审查 app.py 看到
    `from src.arxiv_tool import ...` 时，如果 src/arxiv_tool.py
    也在这个 commit 里，提前告知 LLM 它的导出列表。

    Returns:
        {file_path: ["exported_func1", "exported_func2", ...]}
    """
    if len(files) <= 1:
        return {}  # 只有 1 个文件，不需要兄弟上下文

    sibling_exports: dict[str, list[str]] = {}

    for file_info in files:
        file_path = file_info["path"]
        if _should_skip_review(file_path):
            continue

        diff_content = file_diffs.get(file_path, "")
        if not diff_content.strip():
            continue

        try:
            source_code, _ = _reconstruct_from_diff(diff_content, file_info)
        except Exception:
            continue

        if not source_code:
            continue

        # 提取导出符号
        exports = _quick_extract_exports(source_code, file_path)
        if exports:
            sibling_exports[file_path] = exports

    return sibling_exports


def _quick_extract_exports(source_code: str, file_path: str) -> list[str]:
    """快速提取文件的顶层导出符号名称（函数/类/常量）。

    轻量实现，不做完整 tree-sitter 解析。
    """
    if is_python(file_path):
        import ast as py_ast
        try:
            tree = py_ast.parse(source_code)
        except SyntaxError:
            return []
        exports = []
        for node in py_ast.iter_child_nodes(tree):
            if isinstance(node, (py_ast.FunctionDef, py_ast.AsyncFunctionDef, py_ast.ClassDef)):
                exports.append(node.name)
            elif isinstance(node, py_ast.Assign):
                for target in node.targets:
                    if isinstance(target, py_ast.Name) and target.id.isupper():
                        exports.append(target.id)
        return exports

    # 非 Python：用正则提取函数/类名（轻量，避免 tree-sitter 重解析）
    imports_and_exports = []
    lines = source_code.split("\n")
    for line in lines:
        stripped = line.strip()
        # JS/TS: export function/const/class
        match = re.match(
            r'(?:export\s+)?(?:async\s+)?(?:function|class)\s+(\w+)',
            stripped,
        )
        if match:
            imports_and_exports.append(match.group(1))
        # Java: public class / public void method
        match = re.match(r'public\s+(?:static\s+)?(?:class|interface|enum)\s+(\w+)', stripped)
        if match:
            imports_and_exports.append(match.group(1))
    return imports_and_exports


def _inject_sibling_context(
    content: str,
    current_file: str,
    sibling_exports: dict[str, list[str]],
) -> str:
    """注入兄弟文件上下文到审查内容中。

    格式:
        [Sibling Files: 同 commit 新增/修改的文件]
          → src/arxiv_tool.py: search_arxiv, fetch_paper
          → src/aminer_tool.py: search_aminer, get_author
    """
    siblings = {
        fp: names
        for fp, names in sibling_exports.items()
        if fp != current_file and names
    }

    if not siblings:
        return content

    # 找相关兄弟：文件名与当前文件的 import 有关联
    relevant = {}
    import re as _re
    current_lower = current_file.lower()
    for fp, names in siblings.items():
        fp_stem = _re.sub(r'\.\w+$', '', fp)  # 去掉扩展名
        fp_base = fp_stem.split("/")[-1]  # 文件名（不含路径）
        # 简单关联：如果兄弟文件名在 current_file 的路径中有关联
        # 或者导出符号只有几个（可能都被 import 了），都认为是相关
        if len(siblings) <= 5 or fp_base in current_lower or current_lower.split("/")[-1].replace(".", "") in fp:
            relevant[fp] = names

    if not relevant:
        relevant = dict(list(siblings.items())[:5])  # 取前 5 个

    lines = [
        "\n\n---- 8< ----",
        "[Sibling Files: 同 commit 的其他文件（如果当前文件 import 了这些模块，它们确实存在）]",
    ]
    for fp, names in relevant.items():
        short = fp.split("/")[-1] if "/" in fp else fp
        names_str = ", ".join(names[:8])
        if len(names) > 8:
            names_str += " ..."
        lines.append(f"  → {short}: {names_str}")

    lines.append("---- 8< ----\n")
    return content.rstrip() + "\n" + "\n".join(lines)


def _compress_with_ast(
    file_path: str,
    file_info: dict,
    file_diff: str,
    mcp_client=None,
) -> tuple[str, int]:
    """
    用 AST 压缩 diff 内容：只提取变更函数/类上下文。

    对 Python 文件使用标准库 ast 模块。
    对 Java/Vue/JS/TS 文件使用 tree-sitter 多语言解析器。
    对新增文件（status="added"）跳过压缩。

    Args:
        mcp_client: MCP 客户端（启用 MCP 模式时传入）

    Returns:
        (compressed_content, compressed_tokens)
    """
    # 新增文件：全文件源码 = diff 内容（去掉 diff 头标记），所有行为变更行
    is_added = file_info.get("status") == "added"

    # 语言检测：非代码文件直接跳过
    lang_info = detect_language(file_path)
    if lang_info.name == "General":
        logger.debug("  非代码文件，跳过 AST 压缩: %s (%s)", file_path, lang_info.extension)
        return file_diff, _estimate_tokens(file_diff)

    raw_tokens = _estimate_tokens(file_diff)

    # Python: 沿现有路径（ast 模块 + MCP 支持）
    if is_python(file_path):
        return _compress_python_ast(file_path, file_info, file_diff, raw_tokens, mcp_client)

    # 多语言: tree-sitter 压缩
    return _compress_multi_lang_ast(file_path, file_info, file_diff, raw_tokens)


def _compress_python_ast(
    file_path: str,
    file_info: dict,
    file_diff: str,
    raw_tokens: int,
    mcp_client=None,
) -> tuple[str, int]:
    """Python AST 压缩（保持原有逻辑不变）."""
    # 从 diff 中提取变更行和 target 源码
    try:
        source_code, changed_lines = _reconstruct_from_diff(file_diff, file_info)
    except Exception as e:
        logger.warning("  源码重建失败 (%s)，使用原始 diff: %s", file_path, e)
        return file_diff, raw_tokens

    if not source_code or not source_code.strip():
        logger.warning("  重建源码为空，使用原始 diff: %s", file_path)
        return file_diff, raw_tokens

    if not changed_lines:
        logger.warning("  无变更行，使用原始 diff: %s", file_path)
        return file_diff, raw_tokens

    # AST 提取（MCP 模式 vs import 模式）
    if mcp_client is not None:
        import json as json_mod
        result = mcp_client.call("extract_function_context", {
            "source_code": source_code,
            "changed_lines_json": json_mod.dumps(sorted(changed_lines)),
            "context_lines": 2,
        })
        compressed = result.get("compressed_code", "")
        if result.get("stats"):
            logger.debug(
                "  MCP AST 压缩: %s -> %s tokens (%.1f%%)",
                result["stats"]["original_tokens"],
                result["stats"]["compressed_tokens"],
                result["stats"]["compression_ratio_pct"],
            )
    else:
        compressed = extract_function_context(source_code, changed_lines, context_lines=2)

    if not compressed or not compressed.strip():
        logger.debug("  AST 提取结果为空，降级为行范围提取: %s", file_path)
        source_lines = source_code.splitlines()
        compressed = _fallback_extract(source_lines, changed_lines, context_lines=3)

    # ---- 注入文件级声明 + 局部调用图（减少截断误报） ----
    from src.ast_context import inject_python_context, inject_python_local_call_graph

    # 提取变更函数名（用于局部调用图）
    changed_func_names = _extract_changed_function_names(source_code, changed_lines, file_path)

    # 第 1 层：注入 import + 全局声明
    compressed = inject_python_context(compressed, source_code)

    # 第 2 层：注入同文件调用关系
    compressed = inject_python_local_call_graph(compressed, source_code, changed_func_names)

    compressed_tokens = _estimate_tokens(compressed)
    return compressed, compressed_tokens


def _compress_multi_lang_ast(
    file_path: str,
    file_info: dict,
    file_diff: str,
    raw_tokens: int,
) -> tuple[str, int]:
    """多语言 AST 压缩（tree-sitter，支持 Java/Vue/JS/TS）."""
    from src.multi_lang_ast import extract_context_multi_lang

    # 从 diff 中提取变更行和 target 源码
    try:
        source_code, changed_lines = _reconstruct_from_diff(file_diff, file_info)
    except Exception as e:
        logger.warning("  源码重建失败 (%s)，使用原始 diff: %s", file_path, e)
        return file_diff, raw_tokens

    if not source_code or not source_code.strip():
        logger.warning("  重建源码为空，使用原始 diff: %s", file_path)
        return file_diff, raw_tokens

    if not changed_lines:
        logger.warning("  无变更行，使用原始 diff: %s", file_path)
        return file_diff, raw_tokens

    # tree-sitter 多语言压缩
    try:
        compressed = extract_context_multi_lang(
            source_code, changed_lines, file_path, context_lines=2,
        )
    except Exception as e:
        logger.warning("  多语言 AST 压缩失败 (%s): %s，降级", file_path, e)
        source_lines = source_code.splitlines()
        compressed = _fallback_extract(source_lines, changed_lines, context_lines=3)

    if not compressed or not compressed.strip():
        logger.debug("  多语言 AST 提取结果为空，降级: %s", file_path)
        source_lines = source_code.splitlines()
        compressed = _fallback_extract(source_lines, changed_lines, context_lines=3)

    # ---- 注入文件级声明 + 局部调用图（减少截断误报） ----
    from src.multi_lang_ast import inject_file_context, inject_local_call_graph

    changed_func_names = _extract_changed_function_names(source_code, changed_lines, file_path)

    # 第 1 层：注入 import + 全局声明
    compressed = inject_file_context(compressed, source_code, file_path)

    # 第 2 层：注入同文件调用关系
    compressed = inject_local_call_graph(compressed, source_code, file_path, changed_func_names)

    compressed_tokens = _estimate_tokens(compressed)
    if compressed_tokens < raw_tokens:
        logger.debug(
            "  多语言 AST 压缩: %d -> %d tokens (%.1f%%)  [%s]",
            raw_tokens, compressed_tokens,
            (1 - compressed_tokens / raw_tokens) * 100,
            file_path,
        )
    return compressed, compressed_tokens


def _extract_changed_function_names(
    source_code: str,
    changed_lines: set[int],
    file_path: str,
) -> list[str]:
    """从变更行号中提取涉及的函数/类名称.

    Args:
        source_code: 完整源码
        changed_lines: 变更行号集合
        file_path: 文件路径

    Returns:
        函数名列表
    """
    if is_python(file_path):
        import ast
        try:
            tree = ast.parse(source_code)
        except SyntaxError:
            return []
        names = []
        for node in ast.iter_child_nodes(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                if hasattr(node, "lineno") and hasattr(node, "end_lineno"):
                    if any(node.lineno <= cl <= node.end_lineno for cl in changed_lines):
                        names.append(node.name)
        return names

    # 非 Python：用多语言 AST 提取
    from src.multi_lang_ast import _find_enclosing_nodes
    parser = get_parser_for_file(file_path) if "get_parser_for_file" in dir() else None
    if parser is None:
        from src.language_detector import get_parser_for_file as _get_pf
        parser = _get_pf(file_path)
    if parser is None:
        return []

    try:
        tree = parser.parse(source_code.encode("utf-8"))
    except Exception:
        return []

    nodes = _find_enclosing_nodes(tree.root_node, changed_lines, source_code)
    # 从节点类型/内容提取函数名
    names = []
    for _, _, node_type in nodes:
        label = node_type.replace("_declaration", "").replace("_definition", "")
        names.append(label)
    return names


def _build_fallback_parsed(raw_diff: str, diff_path: str) -> dict:
    """unidiff 解析失败时的降级方案：纯正则拆分 diff。

    从原始 diff 文本中按 `diff --git` 标记拆分文件，
    构造与 parse_diff_file 兼容的 parsed 结构。
    """
    file_diffs = _split_raw_diff(raw_diff)
    files: list[dict] = []

    for file_path, content in file_diffs.items():
        if not content.strip():
            continue
        # 粗略统计
        additions = content.count("\n+") - content.count("\n+++")
        deletions = content.count("\n-") - content.count("\n---")
        files.append({
            "path": file_path,
            "status": "modified",
            "additions": max(additions, 0),
            "deletions": max(deletions, 0),
            "hunks": [],
        })

    total_additions = sum(f["additions"] for f in files)
    total_deletions = sum(f["deletions"] for f in files)

    pr_id = os.path.basename(diff_path).replace(".diff", "")

    logger.info(
        "降级解析完成: %d 个文件 (+%d/-%d) [unidiff skip]",
        len(files), total_additions, total_deletions,
    )

    return {
        "files": files,
        "stats": {
            "pr_id": pr_id,
            "total_files": len(files),
            "total_additions": total_additions,
            "total_deletions": total_deletions,
        },
    }


def _reconstruct_from_diff(
    file_diff: str,
    file_info: dict,
) -> tuple[str, set[int]]:
    """
    从 diff 内容重建变更后的源码，并提取变更行号。

    策略：
    1. 从 diff 中提取 target 侧的所有行（上下文行 + 新增行）
    2. 记录新增行的行号

    Returns:
        (source_code, changed_line_numbers)
        source_code: 重建的 target 源码字符串
        changed_line_numbers: 变更行号集合（1-indexed）
    """
    lines = file_diff.split("\n")

    target_lines: list[str] = []
    changed_lines: set[int] = set()
    current_line = 0
    in_hunk = False

    for line in lines:
        if line.startswith("@@ "):
            # 解析 hunk header: @@ -start,len +start,len @@ ...
            match = re.match(r"@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@", line)
            if match:
                current_line = int(match.group(1))
            in_hunk = True
            continue

        if not in_hunk:
            continue

        if not line:
            continue

        marker = line[0]

        if marker == " ":
            # 上下文行：target 也有
            target_lines.append(line[1:])
            current_line += 1

        elif marker == "+":
            # 新增行
            target_lines.append(line[1:])
            changed_lines.add(current_line)  # 1-indexed
            current_line += 1

        elif marker == "-":
            # 删除行：target 没有，跳过
            pass

        elif marker == "\\":
            # no newline at end of file
            pass

    return "\n".join(target_lines), changed_lines


# ──────────────────────────────────────────────
#  模拟审查（用于 dry-run 测试）
# ──────────────────────────────────────────────

def _mock_review(file_path: str, diff_content: str) -> dict:
    """
    生成模拟审查结果，用于 dry-run 模式测试管线流程。

    支持多语言：Python / Java / Vue / JS / TS.
    """
    from src.language_detector import detect_language
    info = detect_language(file_path)
    lang = info.name

    issues = []
    lines = diff_content.split("\n")

    # 扫描新增行（+ 开头）
    added_lines = [(i, l) for i, l in enumerate(lines) if l.startswith("+") and not l.startswith("+++")]

    for line_no, line in added_lines:
        content = line[1:].strip()

        # === 通用规则（所有语言）===

        # 检查 console.log / print 语句
        if re.match(r'^\s*(console\.log|print|System\.out\.print)', content):
            issues.append({
                "line": line_no,
                "severity": "suggestion",
                "category": "style",
                "title": "避免在生产代码中使用调试输出",
                "description": f"使用了调试输出语句: `{content[:50]}`",
                "suggestion": f"建议移除或使用条件编译/日志框架替代 {'print' if 'print' in content else 'console.log'}",
                "code_reference": content[:80],
            })

        # 检查 TODO/FIXME
        if re.search(r'(TODO|FIXME|XXX|HACK)', content, re.IGNORECASE):
            issues.append({
                "line": line_no,
                "severity": "warning",
                "category": "style",
                "title": "代码中包含待办标记",
                "description": f"存在待办标记: {content[:60]}",
                "suggestion": "在合并前完成待办事项或创建 Issue 跟踪",
                "code_reference": content[:80],
            })

        # 检查裸异常捕获
        if re.match(r'^\s*except\s*:', content):
            issues.append({
                "line": line_no,
                "severity": "critical",
                "category": "correctness",
                "title": "裸 except 捕获所有异常",
                "description": "使用了裸 except 语句，会捕获包括 SystemExit 在内的所有异常",
                "suggestion": "指定具体的异常类型，如 except ValueError:",
                "code_reference": content[:80],
            })

        # 检查空 catch 块
        if re.match(r'^\s*catch\s*\(\s*\w*\s*\)\s*\{\s*\}', content):
            issues.append({
                "line": line_no,
                "severity": "warning",
                "category": "correctness",
                "title": "空的 catch 块",
                "description": "捕获异常后没有任何处理逻辑，异常被静默吞掉",
                "suggestion": "至少记录日志，或重新抛出异常",
                "code_reference": content[:80],
            })

        # === Python 专属规则 ===
        if lang == "Python":
            # 检查没有类型注解的 def
            if content.startswith("def ") and "->" not in content and ":" in content:
                func_match = re.match(r'def (\w+)\((.*)\):', content)
                if func_match and func_match.group(1) and not func_match.group(1).startswith("_"):
                    issues.append({
                        "line": line_no,
                        "severity": "suggestion",
                        "category": "style",
                        "title": "函数缺少返回类型注解",
                        "description": f"函数 `{func_match.group(1)}` 没有返回类型注解",
                        "suggestion": "建议添加 -> 返回类型",
                        "code_reference": content[:80],
                    })

        # === Java 专属规则 ===
        if lang == "Java":
            # 检查 public 方法没有 @Override
            if re.match(r'^\s*public\s+\w+\s+\w+\s*\(', content):
                issues.append({
                    "line": line_no,
                    "severity": "suggestion",
                    "category": "style",
                    "title": "公开方法建议添加 JavaDoc",
                    "description": f"新增的 public 方法: `{content[:60]}`",
                    "suggestion": "考虑添加 @param / @return JavaDoc 注释",
                    "code_reference": content[:80],
                })

        # === JS/TS 专属规则 ===
        if lang in ("JavaScript", "TypeScript", "Vue"):
            # 检查 var 使用（应使用 const/let）
            if re.match(r'^\s*var\s+', content):
                issues.append({
                    "line": line_no,
                    "severity": "suggestion",
                    "category": "style",
                    "title": "使用 var 声明变量",
                    "description": f"使用了 var: `{content[:60]}`",
                    "suggestion": "建议使用 const 或 let 替代 var",
                    "code_reference": content[:80],
                })

    summary = f"发现 {len(issues)} 个问题" if issues else "未发现明显问题"

    return {
        "file": file_path,
        "issues": issues,
        "summary": summary,
        "error": False,
    }


# ──────────────────────────────────────────────
#  CLI 快捷入口
# ──────────────────────────────────────────────

if __name__ == "__main__":
    import argparse

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    parser = argparse.ArgumentParser(description="AI Code Review Pipeline")
    parser.add_argument("--diff", required=True, help=".diff 文件路径")
    parser.add_argument("--output", "-o", help="输出报告路径")
    parser.add_argument("--dry-run", action="store_true", help="模拟审查（不调用 API）")
    parser.add_argument("--compress", choices=["none", "ast"], default="none",
                        help="上下文压缩模式")
    args = parser.parse_args()

    config = None
    if not args.dry_run:
        try:
            from src.config import load_config
            config = load_config()
        except ValueError as e:
            print(f"配置错误: {e}")
            print("提示: 使用 --dry-run 可跳过 API 调用进行管线测试")
            exit(1)

    report = review_pr(args.diff, config, dry_run=args.dry_run, compress=args.compress)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(report)
        print(f"\n✅ 报告已保存: {args.output}")
    else:
        print(report)
