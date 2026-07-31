"""
AI Code Reviewer - 规则引擎模块

基于特征签名的确定性过滤层，用于拦截 LLM 审查结果中的已知误报。

设计原则:
- 不依赖 LLM 输出的语义一致性，只做确定性字段匹配
- 宁可漏过，不可误拦（精确率优先）
- 所有规则可外部配置（rules.json）

核心函数:
    filter_issues(issues, file_path, rules_path) -> dict
"""

import json
import logging
import os
import re
from typing import Optional

logger = logging.getLogger(__name__)

# 默认规则文件路径
_DEFAULT_RULES_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "rules", "rules.json",
)


def load_rules(rules_path: Optional[str] = None) -> list[dict]:
    """
    从 JSON 文件加载规则列表。

    Args:
        rules_path: 规则 JSON 文件路径，默认使用 rules/rules.json

    Returns:
        list[dict]: 规则列表
    """
    path = rules_path or _DEFAULT_RULES_PATH
    if not os.path.isfile(path):
        logger.warning("规则文件不存在: %s，使用内置规则", path)
        return _builtin_rules()

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        rules = data.get("rules", [])
        # 只返回启用的规则
        enabled = [r for r in rules if r.get("enabled", True)]
        logger.info("规则加载完成: %d/%d 条已启用 (from %s)", len(enabled), len(rules), path)
        return enabled
    except Exception as e:
        logger.warning("规则文件加载失败 (%s)，使用内置规则: %s", path, e)
        return _builtin_rules()


def _builtin_rules() -> list[dict]:
    """内置规则（当 rules.json 不可用时的后备）。"""
    return [
        {
            "id": "RULE-001", "name": "空/空值描述过滤", "enabled": True,
            "action": "filter",
            "conditions": {"type": "field_value", "field": "description",
                           "match_empty": True,
                           "match_values": ["N/A", "n/a", "None", "none", "null"]},
        },
        {
            "id": "RULE-002", "name": "模棱两可语气过滤", "enabled": True,
            "action": "filter",
            "conditions": {"type": "severity_and_field_contains",
                           "severity": "suggestion", "field": "description",
                           "keywords": ["Consider", "Maybe", "It might be better",
                                       "可以考虑", "可能需要", "maybe", "consider"]},
        },
        {
            "id": "RULE-003", "name": "测试文件问题降级", "enabled": True,
            "action": "downgrade",
            "conditions": {"type": "path_and_severity",
                           "path_patterns": ["test_", "_test.py", "/tests/"],
                           "max_severity": "warning"},
        },
        {
            "id": "RULE-004", "name": "SQL 注入假阳性过滤", "enabled": True,
            "action": "filter",
            "conditions": {"type": "keyword_conflict",
                           "trigger_keywords": {"fields": ["title", "description"],
                                                "keywords": ["SQL", "注入", "injection"]},
                           "safe_keywords": {"fields": ["title", "description", "code_reference"],
                                             "keywords": ["ORM", "session.query", "SQLAlchemy"]},
                           "logic": "trigger AND safe → filter"},
        },
        {
            "id": "RULE-005", "name": "私有函数类型标注宽松", "enabled": True,
            "action": "downgrade",
            "conditions": {"type": "code_pattern", "category": "style",
                           "title_contains": ["missing type", "类型注解", "type annotation",
                                            "缺少返回类型"],
                           "code_pattern": "def _+\\w+"},
        },
        {
            "id": "RULE-010", "name": "AST截断假阳性-未定义变量过滤", "enabled": True,
            "action": "filter",
            "conditions": {
                "type": "undefined_in_context",
                "trigger_keywords": {
                    "fields": ["title", "description"],
                    "keywords": ["未定义", "undefined", "is not defined", "not declared",
                                "未导入", "not imported", "undeclared"]
                },
            },
        },
    ]


def filter_issues(
    issues: list[dict],
    file_path: str = "",
    rules: Optional[list[dict]] = None,
) -> dict:
    """
    对 LLM 返回的 issues 列表应用规则引擎过滤。

    Args:
        issues: LLM 返回的问题列表
        file_path: 当前审查的文件路径（用于测试文件相关的规则）
        rules: 规则列表，默认从 rules.json 加载

    Returns:
        dict: {
            "passed": list[dict],       # 通过规则验证的问题
            "filtered": list[dict],     # 被规则拦截的问题
            "downgraded": list[dict],   # 被降级的问题（severity 改为 suggestion）
            "filtered_count": int,       # 被过滤的数量
            "applied_rules": list[str],  # 被触发的规则 ID 列表
        }
    """
    if rules is None:
        rules = load_rules()

    passed: list[dict] = []
    filtered: list[dict] = []
    downgraded: list[dict] = []
    applied_rules: list[str] = []

    for issue in issues:
        result = _apply_rules(issue, file_path, rules)
        if result["action"] == "filter":
            filtered.append(issue)
            if result["rule_id"] not in applied_rules:
                applied_rules.append(result["rule_id"])
        elif result["action"] == "downgrade":
            issue["severity"] = "suggestion"
            downgraded.append(issue)
            passed.append(issue)
            if result["rule_id"] not in applied_rules:
                applied_rules.append(result["rule_id"])
        else:  # pass
            passed.append(issue)

    return {
        "passed": passed,
        "filtered": filtered,
        "downgraded": downgraded,
        "filtered_count": len(filtered),
        "downgraded_count": len(downgraded),
        "applied_rules": applied_rules,
    }


def _apply_rules(issue: dict, file_path: str, rules: list[dict]) -> dict:
    """
    对单个 issue 应用所有规则。

    Returns:
        dict: {"action": "pass" | "filter" | "downgrade", "rule_id": str or None}
    """
    # 检测文件语言（用于跳过不适用于该语言的规则）
    from src.language_detector import is_python

    for rule in rules:
        action = rule.get("action", "filter")
        conditions = rule.get("conditions", {})

        # Python 专属规则：对非 Python 文件跳过
        rule_id = rule.get("id", "")
        if not is_python(file_path) and rule_id in _PYTHON_ONLY_RULES:
            continue

        if _match_condition(conditions, issue, file_path, rule):
            return {"action": action, "rule_id": rule_id}

    return {"action": "pass", "rule_id": None}


# Python 专属规则 ID 集合
_PYTHON_ONLY_RULES: set[str] = {
    "RULE-004",  # SQLAlchemy 假阳性过滤（仅 Python 有 ORM）
    "RULE-005",  # def _func 私有函数类型注解（Python 特有命名约定）
}


def _match_condition(
    conditions: dict,
    issue: dict,
    file_path: str,
    rule: dict,
) -> bool:
    """根据条件类型匹配 issue。"""
    cond_type = conditions.get("type", "")

    if cond_type == "field_value":
        return _match_field_value(conditions, issue)

    elif cond_type == "severity_and_field_contains":
        return _match_severity_and_contains(conditions, issue)

    elif cond_type == "path_and_severity":
        return _match_path_and_severity(conditions, issue, file_path)

    elif cond_type == "keyword_conflict":
        return _match_keyword_conflict(conditions, issue)

    elif cond_type == "code_pattern":
        return _match_code_pattern(conditions, issue)

    elif cond_type == "undefined_in_context":
        return _match_undefined_in_context(conditions, issue)

    else:
        logger.debug("未知规则条件类型: %s", cond_type)
        return False


# ── 条件匹配器 ──


def _get_field(issue: dict, field_path: str) -> str:
    """从 issue 中获取嵌套字段值。"""
    parts = field_path.split(".")
    value = issue
    for part in parts:
        if isinstance(value, dict):
            value = value.get(part, "")
        else:
            return ""
    return str(value) if value else ""


def _match_field_value(conditions: dict, issue: dict) -> bool:
    """RULE-001: 字段为空或为特定值。"""
    field = conditions.get("field", "description")
    value = _get_field(issue, field).strip()

    # 空匹配
    if conditions.get("match_empty", False) and not value:
        return True

    # 特定值匹配
    for v in conditions.get("match_values", []):
        if value == v:
            return True

    return False


def _match_severity_and_contains(conditions: dict, issue: dict) -> bool:
    """RULE-002: 特定严重级别且字段包含模糊词。"""
    target_severity = conditions.get("severity", "")
    if issue.get("severity") != target_severity:
        return False

    field = conditions.get("field", "description")
    value = _get_field(issue, field)
    keywords = conditions.get("keywords", [])

    for kw in keywords:
        if kw in value:
            return True

    return False


def _match_path_and_severity(conditions: dict, issue: dict, file_path: str) -> bool:
    """RULE-003: 测试文件中的问题降级。"""
    # 检查文件路径
    path_patterns = conditions.get("path_patterns", [])
    path_match = any(p in file_path for p in path_patterns)
    if not path_match:
        return False

    # 检查严重级别
    sev = issue.get("severity", "")
    max_sev = conditions.get("max_severity", "warning")
    severity_order = {"suggestion": 0, "warning": 1, "critical": 2}
    if severity_order.get(sev, 0) > severity_order.get(max_sev, 1):
        return False

    return True


def _match_keyword_conflict(conditions: dict, issue: dict) -> bool:
    """RULE-004/006: 关键词冲突检测（触发词 + 安全词同时存在 → 假阳性）。"""
    trigger = conditions.get("trigger_keywords", {})
    safe = conditions.get("safe_keywords", {})

    # 检查触发词
    trigger_fields = trigger.get("fields", [])
    trigger_kws = trigger.get("keywords", [])
    trigger_match = _any_field_contains(issue, trigger_fields, trigger_kws)

    if not trigger_match:
        return False

    # 检查安全词
    safe_fields = safe.get("fields", [])
    safe_kws = safe.get("keywords", [])
    safe_match = _any_field_contains(issue, safe_fields, safe_kws)

    return safe_match


def _match_code_pattern(conditions: dict, issue: dict) -> bool:
    """RULE-005: 代码模式匹配。"""
    # 检查类别
    category = conditions.get("category", "")
    if category and issue.get("category") != category:
        return False

    # 检查标题关键词
    title = issue.get("title", "")
    title_kws = conditions.get("title_contains", [])
    title_match = any(kw in title for kw in title_kws)

    if not title_match:
        return False

    # 检查代码中的函数名模式
    code = issue.get("code_reference", "") or issue.get("description", "")
    pattern = conditions.get("code_pattern", "")
    if pattern and re.search(pattern, code):
        return True

    return False


def _match_undefined_in_context(conditions: dict, issue: dict) -> bool:
    """RULE-010: AST 压缩截断导致的「未定义变量」误报。

    策略：检查 issue 中引用的变量名是否出现在 code_reference 中，
    如果 code_reference 包含完整的变量赋值/声明 → 不是误报。
    如果 code_reference 只使用变量但未声明 → 可能是截断误报 → 过滤。
    """
    trigger = conditions.get("trigger_keywords", {})
    trigger_fields = trigger.get("fields", [])
    trigger_kws = trigger.get("keywords", [])

    # 检查是否触发关键词
    matched = _any_field_contains(issue, trigger_fields, trigger_kws)
    if not matched:
        return False

    # 获取代码引用
    code_ref = issue.get("code_reference", "") or issue.get("description", "")

    # 简单启发式：如果代码引用包含 const/let/var/function/import 声明
    # 说明变量在可见范围内有定义 → 不是误报，不拦截
    if any(
        keyword in code_ref
        for keyword in ("const ", "let ", "var ", "function ", "import ", "from ", "def ")
    ):
        return False

    # 否则可能是 AST 压缩截断导致的误报 → 过滤
    return True


def _any_field_contains(issue: dict, fields: list[str], keywords: list[str]) -> bool:
    """检查 issue 的任一字段是否包含任一关键词。"""
    for field in fields:
        value = _get_field(issue, field)
        for kw in keywords:
            if kw in value:
                return True
    return False


# ── CLI 入口 ──

if __name__ == "__main__":
    import argparse

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    # 构造一组测试 issues
    test_issues = [
        {"line": 10, "severity": "warning", "category": "security",
         "title": "SQL 注入风险", "description": "使用了 ORM session.query 可能不安全",
         "code_reference": "session.query(User).filter(...)"},
        {"line": 20, "severity": "suggestion", "category": "style",
         "title": "考虑重命名变量", "description": "Consider renaming 'x' to something meaningful"},
        {"line": 30, "severity": "critical", "category": "correctness",
         "title": "可能的空指针", "description": "没有 None 检查"},
        {"line": 40, "severity": "suggestion", "category": "style",
         "title": "缺少类型注解", "description": "_private_func 缺少返回类型注解",
         "code_reference": "_private_func()"},
        {"line": 50, "severity": "warning", "category": "security",
         "title": "硬编码密码", "description": "代码中使用了硬编码的密码",
         "code_reference": "password = os.getenv('DB_PASSWORD')"},
    ]

    print("=" * 60)
    print("规则引擎测试")
    print("=" * 60)

    rules = load_rules()
    print(f"已加载 {len(rules)} 条规则\n")

    for issue in test_issues:
        fp = "fastapi/app.py"
        result = _apply_rules(issue, fp, rules)
        action = result["action"]
        rule_id = result["rule_id"] or "-"
        print(f"  [{action:>10}] [{rule_id}] {issue['title']} ({issue['severity']})")

    # 测试文件路径过滤
    test_issue2 = {"line": 1, "severity": "warning", "category": "style",
                   "title": "命名不规范", "description": "变量名不符合规范"}
    fp_test = "tests/test_user.py"
    result = _apply_rules(test_issue2, fp_test, rules)
    print(f"\n  测试文件规则:")
    print(f"  [{result['action']:>10}] [{result['rule_id']}] {test_issue2['title']} in {fp_test}")
