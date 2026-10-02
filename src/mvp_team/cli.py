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
    if getattr(args, "no_smoke", False):
        settings.run_smoke = False
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

    # 退出码如实反映交付状态：dry-run 是演练，始终算成功
    if settings.dry_run:
        return 0
    return 0 if final.get("delivery_status") == "ok" else 1


def _count_products(final: dict) -> dict[str, int]:
    """按类别统计**磁盘上真实存在**的产物数量。

    为什么要扫盘而不是直接 ``len(state["backend_files"])``：
    ``backend_files`` / ``frontend_files`` / ``test_files`` 在返工时会被**整体覆盖**，
    所以「最后一轮某个角色写了 0 个文件」会让汇总显示成 0——
    但磁盘上明明躺着前几轮写好的十几个文件。
    真实运行里就出现过「后端 0 个」这种明显误导的汇总，故改为以磁盘为准。

    受保护的骨架文件不计入任何业务类别（工程师并未创作它们）。
    """
    from mvp_team.agents.base import project_dir, scan_tree
    from mvp_team.tools.scaffold import skeleton_paths

    counts = {"backend": 0, "frontend": 0, "tests": 0, "deploy": 0}
    try:
        root = project_dir(final)
    except Exception:  # noqa: BLE001 - 汇总打印不应因统计失败而中断
        return counts

    if not root.is_dir():
        return counts

    protected = skeleton_paths()
    for rel in scan_tree(root, limit=2000):
        if rel in protected:
            continue
        if rel.startswith("backend/tests/"):
            counts["tests"] += 1
        elif rel.startswith("backend/"):
            counts["backend"] += 1
        elif rel.startswith("frontend/"):
            counts["frontend"] += 1
        elif rel.startswith("deploy/") or rel in {"Makefile", "docker-compose.yml"}:
            counts["deploy"] += 1
    return counts


def _print_summary(final: dict, settings: Settings) -> None:
    artifacts = final.get("artifacts", [])
    docs = final.get("docs_files", [])
    scaffold = final.get("scaffold_files") or []
    unique = sorted({a.path for a in artifacts})

    smoke = final.get("smoke_report") or {}
    if not smoke or (smoke.get("facts") or {}).get("skipped"):
        smoke_txt = "（未执行）"
    else:
        smoke_txt = "✅ 通过" if smoke.get("ok") else "❌ 未通过"

    status = final.get("delivery_status") or "pending"
    status_txt = {
        "ok": "✅ 通过质量门",
        "risk": "⚠️  未通过质量门（带风险交付）",
    }.get(status, status)

    print(_c("─" * 72, "dim"))
    print(_c("  📊 交付汇总", "bold"))
    print(f"  项目代号：{final.get('project_name', '-')}")
    print(f"  质量门：{'✅ 放行' if final.get('qa_passed') else '❌ 未通过'}（共 {final.get('qa_round', 0)} 轮）")
    print(f"  冒烟测试：{smoke_txt}")
    print(f"  交付状态：{status_txt}")
    print(f"  产出文件：{len(unique)} 个（其中工程骨架 {len(scaffold)} 个、文档 {len(docs)} 份）")
    counted = _count_products(final)
    print(
        f"    ⚙️ 后端 {counted['backend']} 个 ｜ 🖥️ 前端 {counted['frontend']} 个 ｜ "
        f"🔍 测试 {counted['tests']} 个 ｜ 🚀 部署 {counted['deploy']} 个"
    )
    if settings.dry_run:
        print(_c("  注意：本次为 dry-run 演练，未调用真实模型。", "yellow"))
    if status == "risk":
        print(_c("  注意：本项目未通过质量门，详见 docs/DELIVERY_STATUS.md", "red"))
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
        "delivery_status": final.get("delivery_status", "pending"),
        "smoke_passed": (final.get("smoke_report") or {}).get("ok"),
        "model": settings.model,
        "dry_run": settings.dry_run,
        "brief": final.get("brief"),
        "contract": final.get("contract"),
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
    print("  " + " → ".join(["START", "director_brief", "director_plan", "pm_analyze", "scaffold_baseline"]))
    print("  ↑ 之后 {architect_design ∥ ui_design} → {backend_dev ∥ frontend_dev} → qa_test")
    print("  ↑ qa_test 四道证据：契约一致性 → 静态体检 → 真跑 pytest → 真启动服务冒烟")
    print("  ↑ 未通过则打回工程师返工；通过或额度用尽后 → devops_deploy → devops_docs → director_review → END")
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
    run.add_argument("--no-smoke", action="store_true", help="跳过冒烟门（不启动服务打接口）")
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
