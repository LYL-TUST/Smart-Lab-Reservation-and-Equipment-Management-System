#!/usr/bin/env python
"""
AI Code Review Agent — CLI 入口

用法:
    # 审查模式
    python main.py --diff test_data/pr_a.diff                         # 模拟审查
    python main.py --diff test_data/pr_a.diff --compress ast -o r.md  # AST 压缩
    python main.py --diff test_data/pr_a.diff --live                   # 真实 LLM

    # 反馈飞轮模式
    python main.py --mode feedback                                    # 从默认路径跑飞轮
    python main.py --mode feedback --feedback path/to/feedback.json    # 指定反馈文件
"""

import argparse
import logging
import sys


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="AI Code Review Agent — 智能 PR 审查 + 反馈飞轮",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
模式:
  review   审查 PR diff（默认模式）
  feedback 执行反馈飞轮，从 dismiss 数据自动生成规则

示例:
  # 模拟审查
  python main.py --diff test_data/pr_a.diff

  # 真实 LLM 审查 + AST 压缩
    python main.py --diff test_data/pr_a.diff --live --compress ast

  # MCP 模式（工具运行时发现）
  python main.py --diff test_data/pr_a.diff --mcp
  python main.py --diff test_data/pr_a.diff --mcp --compress ast -o report.md

  # 跑飞轮
  python main.py --mode feedback
  python main.py --mode feedback --feedback feedback/feedback_log.json
        """,
    )

    # 通用参数
    parser.add_argument("--mode", choices=["review", "feedback"], default="review",
                        help="运行模式: review=审查, feedback=飞轮（默认 review）")
    parser.add_argument("--verbose", "-v", action="store_true", help="显示详细日志")

    # 审查模式参数
    parser.add_argument("--diff", help="待审查的 .diff 文件路径")
    parser.add_argument("--output", "-o", help="输出 Markdown 报告路径")
    parser.add_argument("--dry-run", action="store_true",
                        help="模拟审查模式（默认开启，加 --live 关闭）")
    parser.add_argument("--live", action="store_true",
                        help="使用真实 LLM（需设置 API Key）")
    parser.add_argument("--compress", choices=["none", "ast"], default="none",
                        help="上下文压缩模式: none=原始diff, ast=AST提取变更函数")
    parser.add_argument("--mcp", action="store_true",
                        help="启用 MCP 协议模式：工具在运行时发现而非编译时 import 绑定")
    parser.add_argument("--no-cache", action="store_true",
                        help="跳过审查缓存（每次都调 LLM）")
    parser.add_argument("--no-degrade", action="store_true",
                        help="禁用降级策略（API 失败时直接报错，不回退 Mock）")

    # 反馈飞轮模式参数
    parser.add_argument("--feedback", help="反馈日志 JSON 路径（--mode feedback 时使用）")
    parser.add_argument("--min-dismiss", type=int, default=3,
                        help="飞轮聚簇最小 dismiss 次数（默认 3）")

    return parser


def run_review_mode(args: argparse.Namespace) -> None:
    """执行 PR 审查。"""
    from src.review_pipeline import review_pr

    if not args.diff:
        print("[ERROR] 审查模式需要 --diff 参数")
        sys.exit(1)

    # 加载 LLM 配置
    config = None
    use_live = args.live

    if use_live:
        try:
            from src.config import load_config, print_config_summary
            config = load_config()
            print_config_summary(config)
            print()
        except ValueError as e:
            print(f"[ERROR] {e}")
            print("[HINT] 不设置 API Key 时使用 --dry-run 模拟审查")
            sys.exit(1)
        dry_run = False
    else:
        dry_run = True

    mode_parts = []
    if use_live:
        mode_parts.append("LIVE")
    else:
        mode_parts.append("DRY-RUN")
    if args.mcp:
        mode_parts.append("MCP")
    mode_label = f"[{'/'.join(mode_parts)}] 审查"
    print(f"{mode_label}: {args.diff}\n")

    if args.mcp:
        print("[MCP] 工具将通过 MCP 协议在运行时发现和调用\n")

    try:
        report = review_pr(
            args.diff, config=config,
            dry_run=dry_run,
            compress=args.compress,
            use_mcp=args.mcp,
            use_cache=not args.no_cache,
            enable_degrade=not args.no_degrade,
        )
    except FileNotFoundError as e:
        print(f"[ERROR] 文件错误: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"[ERROR] 审查失败: {e}")
        logging.exception("详细错误")
        sys.exit(1)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(report)
        print(f"[OK] 报告已保存: {args.output} ({len(report)} 字符)")
    else:
        print(report)

    print("[OK] 审查完成！")


def run_feedback_mode(args: argparse.Namespace) -> None:
    """执行反馈飞轮。

    MCP 模式：通过 MCP 协议调用 feedback_loop 工具，
    演示 MCP registry 中第 4 个工具的实际使用场景。
    """
    if args.mcp:
        # MCP 模式：通过 MCP 客户端调用 record_review_feedback
        from src.mcp_client import LocalRegistryClient

        mcp_client = LocalRegistryClient(servers=["feedback_loop"])
        mcp_client.discover()

        # 通过 MCP 协议记录一次样例反馈（演示 routing）
        # 实际反馈由开发者手动触发，这里只是展示工具调用链路
        try:
            result = mcp_client.call("record_review_feedback", {
                "issue_id": f"sample-{int(__import__('time').time())}",
                "action": "dismiss",
                "reason": "MCP demo: testing tool routing",
                "pr_id": "demo",
                "metadata_json": "{}",
            })
            print(f"[MCP] record_review_feedback 返回: recorded={result.get('recorded')}")
            print(f"[MCP] 当前统计: total={result.get('total_feedback')}, "
                  f"accept={result.get('accept_count')}, "
                  f"dismiss={result.get('dismiss_count')}")
            if result.get('new_rule_candidates', 0) > 0:
                print(f"[MCP] 发现 {result['new_rule_candidates']} 条新规则候选")
        except Exception as e:
            print(f"[MCP] 错误: {e}")

        # 同时执行飞轮分析
        from src.feedback_loop import run_flywheel, print_flywheel_report
        report = run_flywheel(
            feedback_path=args.feedback,
            min_dismiss=args.min_dismiss,
        )
        print_flywheel_report(report)
        if report["errors"]:
            sys.exit(1)
    else:
        # Import 模式
        from src.feedback_loop import run_flywheel, print_flywheel_report

        report = run_flywheel(
            feedback_path=args.feedback,
            min_dismiss=args.min_dismiss,
        )

        print_flywheel_report(report)

        if report["errors"]:
            sys.exit(1)


def main():
    parser = build_parser()
    args = parser.parse_args()

    # 日志级别
    log_level = logging.INFO if args.verbose else logging.WARNING
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    if args.mode == "feedback":
        run_feedback_mode(args)
    else:
        run_review_mode(args)


if __name__ == "__main__":
    main()
