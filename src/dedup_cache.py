"""
AI Code Reviewer - 请求去重缓存模块

设计目的：同一 diff 同一模型只调一次 LLM——省钱，省 token，保证幂等。

缓存 Key: SHA256(model + file_path + diff_content_hash) 的前 16 个字符。
缓存值: issues + summary + 时间戳 + model info。
后端: JSON 文件（单文件零依赖，秒级读写，适合 CLI 工具）。
TTL: 默认 24 小时，过期自动跳过。

用法:
    cache = ReviewCache()
    key = cache.make_key(model, file_path, diff_content)
    cached = cache.get(key)
    if cached:
        return cached  # 命中！
    result = call_llm(...)
    cache.set(key, result)
"""

import hashlib
import json
import os
import time
from typing import Optional

# 默认缓存目录
DEFAULT_CACHE_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "results", ".review_cache",
)


class ReviewCache:
    """
    审查结果缓存，基于 JSON 文件后端。

    存储结构:
        results/.review_cache/
            a1b2c3d4.json  ← 一文件一条审查结果
            e5f6g7h8.json

    JSON 格式:
    {
        "key": "a1b2c3d4",
        "model": "deepseek-chat",
        "file": "fastapi/routing.py",
        "issues": [...],
        "summary": "Found 3 issues",
        "cached_at": 1753800000.123,
        "diff_hash": "sha256-of-diff-content"
    }
    """

    def __init__(self, cache_dir: str = DEFAULT_CACHE_DIR, cache_ttl: int = 86400):
        """
        Args:
            cache_dir: 缓存文件存放目录
            cache_ttl: 缓存有效期（秒），默认 24h
        """
        self.cache_dir = cache_dir
        self.cache_ttl = cache_ttl
        self._enabled = True
        os.makedirs(self.cache_dir, exist_ok=True)

    @staticmethod
    def make_key(model: str, file_path: str, diff_content: str) -> str:
        """
        生成缓存键。

        使用双层哈希确保唯一性：
        1. diff_content → SHA256（避免长字符串碰撞）
        2. model + file_path + diff_hash → SHA256 前 16 位

        Returns:
            16 字符的十六进制缓存键
        """
        diff_hash = hashlib.sha256(diff_content.encode("utf-8")).hexdigest()
        full = f"{model}\x00{file_path}\x00{diff_hash}"
        return hashlib.sha256(full.encode("utf-8")).hexdigest()[:16]

    def get(self, key: str) -> Optional[dict]:
        """
        从缓存中读取审查结果。

        Returns:
            命中 → {"issues": [...], "summary": "...", "cached": True, ...}
            未命中/过期 → None
        """
        if not self._enabled:
            return None

        path = self._path(key)
        if not os.path.isfile(path):
            return None

        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError):
            return None

        # 检查 TTL
        cached_at = data.get("cached_at", 0)
        if time.time() - cached_at > self.cache_ttl:
            os.remove(path)  # 清理过期缓存
            return None

        data["cached"] = True
        return data

    def set(self, key: str, result: dict, file_path: str = "", model: str = ""):
        """
        写入审查结果到缓存。只缓存成功结果（无 error 标记）。
        """
        if not self._enabled:
            return

        if result.get("error"):
            return  # 不缓存错误结果

        data = {
            "key": key,
            "model": model,
            "file": file_path,
            "issues": result.get("issues", []),
            "summary": result.get("summary", ""),
            "cached_at": time.time(),
        }

        path = self._path(key)
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except OSError:
            pass  # 磁盘写失败不影响审查流程

    def clear(self):
        """清除所有缓存文件。"""
        for fname in os.listdir(self.cache_dir):
            if fname.endswith(".json"):
                try:
                    os.remove(os.path.join(self.cache_dir, fname))
                except OSError:
                    pass

    def clear_expired(self):
        """只清除已过期的缓存。"""
        for fname in os.listdir(self.cache_dir):
            if not fname.endswith(".json"):
                continue
            path = os.path.join(self.cache_dir, fname)
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if time.time() - data.get("cached_at", 0) > self.cache_ttl:
                    os.remove(path)
            except (json.JSONDecodeError, OSError):
                try:
                    os.remove(path)
                except OSError:
                    pass

    def disable(self):
        """禁用缓存（--no-cache 时使用）。"""
        self._enabled = False

    def _path(self, key: str) -> str:
        return os.path.join(self.cache_dir, f"{key}.json")
