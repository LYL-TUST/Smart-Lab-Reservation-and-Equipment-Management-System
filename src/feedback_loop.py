"""
AI Code Reviewer - 反馈飞轮数据存储层

核心价值：将开发者对 AI 审查结果的反馈持久化，
使规则引擎能从人的判断中自动学习生长。

设计原则:
- 数据先行：所有反馈先落地，再做分析
- 不可变日志：每条 feedback 写入后不做修改（追加模式）
- 可审计：每次 dismiss 记录 reason，确保可回溯

面试金句:
"我的规则引擎不是靠人定，而是靠使用者的反馈自动生长的。"
"""

import json
import logging
import os
import re
import uuid
from collections import Counter
from datetime import datetime, timezone
from typing import Any, Optional

logger = logging.getLogger(__name__)

# 默认存储路径
DEFAULT_FEEDBACK_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "feedback",
)
DEFAULT_FEEDBACK_PATH = os.path.join(DEFAULT_FEEDBACK_DIR, "feedback_log.json")

# 合法操作
VALID_ACTIONS = ("accept", "dismiss")


class FeedbackStore:
    """反馈飞轮的数据存储。

    将开发者对 AI 审查结果的反馈（accept / dismiss）
    持久化到本地 JSON 文件中，供后续自动生成规则。

    用法:
        store = FeedbackStore()
        store.record_action("issue_001", "dismiss",
                            reason="mock object, no null check needed",
                            metadata={"file": "app.py", "category": "correctness"})
        stats = store.get_statistics()
        batches = store.get_dismiss_batches(min_count=2)
    """

    def __init__(self, path: str = DEFAULT_FEEDBACK_PATH):
        self.path = path
        self._ensure_file()

    # ── 公开 API ──

    def record_action(
        self,
        issue_id: str,
        action: str,
        reason: str = "",
        metadata: Optional[dict] = None,
    ) -> dict:
        """记录一次用户对审查结果的反馈。

        Args:
            issue_id: issue 唯一标识，格式建议 "YYYYMMDD_PR#_file_N"
            action: "accept"（确认问题）| "dismiss"（标记为误报）
            reason: 开发者填写的原因，dismiss 时建议必填
            metadata: issue 的上下文信息。
                    推荐包含 {"file", "category", "severity", "title", "description"}

        Returns:
            dict: 写入的 feedback 记录

        Raises:
            ValueError: action 不合法或 issue_id 为空
        """
        # 参数校验
        if not issue_id or not issue_id.strip():
            raise ValueError("issue_id 不能为空")
        if action not in VALID_ACTIONS:
            raise ValueError(f"action 必须是 {VALID_ACTIONS} 之一，收到: {action}")

        record = {
            "issue_id": issue_id.strip(),
            "action": action,
            "reason": reason.strip() if reason else "",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "metadata": {
                "file": "",
                "category": "",
                "severity": "",
                "title": "",
                "description": "",
                **(metadata or {}),
            },
        }

        # 追加写入
        data = self._read()
        data["feedbacks"].append(record)
        data["total_count"] = len(data["feedbacks"])
        self._write(data)

        logger.info(
            "反馈已记录: issue=%s action=%s reason=%s",
            issue_id, action, reason[:50] if reason else "",
        )
        return record

    def get_statistics(self) -> dict:
        """返回当前所有反馈的统计摘要。

        Returns:
            {
              "total_feedback": int,
              "accept_count": int,
              "dismiss_count": int,
              "accept_rate": float,
              "dismiss_rate": float,
              "top_dismissed_categories": [{"category": str, "count": int}, ...],
              "top_dismissed_titles": [{"title": str, "count": int}, ...],
            }
        """
        data = self._read()
        feedbacks = data.get("feedbacks", [])

        total = len(feedbacks)
        if total == 0:
            return {
                "total_feedback": 0,
                "accept_count": 0,
                "dismiss_count": 0,
                "accept_rate": 0.0,
                "dismiss_rate": 0.0,
                "top_dismissed_categories": [],
                "top_dismissed_titles": [],
            }

        accepts = [f for f in feedbacks if f["action"] == "accept"]
        dismisses = [f for f in feedbacks if f["action"] == "dismiss"]

        # 被 dismiss 的 issue 分类统计
        cat_counter: Counter = Counter()
        title_counter: Counter = Counter()
        for f in dismisses:
            meta = f.get("metadata", {})
            if meta.get("category"):
                cat_counter[meta["category"]] += 1
            if meta.get("title"):
                # 将 title 归一化用于聚类
                normalized = self._normalize_title(meta["title"])
                title_counter[normalized] += 1

        return {
            "total_feedback": total,
            "accept_count": len(accepts),
            "dismiss_count": len(dismisses),
            "accept_rate": round(len(accepts) / total, 3),
            "dismiss_rate": round(len(dismisses) / total, 3),
            "top_dismissed_categories": [
                {"category": k, "count": v}
                for k, v in cat_counter.most_common(10)
            ],
            "top_dismissed_titles": [
                {"title": k, "count": v}
                for k, v in title_counter.most_common(10)
            ],
        }

    def get_dismiss_batches(self, min_count: int = 3) -> list[dict]:
        """返回被 dismiss 次数 >= min_count 的同类问题分组。

        用于自动生成规则：当某类问题被反复 dismiss，
        说明这是一个稳定的误报模式，可以提提取为规则。

        Args:
            min_count: 最小触发次数，低于此阈值不分组

        Returns:
            [{
                "pattern_key": "security|SQL injection risk",
                "count": int,
                "samples": [{"issue_id": str, "title": str, "description": str}, ...],
            }, ...]
        """
        data = self._read()
        dismisses = [
            f for f in data.get("feedbacks", [])
            if f["action"] == "dismiss"
        ]

        # 用 (category, normalized_title) 做分组 key
        groups: dict[str, list[dict]] = {}
        for f in dismisses:
            meta = f.get("metadata", {})
            category = meta.get("category", "unknown")
            title = meta.get("title", "")
            normalized = self._normalize_title(title)
            key = f"{category}|{normalized}"

            if key not in groups:
                groups[key] = []
            groups[key].append({
                "issue_id": f["issue_id"],
                "title": title,
                "description": meta.get("description", ""),
                "reason": f.get("reason", ""),
            })

        # 过滤并排序
        result = [
            {
                "pattern_key": key,
                "count": len(items),
                "samples": items[:3],  # 最多保留 3 条样本
            }
            for key, items in groups.items()
            if len(items) >= min_count
        ]
        result.sort(key=lambda x: x["count"], reverse=True)

        return result

    def generate_rules_candidates(self, min_count: int = 3) -> list[dict]:
        """根据 dismiss 数据，生成可用于 rules.json 的规则候选。

        这是反馈飞轮的核心转化函数：
        人的判断 → 统计数据 → 可执行的规则。

        Args:
            min_count: 最小 dismiss 次数，低于此不生成规则

        Returns:
            [{
                "id": "AUTO-RULE-001",
                "name": str,
                "action": "filter",
                "conditions": {...},
                "generated_from": "feedback",
                "dismiss_count": int,
            }, ...]
        """
        batches = self.get_dismiss_batches(min_count=min_count)
        candidates = []

        for i, batch in enumerate(batches):
            key = batch["pattern_key"]
            category, title_normalized = key.split("|", 1)

            # 提取 trigger keywords（从样本的 title/description 中提取高频词）
            all_text = " ".join(
                f"{s['title']} {s['description']}"
                for s in batch["samples"]
            )
            keywords = self._extract_keywords(all_text)
            if not keywords:
                continue

            # 生成规则候选
            candidate = {
                "id": f"AUTO-RULE-{i + 1:03d}",
                "name": f"自动规则: {title_normalized[:40]}",
                "action": "filter",
                "enabled": False,  # 默认关闭，需人工审核
                "description": f"由反馈飞轮自动生成 (dismiss {batch['count']} 次)",
                "conditions": {
                    "type": "field_value",
                    "field": "title",
                    "match_values": keywords[:5],
                },
                "generated_from": "feedback",
                "dismiss_count": batch["count"],
                "samples": batch["samples"],
            }
            candidates.append(candidate)

        return candidates

    # ── 内部方法 ──

    def _ensure_file(self) -> None:
        """确保存储目录和文件存在。"""
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        if not os.path.isfile(self.path):
            self._write({
                "version": "1.0",
                "total_count": 0,
                "feedbacks": [],
            })
            logger.info("反馈日志文件已创建: %s", self.path)

    def _read(self) -> dict:
        """读取完整反馈数据。"""
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            logger.warning("反馈文件读取失败，返回空数据: %s", self.path)
            return {"version": "1.0", "total_count": 0, "feedbacks": []}

    def _write(self, data: dict) -> None:
        """写入反馈数据。"""
        tmp_path = self.path + ".tmp"
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        os.replace(tmp_path, self.path)  # 原子写入

    @staticmethod
    def _normalize_title(title: str) -> str:
        """将 title 归一化用于聚类。

        归一化规则:
        1. 小写 + trim
        2. 去尾部数字序号（"query 0" → "query"）
        3. 去尾部 "in/for/at/of/on xxx" 局部信息
        4. 去标点

        例如:
            "Missing null check for mock object" → "missing null check"
            "SQL injection risk in query 0" → "sql injection risk"
            "  Naming convention violation  " → "naming convention violation"
        """
        t = title.lower().strip()
        # 去尾部数字序号（"risk 0", "query_1", "test_2" 等）
        t = re.sub(r'[\s_]\d+$', '', t)
        # 去尾部的局部信息（"in xxx", "for xxx xxx", "at xxx"）
        t = re.sub(r'\s+(?:in|for|at|of|on)\s+.+$', '', t)
        # 去标点
        t = re.sub(r'[^\w\s]', '', t)
        return t.strip()[:60]

    @staticmethod
    def _extract_keywords(text: str, max_keywords: int = 5) -> list[str]:
        """从文本中提取高频关键词作为匹配特征。"""
        text = text.lower()
        # 分词，过滤停用词和短词
        stop_words = {
            "the", "a", "an", "is", "are", "was", "were", "be", "been",
            "in", "on", "at", "to", "for", "of", "with", "by", "from",
            "this", "that", "it", "its", "we", "you", "they", "he", "she",
            "not", "no", "but", "or", "and", "if", "so", "as",
        }
        words = re.findall(r'\b[a-zA-Z]{3,}\b', text)
        words = [w for w in words if w not in stop_words]

        # 按频率排序
        counter = Counter(words)
        keywords = [w for w, _ in counter.most_common(max_keywords)]

        return keywords if keywords else []


# ──────────────────────────────────────────────
#  RuleGenerator — 反馈 → 规则转换器
# ──────────────────────────────────────────────

class RuleGenerator:
    """基于反馈批次自动生成规则候选。

    从 FeedbackStore.get_dismiss_batches() 获取分组结果，
    根据 group 中的 title/category 模式，自动构造
    rules.json 格式的规则条目。

    用法:
        generator = RuleGenerator()
        batch = store.get_dismiss_batches(min_count=3)[0]
        rule = generator.from_dismiss_batch(batch)
        if rule:
            generator.write_rule(rule)
    """

    # 已知规则文件路径（用于冲突检测）
    DEFAULT_RULES_PATH = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "rules", "rules.json",
    )

    # category → conditions type 映射
    CATEGORY_CONDITION_MAP = {
        "security": "keyword_conflict",
        "correctness": "field_value",
        "performance": "field_value",
        "style": "severity_and_field_contains",
        "logic": "code_pattern",
    }

    @staticmethod
    def from_dismiss_batch(
        batch: dict,
        rules_path: str = "",
    ) -> dict | None:
        """为一批同类 dismiss 生成一条规则。

        生成逻辑：
        1. 取 batch 中 samples 的 title 公共子串作为规则名
        2. 根据 samples[0].category 推断 conditions 类型
        3. 默认 action 为 "downgrade"（降级为 suggestion 而非完全过滤）
        4. 自动分配 rule id: "RULE-{:03d}-auto"
        5. 检查是否与现有规则冲突（keywords 去重）

        Args:
            batch: get_dismiss_batches 返回的一个分组
            rules_path: 现有规则文件路径（用于冲突检测）

        Returns:
            dict: 新规则，如果与现有规则冲突则返回 None
        """
        samples = batch.get("samples", [])
        if not samples:
            return None

        # 1. 推断规则名
        category = samples[0].get("metadata", {}).get("category", "unknown")
        severity = samples[0].get("metadata", {}).get("severity", "warning")

        # 取 title 公共特征
        titles = [s.get("title", "") for s in samples]
        common_title = RuleGenerator._longest_common_prefix(titles)
        rule_name = common_title[:50] if common_title else "自动生成规则"

        # 2. 提取关键词
        all_text = " ".join(
            f"{s.get('title', '')} {s.get('description', '')}"
            for s in samples
        )
        keywords = FeedbackStore._extract_keywords(all_text, max_keywords=5)
        if not keywords:
            return None

        # 3. 构建 conditions
        cond_type = RuleGenerator.CATEGORY_CONDITION_MAP.get(category, "field_value")
        conditions = RuleGenerator._build_conditions(cond_type, category, keywords, severity)

        # 4. 构造规则
        rule = {
            "id": f"RULE-{999:03d}-auto",
            "name": rule_name,
            "enabled": False,
            "action": "downgrade",
            "description": f"由反馈飞轮自动生成（dismiss {batch['count']} 次, category={category}）",
            "conditions": conditions,
        }

        # 5. 冲突检测
        rules_path = rules_path or RuleGenerator.DEFAULT_RULES_PATH
        existing = RuleGenerator._load_existing_rules(rules_path)
        conflict = RuleGenerator.check_conflict(rule, existing)
        if conflict:
            logger.info("规则与 %s 冲突，跳过生成: %s", conflict, rule_name)
            return None

        return rule

    @staticmethod
    def write_rule(rule: dict, rules_path: str = "") -> bool:
        """将新规则追加到 rules.json 的 rules 数组中。

        保留 rules_metadata 不变，自动分配正式 ID。

        Args:
            rule: 由 from_dismiss_batch 生成的规则 dict
            rules_path: rules.json 文件路径

        Returns:
            bool: 是否写入成功
        """
        path = rules_path or RuleGenerator.DEFAULT_RULES_PATH
        if not os.path.isfile(path):
            logger.warning("规则文件不存在: %s", path)
            return False

        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            logger.error("读取规则文件失败: %s", e)
            return False

        existing = data.get("rules", [])

        # 分配正式 ID
        max_num = 0
        for r in existing:
            match = re.match(r"RULE-(\d+)", r.get("id", ""))
            if match:
                max_num = max(max_num, int(match.group(1)))
        rule["id"] = f"RULE-{max_num + 1:03d}"

        data["rules"].append(rule)

        # 原子写入
        tmp_path = path + ".tmp"
        try:
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            os.replace(tmp_path, path)
            logger.info("规则已追加: %s — %s", rule["id"], rule["name"])
            return True
        except Exception as e:
            logger.error("写入规则文件失败: %s", e)
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
            return False

    @staticmethod
    def check_conflict(rule: dict, existing_rules: list[dict]) -> str | None:
        """检查新规则是否与现有规则重复。

        冲突判断规则：
        - 取规则 conditions 中的 match_values/keywords 作为特征词集
        - 与每条现有规则的特征词集计算 Jaccard 相似度
        - 相似度 >= 0.5 判定为冲突

        Args:
            rule: 新规则
            existing_rules: 现有规则列表

        Returns:
            None 表示无冲突，str 表示冲突规则的 ID（如 "RULE-001"）
        """
        new_keywords = RuleGenerator._extract_rule_keywords(rule)
        if not new_keywords:
            return None

        new_set = set(new_keywords)

        for existing in existing_rules:
            existing_keywords = RuleGenerator._extract_rule_keywords(existing)
            if not existing_keywords:
                continue

            existing_set = set(existing_keywords)
            # Jaccard 相似度
            intersection = new_set & existing_set
            union = new_set | existing_set
            if not union:
                continue

            similarity = len(intersection) / len(union)
            if similarity >= 0.3:
                return existing.get("id", "unknown")

        return None

    # ── 内部方法 ──

    @staticmethod
    def _build_conditions(cond_type: str, category: str, keywords: list[str], severity: str) -> dict:
        """根据条件类型构建 conditions 字典。"""
        if cond_type == "keyword_conflict":
            return {
                "type": "keyword_conflict",
                "trigger_keywords": {
                    "fields": ["title", "description"],
                    "keywords": keywords,
                },
                "safe_keywords": {
                    "fields": ["code_reference", "description"],
                    "keywords": [],
                },
                "logic": "auto-generated from feedback",
            }

        if cond_type == "severity_and_field_contains":
            return {
                "type": "severity_and_field_contains",
                "severity": severity,
                "field": "description",
                "keywords": keywords,
            }

        if cond_type == "code_pattern":
            return {
                "type": "code_pattern",
                "category": category,
                "title_contains": keywords[:3],
                "code_pattern": "",
            }

        # field_value (默认)
        return {
            "type": "field_value",
            "field": "title",
            "match_empty": False,
            "match_values": keywords,
        }

    @staticmethod
    def _load_existing_rules(rules_path: str) -> list[dict]:
        """从规则文件加载现有规则列表。"""
        try:
            with open(rules_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data.get("rules", [])
        except Exception:
            return []

    @staticmethod
    def _extract_rule_keywords(rule: dict) -> list[str]:
        """从规则中提取用于冲突检测的特征词。"""
        conditions = rule.get("conditions", {})
        cond_type = conditions.get("type", "")

        words = []

        if cond_type == "keyword_conflict":
            trigger = conditions.get("trigger_keywords", {})
            words.extend(trigger.get("keywords", []))

        elif cond_type == "severity_and_field_contains":
            words.extend(conditions.get("keywords", []))

        elif cond_type == "code_pattern":
            words.extend(conditions.get("title_contains", []))

        else:  # field_value
            words.extend(conditions.get("match_values", []))

        # 全部小写后去重
        return list(dict.fromkeys(w.lower() for w in words))

    @staticmethod
    def _longest_common_prefix(strings: list[str]) -> str:
        """取一组字符串的最长公共前缀，用于推断规则名。"""
        if not strings:
            return ""
        if len(strings) == 1:
            return strings[0]

        prefix = strings[0]
        for s in strings[1:]:
            i = 0
            while i < len(prefix) and i < len(s) and prefix[i].lower() == s[i].lower():
                i += 1
            prefix = prefix[:i]
            if not prefix:
                break

        return prefix.strip()


# ──────────────────────────────────────────────
#  run_flywheel — 执行一轮完整的反馈飞轮
# ──────────────────────────────────────────────

def run_flywheel(
    feedback_path: str = "",
    rules_path: str = "",
    min_dismiss: int = 3,
) -> dict:
    """执行一轮完整反馈飞轮：读取反馈 → 聚簇 → 生成规则 → 写入。

    这是反馈飞轮的顶层入口函数，串联 FeedbackStore 和 RuleGenerator。

    Args:
        feedback_path: feedback_log.json 路径
        rules_path: rules.json 路径
        min_dismiss: 聚簇的最小 dismiss 次数

    Returns:
        {
          "total_feedback": N,
          "accept_count": N,
          "dismiss_count": N,
          "accept_rate": 0.XX,
          "batches_found": 3,
          "rules_generated": 2,
          "rules_skipped_conflict": 1,
          "new_rule_ids": ["RULE-007", "RULE-008"],
          "errors": [],
        }
    """
    # 默认路径
    if not feedback_path:
        feedback_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "feedback", "feedback_log.json",
        )
    if not rules_path:
        rules_path = RuleGenerator.DEFAULT_RULES_PATH

    report = {
        "total_feedback": 0,
        "accept_count": 0,
        "dismiss_count": 0,
        "accept_rate": 0.0,
        "batches_found": 0,
        "rules_generated": 0,
        "rules_skipped_conflict": 0,
        "new_rule_ids": [],
        "errors": [],
    }

    # 1. 加载反馈数据
    if not os.path.isfile(feedback_path):
        report["errors"].append(f"反馈文件不存在: {feedback_path}")
        return report

    store = FeedbackStore(path=feedback_path)
    stats = store.get_statistics()
    report["total_feedback"] = stats["total_feedback"]
    report["accept_count"] = stats["accept_count"]
    report["dismiss_count"] = stats["dismiss_count"]
    report["accept_rate"] = stats["accept_rate"]

    if stats["total_feedback"] == 0:
        report["errors"].append("无反馈数据")
        return report

    if stats["dismiss_count"] == 0:
        logger.info("飞轮: 无 dismiss 记录，跳过规则生成")
        return report

    # 2. 聚簇
    batches = store.get_dismiss_batches(min_count=min_dismiss)
    report["batches_found"] = len(batches)
    logger.info("飞轮: 发现 %d 个 dismiss 聚簇（min_count=%d）", len(batches), min_dismiss)

    if not batches:
        return report

    # 3. 逐簇生成规则
    for batch in batches:
        try:
            rule = RuleGenerator.from_dismiss_batch(batch, rules_path=rules_path)
            if rule is None:
                report["rules_skipped_conflict"] += 1
                continue

            # 写入
            ok = RuleGenerator.write_rule(rule, rules_path=rules_path)
            if ok:
                report["rules_generated"] += 1
                report["new_rule_ids"].append(rule.get("id", "unknown"))
                logger.info("飞轮: 生成规则 %s — %s", rule["id"], rule["name"])
            else:
                report["errors"].append(f"写入规则失败: batch={batch.get('pattern_key', '?')}")

        except Exception as e:
            logger.exception("飞轮: 规则生成异常")
            report["errors"].append(f"规则生成异常: {e}")

    return report


def print_flywheel_report(report: dict) -> None:
    """友好打印飞轮执行报告。"""
    print()
    print("=" * 60)
    print("  反馈飞轮执行报告")
    print("=" * 60)
    print(f"  总反馈数:         {report['total_feedback']}")
    print(f"  采纳数 / 驳回数:  {report['accept_count']} / {report['dismiss_count']}")
    print(f"  采纳率:           {report['accept_rate'] * 100:.1f}%")
    print(f"  发现重复模式:     {report['batches_found']} 个")
    print(f"  生成新规则:       {report['rules_generated']} 条")
    print(f"  跳过（冲突）:     {report['rules_skipped_conflict']} 条")
    if report["new_rule_ids"]:
        print(f"  规则 ID:          {', '.join(report['new_rule_ids'])}")
    if report["errors"]:
        print(f"  错误:             {len(report['errors'])} 个")
        for err in report["errors"]:
            print(f"    - {err}")
    print("=" * 60)
    print()


# ── CLI 快捷诊断 ──

if __name__ == "__main__":
    import argparse

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    parser = argparse.ArgumentParser(description="反馈飞轮管理")
    parser.add_argument("action", choices=["stats", "batches", "candidates", "add"],
                        help="操作: stats=统计, batches=分组, candidates=规则候选, add=添加反馈")
    parser.add_argument("--issue-id", help="issue 标识")
    parser.add_argument("--action-type", choices=["accept", "dismiss"], help="反馈类型")
    parser.add_argument("--reason", default="", help="dismiss 原因")
    parser.add_argument("--file", default="", help="文件路径")
    parser.add_argument("--category", default="", help="问题分类")
    parser.add_argument("--severity", default="", help="严重级别")
    parser.add_argument("--title", default="", help="问题标题")
    parser.add_argument("--min-count", type=int, default=2, help="最小分组次数")
    args = parser.parse_args()

    store = FeedbackStore()

    if args.action == "add":
        if not args.issue_id or not args.action_type:
            print("add 操作需要 --issue-id 和 --action-type")
            exit(1)
        meta = {
            "file": args.file,
            "category": args.category,
            "severity": args.severity,
            "title": args.title,
        }
        record = store.record_action(args.issue_id, args.action_type, args.reason, meta)
        print(json.dumps(record, indent=2, ensure_ascii=False))

    elif args.action == "stats":
        stats = store.get_statistics()
        print(json.dumps(stats, indent=2, ensure_ascii=False))

    elif args.action == "batches":
        batches = store.get_dismiss_batches(min_count=args.min_count)
        print(json.dumps(batches, indent=2, ensure_ascii=False))

    elif args.action == "candidates":
        candidates = store.generate_rules_candidates(min_count=args.min_count)
        print(f"生成 {len(candidates)} 条规则候选:\n")
        print(json.dumps(candidates, indent=2, ensure_ascii=False))
