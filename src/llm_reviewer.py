"""
AI Code Reviewer - LLM 审查核心模块

将单个文件的 diff 内容发送给 LLM（DeepSeek / OpenAI），
获取结构化的代码审查结果（JSON）。

核心函数:
    review_file(file_path, diff_content, config) -> dict
"""

import json
import logging
import time
from typing import Optional

from openai import OpenAI, APIError, APITimeoutError, RateLimitError

logger = logging.getLogger(__name__)

# ---- Prompt 定义 ----

# ---- 语言 → 专家身份映射 ----
_LANGUAGE_EXPERT_MAP = {
    "Python": "你是一个资深的 Python 代码架构师和审查专家。",
    "Java": "你是一个资深的 Java 代码架构师和审查专家（Spring Boot 生态）。",
    "JavaScript": "你是一个资深的 JavaScript/Node.js 代码审查专家。",
    "TypeScript": "你是一个资深的 TypeScript 代码架构师和审查专家。",
    "Vue": "你是一个资深的 Vue 3 前端代码审查专家（Composition API + TypeScript）。",
    "General": "你是一个资深的代码架构师和审查专家。",
}

_SAFETY_CONSTRAINTS = (
    "请根据提供的文件变更，按照 JSON 格式输出审查结果。"
    "绝对不要输出任何 Markdown 标记，只输出纯 JSON。"
    "\n\n## 安全约束\n"
    "1. 在报告任何问题之前，请先判断该修改是否改变了函数的外部接口"
    "（签名、返回值类型、异常类型）。"
    "2. 如果修改改变了外部接口，请在报告中明确标注「⚠️ 接口变更」"
    "并说明影响范围。"
    "3. 对于性能优化建议，请先确认原代码是否有副作用（I/O、状态修改）。"
    "如果有副作用，请不要建议替换。"
    "4. 如果你不确定某个修改的影响，请标注「需人工确认」"
    "而非给出确定性建议。"
    "5. 审查的代码片段是从完整文件中提取的，某些变量/函数/类型的定义"
    "可能在片段之外（以 'Injected File-Level Context' 或 'Local Call Graph' "
    "标注）。如果你能确定某个名称在文件级作用域内合理存在，"
    "请不要将其报告为「未定义」或「未导入」。"
)


def _build_system_prompt(file_path: str) -> str:
    """根据文件扩展名动态选择专家身份。

    Args:
        file_path: 文件路径（如 "src/AuthService.java"）

    Returns:
        对应的 SYSTEM_PROMPT
    """
    from src.language_detector import get_language_name
    lang = get_language_name(file_path)
    expert_line = _LANGUAGE_EXPERT_MAP.get(lang, _LANGUAGE_EXPERT_MAP["General"])
    return expert_line + _SAFETY_CONSTRAINTS


# 保留旧 SYSTEM_PROMPT 用于兼容
SYSTEM_PROMPT = _LANGUAGE_EXPERT_MAP["Python"] + _SAFETY_CONSTRAINTS.replace(
    "请根据提供的文件变更",
    "请根据提供的文件变更"
)

USER_PROMPT_TEMPLATE = """请审查以下文件变更，输出严格符合以下 JSON Schema：

{{
  "file": "文件名",
  "issues": [
    {{
      "line": 行号 (int),
      "severity": "critical|warning|suggestion",
      "category": "security|performance|correctness|style|logic",
      "title": "问题简短标题",
      "description": "问题详细说明",
      "suggestion": "修改建议",
      "code_reference": "涉及的具体代码片段"
    }}
  ],
  "summary": "一句话总结"
}}

没有发现问题时返回 {{"file": "{file_path}", "issues": [], "summary": "未发现明显问题"}}

变更内容：
{diff_content}"""

# ---- Token 超限关键词 ----

TOKEN_LIMIT_SIGNALS = [
    "context window",
    "token limit",
    "maximum context",
    "context length",
    "too many tokens",
    "token exceeded",
    "input too long",
    "context_length_exceeded",
    "maximum text length",
]


def _is_token_limit_error(error_msg: str) -> bool:
    """判断 API 错误消息是否指示 Token 超限。"""
    msg_lower = error_msg.lower()
    return any(signal in msg_lower for signal in TOKEN_LIMIT_SIGNALS)


def _truncate_diff_to_changed_lines(diff_content: str, context_lines: int = 3) -> str:
    """
    裁剪 diff，只保留变更行及其上下文 ±N 行。

    这是 Token 超限时的 Plan B 策略：
    大幅减少传给 LLM 的内容量，同时保留审查所需的关键信息。

    Args:
        diff_content: 原始 diff 文本
        context_lines: 变更行周围保留的上下文行数

    Returns:
        裁剪后的 diff 文本
    """
    lines = diff_content.split("\n")
    n = len(lines)

    # 1. 标记哪些行是实际变更行（+/- 开头的行，排除 ---/+++ 头）
    is_changed = [False] * n
    for i, line in enumerate(lines):
        stripped = line.lstrip()
        if stripped.startswith("+") and not stripped.startswith("+++"):
            is_changed[i] = True
        elif stripped.startswith("-") and not stripped.startswith("---"):
            is_changed[i] = True

    # 2. 没有实际变更行 → 返回空字符串
    if not any(is_changed):
        logger.warning("裁剪时未找到任何变更行，返回空 diff")
        return ""

    # 3. 扩展上下文范围
    expanded = [False] * n
    for i in range(n):
        if is_changed[i]:
            start = max(0, i - context_lines)
            end = min(n, i + context_lines + 1)
            for j in range(start, end):
                expanded[j] = True

    # 4. 始终保留 diff 头信息和 hunk 头
    for i, line in enumerate(lines):
        if any(line.startswith(prefix) for prefix in
               ("diff --git", "index ", "--- ", "+++ ", "@@")):
            expanded[i] = True

    # 5. 标记文件边界（diff --git 行始终保留）
    result_lines = [line for i, line in enumerate(lines) if expanded[i]]

    logger.info(
        "diff 裁剪完成: %d 行 → %d 行 (保留 ±%d 行上下文)",
        n, len(result_lines), context_lines,
    )
    return "\n".join(result_lines)


def _build_user_prompt(file_path: str, diff_content: str) -> str:
    """构建 User Prompt。"""
    return USER_PROMPT_TEMPLATE.format(
        file_path=file_path,
        diff_content=diff_content,
    )


def _create_client(config: dict) -> OpenAI:
    """创建 OpenAI 客户端（兼容 DeepSeek API）。"""
    return OpenAI(
        api_key=config["api_key"],
        base_url=config["base_url"],
        timeout=config["timeout"],
    )


def _call_llm(
    client: OpenAI,
    model: str,
    system_prompt: str,
    user_prompt: str,
) -> str:
    """
    调用 LLM 并返回原始响应文本。

    Raises:
        APIError: API 返回错误
        APITimeoutError: 请求超时
        RateLimitError: 频率限制
    """
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.1,       # 低温度，输出更稳定
        max_tokens=8192,       # 确保有足够空间输出完整 JSON
        response_format={"type": "json_object"},  # 强制 JSON 输出（需模型支持）
    )

    # 提取响应文本
    content = response.choices[0].message.content
    if content is None:
        raise APIError(
            message="LLM 返回了空响应",
            body={"choices": [{"message": {"content": None}}]},
            request=None,
        )

    return content


def review_file(
    file_path: str,
    diff_content: str,
    config: dict,
) -> dict:
    """
    审查单个文件的 diff，返回结构化审查结果。

    Args:
        file_path: 文件路径（如 "fastapi/app.py"），会传递给 LLM
        diff_content: 该文件的完整 diff 文本
        config: 配置字典（含 api_key, base_url, model, max_retries, timeout）

    Returns:
        dict: {
            "file": str,
            "issues": [{"line": int, "severity": str, ...}],
            "summary": str,
            "error": bool,        # True 表示本次审查失败
            "error_info": str,    # 仅在 error=True 时存在
        }
    """
    # ---- 参数校验 ----
    if not diff_content or not diff_content.strip():
        logger.warning("文件 %s 的 diff 内容为空，跳过审查", file_path)
        return {
            "file": file_path,
            "issues": [],
            "summary": "Empty diff, skipped",
            "error": True,
        }

    # ---- 初始化 ----
    client = _create_client(config)
    system_prompt = _build_system_prompt(file_path)
    max_retries = config.get("max_retries", 2)

    # 当前使用的 diff（可能在 Token 超限后被替换为裁剪版）
    current_diff = diff_content
    already_truncated = False

    # ---- 重试循环 ----
    for attempt in range(max_retries + 1):
        user_prompt = _build_user_prompt(file_path, current_diff)

        try:
            # 调用 LLM
            raw_content = _call_llm(client, config["model"], system_prompt, user_prompt)

            # 解析 JSON
            try:
                result = json.loads(raw_content)
            except json.JSONDecodeError as e:
                logger.error(
                    "JSON 解析失败 (file=%s, attempt=%d): %s\n原始响应前200字: %s",
                    file_path, attempt + 1, e, raw_content[:200],
                )
                # JSON 解析失败不重试——模型输出了非 JSON，重试大概率也一样
                return {
                    "file": file_path,
                    "issues": [],
                    "summary": "Failed to parse LLM response",
                    "error": True,
                    "error_info": f"JSONDecodeError: {e}",
                }

            # 确保必要字段存在
            result.setdefault("file", file_path)
            result.setdefault("issues", [])
            result.setdefault("summary", "")
            result["error"] = False

            logger.info(
                "审查完成 (file=%s): %d issues",
                file_path, len(result["issues"]),
            )
            return result

        except APITimeoutError as e:
            logger.warning(
                "API 超时 (file=%s, attempt=%d/%d): %s",
                file_path, attempt + 1, max_retries + 1, e,
            )
            if attempt < max_retries:
                _wait(attempt)
                continue
            return _error_result(file_path, f"API Timeout: {e}")

        except RateLimitError as e:
            logger.warning(
                "频率限制 (file=%s, attempt=%d/%d): %s",
                file_path, attempt + 1, max_retries + 1, e,
            )
            if attempt < max_retries:
                # 频率限制等久一点
                time.sleep(5 * (attempt + 1))
                continue
            return _error_result(file_path, f"Rate Limit: {e}")

        except APIError as e:
            error_msg = str(e)
            logger.warning(
                "API 错误 (file=%s, attempt=%d/%d): %s",
                file_path, attempt + 1, max_retries + 1, error_msg,
            )

            # ---- Plan B: Token 超限 → 裁剪后重试 ----
            if _is_token_limit_error(error_msg) and not already_truncated:
                logger.info("Token 超限，执行裁剪后重试 (file=%s)", file_path)
                current_diff = _truncate_diff_to_changed_lines(diff_content)
                already_truncated = True
                # 不消耗重试次数，立即重试
                continue

            if attempt < max_retries:
                _wait(attempt)
                continue
            return _error_result(file_path, f"API Error: {error_msg}")

        except Exception as e:
            logger.exception(
                "未知错误 (file=%s, attempt=%d/%d): %s",
                file_path, attempt + 1, max_retries + 1, e,
            )
            if attempt < max_retries:
                _wait(attempt)
                continue
            return _error_result(file_path, f"Unexpected Error: {e}")

    # 不应执行到这里
    return _error_result(file_path, "All retries exhausted")


# ---- 辅助函数 ----

def _wait(attempt: int) -> None:
    """指数退避等待。"""
    delay = 2 ** attempt
    logger.debug("等待 %d 秒后重试...", delay)
    time.sleep(delay)


def _error_result(file_path: str, error_info: str) -> dict:
    """生成标准化的错误结果。"""
    return {
        "file": file_path,
        "issues": [],
        "summary": "LLM review failed",
        "error": True,
        "error_info": error_info,
    }


# ---- CLI 快捷测试 ----
if __name__ == "__main__":
    import argparse

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    parser = argparse.ArgumentParser(description="测试 LLM 审查单个文件")
    parser.add_argument("file_path", help="要审查的文件路径")
    parser.add_argument("--diff", required=True, help="diff 文件路径")
    parser.add_argument("--key", help="API Key（不传则从环境变量读取）")
    args = parser.parse_args()

    # 加载配置
    try:
        from src.config import load_config, print_config_summary
        cfg = load_config()
        if args.key:
            cfg["api_key"] = args.key
        print_config_summary(cfg)
    except ValueError as e:
        print(f"配置错误: {e}")
        exit(1)

    # 读取 diff
    with open(args.diff, "r", encoding="utf-8") as f:
        diff_content = f.read()

    print(f"\n正在审查: {args.file_path}")
    print(f"Diff 大小: {len(diff_content)} 字符\n")

    result = review_file(args.file_path, diff_content, cfg)

    print(json.dumps(result, indent=2, ensure_ascii=False))
