"""
AI Code Reviewer - 配置管理模块

从环境变量读取 API Key、模型名称、超时等配置。
支持 DeepSeek API 和 OpenAI API 两种后端。
支持从 .env 文件自动加载（如果存在）。
"""

import os
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

def _load_env_file(env_path: str = ".env") -> None:
    """
    从 .env 文件加载环境变量（如果文件存在）。
    优先级低于已存在的环境变量（不会覆盖已有值）。
    """
    path = Path(env_path)
    if not path.exists():
        return

    loaded = 0
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            # 跳过空行和注释
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip().strip("\"'")
            if key and value and key not in os.environ:
                os.environ[key] = value
                loaded += 1

    if loaded > 0:
        logger.info("已从 %s 加载 %d 个环境变量", env_path, loaded)


# 模块导入时自动加载 .env
_load_env_file()


# ---- 环境变量名常量 ----
ENV_API_KEY_1 = "DEEPSEEK_API_KEY"
ENV_API_KEY_2 = "OPENAI_API_KEY"

# ---- 默认值 ----
DEFAULT_BASE_URL = "https://api.deepseek.com"
DEFAULT_MODEL = "deepseek-chat"
DEFAULT_MAX_RETRIES = 2
DEFAULT_TIMEOUT = 120  # seconds


def load_config() -> dict:
    """
    从环境变量加载配置。

    Returns:
        dict: {
            "api_key": str,
            "base_url": str,
            "model": str,
            "max_retries": int,
            "timeout": int,
        }

    Raises:
        ValueError: 当 API Key 未设置时抛出
    """
    api_key = os.getenv(ENV_API_KEY_1) or os.getenv(ENV_API_KEY_2)

    if not api_key:
        raise ValueError(
            f"API Key 未设置！请设置环境变量 {ENV_API_KEY_1} 或 {ENV_API_KEY_2}。\n"
            f"  PowerShell:     $env:{ENV_API_KEY_1}=\"sk-your-key\"\n"
            f"  CMD:            set {ENV_API_KEY_1}=sk-your-key\n"
            f"  Mac/Linux Bash: export {ENV_API_KEY_1}=sk-your-key\n"
        )

    config = {
        "api_key": api_key,
        "base_url": os.getenv("BASE_URL", DEFAULT_BASE_URL).rstrip("/"),
        "model": os.getenv("MODEL_NAME", DEFAULT_MODEL),
        "max_retries": int(os.getenv("MAX_RETRIES", str(DEFAULT_MAX_RETRIES))),
        "timeout": int(os.getenv("TIMEOUT", str(DEFAULT_TIMEOUT))),
    }

    logger.debug(
        "配置加载完成: base_url=%s, model=%s, max_retries=%d, timeout=%d",
        config["base_url"], config["model"],
        config["max_retries"], config["timeout"],
    )

    return config


def print_config_summary(config: dict) -> None:
    """打印当前配置摘要（隐藏 API Key 中间部分）"""
    key = config["api_key"]
    masked = key[:6] + "****" + key[-4:] if len(key) > 12 else "****"
    print("当前配置:")
    print(f"  API Key:     {masked}")
    print(f"  Base URL:    {config['base_url']}")
    print(f"  Model:       {config['model']}")
    print(f"  Max Retries: {config['max_retries']}")
    print(f"  Timeout:     {config['timeout']}s")


# ---- CLI 快捷测试 ----
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    try:
        cfg = load_config()
        print_config_summary(cfg)
    except ValueError as e:
        print(f"配置错误: {e}")
        exit(1)
