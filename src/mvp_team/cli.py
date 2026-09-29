"""命令行入口。

    mvp-team run "我想做一个电商小程序后台" --out ./generated
    mvp-team roster
    mvp-team graph
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

from mvp_team.agents import ROSTER, roster_text
from mvp_team.config import Settings
from mvp_team.graph import build_graph, run_workflow
from mvp_team.prompts import PERSONAS

# ---------------------------------------------------------------- 终端着色（无依赖）

_COLOR = {
    "reset": "\033[0m",
    "dim": "\033[2m",
    "bold": "\033[1m",
    "green": "\033[32m",
    "yellow": "\033[33m",
    "red": "\033[31m",
    "cyan": "\033[36m",
    "blue": "\033[34m",
    "magenta": "\033[35m",
}


def _c(text: str, color: str) -> str:
    if not sys.stdout.isatty():
        return text
    return f"{_COLOR.get(color, '')}{text}{_COLOR['reset']}"


def _role_tag(role: str) -> str:
    p = PERSONAS.get(role, {"emoji": "•", "title": role, "name": ""})
    return f"{p['emoji']} {p['title']}·{p.get('name','')}"


# ---------------------------------------------------------------- 子命令


def cmd_run(args: argparse.Namespace) -> int:
    settings = Settings.load()
    if args.dry_run:
        settings.dry_run = True
    if args.verify_frontend:
        settings.verify_frontend = True
    if args.max_qa_rounds is not None:
        settings.max_qa_rounds = args.max_qa_rounds
    if args.model:
        settings.model = args.model

    print()
    print(_c("═" * 72, "blue"))
    print(_c("  MVP 开发专家团 · 8 位专家在线", "bold"))
    print(_c("═" * 72, "blue"))
    print(f"  🎯 需求：{args.idea}")
    print(f"  📦 产物目录：{Path(args.out).expanduser().resolve()}")
    print(
        f"  🤖 模型：{'(离线演练 dry-run)' if settings.dry_run else settings.model}"
        f"｜端点：{settings.base_url or '默认'}"
    )
    print(_c("─" * 72, "dim"))

    files_written: list[str] = []

    def on_event(payload: dict) -> None:
        e = payload["event"]
        icon = {"done": "✅", "warn": "⚠️ ", "fail": "❌", "running": "⏳"}.get(e.status, "•")
        color = {"done": "green", "warn": "yellow", "fail": "red"}.get(e.status, "cyan")
        tag = _c(f"[{_role_tag(e.role)}]", "magenta")
        print(f"{icon} {tag} {e.title}")
        if e.detail:
            for line in str(e.detail).splitlines():
                print(f"    {_c('└ ' + line, 'dim')}")
        for path in (e.data or {}).get("files", [])[:200]:
            files_written.append(path)

    try:
        final = run_workflow(
            idea=args.idea,
            output_dir=args.out,
            settings=settings,
            on_event=on_event,
        )
    except KeyboardInterrupt:
        print(_c("\n⛔ 已被用户中断。", "yellow"))
        return 130
    except Exception as exc:  # noqa: BLE001
        print(_c(f"\n💥 运行失败：{exc}", "red"))
        if args.verbose:
            raise
        return 1

    _print_summary(final, settings)

    if args.json:
        out = _json_summary(final, settings)
        print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0 if final.get("qa_passed") or (final.get("qa_round") or 0) > 0 else 1


def _print_summary(final: dict, settings: Settings) -> None:
    artifacts = final.get("artifacts", [])
    docs = final.get("docs_files", [])
    unique = sorted({a.path for a in artifacts})
    print(_c("─" * 72, "dim"))
    print(_c("  📊 交付汇总", "bold"))
    print(f"  项目代号：{final.get('project_name', '-')}")
    print(f"  质量门：{'✅ 放行' if final.get('qa_passed') else '❌ 未通过'}（共 {final.get('qa_round', 0)} 轮）")
    print(f"  产出文件：{len(unique)} 个（其中文档 {len(docs)} 份）")
    backend = final.get("backend_files") or []
    frontend = final.get("frontend_files") or []
    tests = final.get("test_files") or []
    deploy = final.get("deploy_files") or []
    print(f"    ⚙️ 后端 {len(backend)} 个 ｜ 🖥️ 前端 {len(frontend)} 个 ｜ 🔍 测试 {len(tests)} 个 ｜ 🚀 部署 {len(deploy)} 个")
    if settings.dry_run:
        print(_c("  注意：本次为 dry-run 演练，未调用真实模型。", "yellow"))
    print(_c("─" * 72, "dim"))
    for path in unique[:40]:
        print(f"    {path}")
    if len(unique) > 40:
        print(f"    ... 其余 {len(unique) - 40} 个文件见产物目录")
    print()


def _json_summary(final: dict, settings: Settings) -> dict:
    return {
        "project_name": final.get("project_name"),
        "qa_passed": bool(final.get("qa_passed")),
        "qa_round": final.get("qa_round", 0),
        "model": settings.model,
        "dry_run": settings.dry_run,
        "brief": final.get("brief"),
        "test_report": final.get("test_report"),
        "files": sorted({a.path for a in final.get("artifacts", [])}),
        "events": [asdict(e) for e in final.get("events", [])],
    }


def cmd_roster(_: argparse.Namespace) -> int:
    print()
    print(_c("  MVP 开发专家团 · 团队成员", "bold"))
    print()
    print(roster_text())
    print()
    return 0


def cmd_graph(_: argparse.Namespace) -> int:
    print()
    print(build_graph.__doc__ or "")
    print(_c("  拓扑文字说明见 src/mvp_team/graph.py 顶部注释", "dim"))
    print("  " + " → ".join(name for name in ["START", "director_brief", "director_plan", "pm_analyze"]))
    print("  ↑ 之后 {architect_design ∥ ui_design} → {backend_dev ∥ frontend_dev} → qa_test")
    print("  ↑ qa_test 未通过则打回工程师返工，通过后 → devops_deploy → devops_docs → director_review → END")
    print()
    return 0


# ---------------------------------------------------------------- 解析


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="mvp-team",
        description="MVP 开发专家团：一句话生成可运行的 MVP 产品源码",
    )
    sub = parser.add_subparsers(dest="command")

    run = sub.add_parser("run", help="运行完整开发流水线")
    run.add_argument("idea", help="一句话需求，例如：我想做一个电商小程序后台")
    run.add_argument("--out", default="generated", help="产物根目录（默认 ./generated）")
    run.add_argument("--model", default=None, help="覆盖环境变量中的模型名")
    run.add_argument("--max-qa-rounds", type=int, default=None, help="质量门最多返工轮数")
    run.add_argument("--verify-frontend", action="store_true", help="质量门里额外执行 npm install + build")
    run.add_argument("--dry-run", action="store_true", help="离线演练：不调用真实模型")
    run.add_argument("--json", action="store_true", help="额外输出 JSON 形式的运行摘要")
    run.add_argument("-v", "--verbose", action="store_true", help="异常时打印完整堆栈")
    run.set_defaults(func=cmd_run)

    roster = sub.add_parser("roster", help="查看团队成员")
    roster.set_defaults(func=cmd_roster)

    graph_cmd = sub.add_parser("graph", help="查看工作流拓扑")
    graph_cmd.set_defaults(func=cmd_graph)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not getattr(args, "command", None):
        parser.print_help()
        return 0
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
