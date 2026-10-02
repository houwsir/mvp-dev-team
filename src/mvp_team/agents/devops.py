"""运维工程师（卜宕机）—— 让项目一条命令跑起来。"""

from __future__ import annotations

import os
from typing import Any

from mvp_team.agents.base import (
    artifact_for,
    ev,
    memory_block,
    persist_generated,
    project_dir,
    scan_tree,
    write_text,
)
from mvp_team.prompts import SYSTEM_DEVOPS
from mvp_team.state import Event, TeamState

ROLE = "devops"


def make_nodes(llm: Any, settings: Any) -> dict[str, Any]:
    def devops_deploy(state: TeamState) -> dict[str, Any]:
        root = project_dir(state)
        layout = "\n".join(f"- {p}" for p in scan_tree(root, limit=120))
        user = (
            memory_block("项目简报", state.get("brief"))
            + memory_block("技术方案", state.get("architecture"))
            + memory_block("代码级契约", state.get("contract"))
            + memory_block("测试结论", state.get("test_report"))
            + "\n## 磁盘上真实存在的文件（以此为准，不要臆造路径）\n"
            + (layout or "- （无）")
            + "\n\n请核对 `deploy/` 与 `Makefile` 是否与上面的真实入口一致，"
            "不一致就修正；然后补全/更新根目录 `README.md`。"
        )
        text = llm.say(ROLE, SYSTEM_DEVOPS, user)
        files, warnings = persist_generated(state, text, ROLE)

        # 给 shell 脚本补可执行位
        for f in files:
            if f.path.endswith((".sh", ".command")):
                try:
                    os.chmod(root / f.path, 0o755)
                except OSError:
                    pass

        update: dict[str, Any] = {"deploy_files": files}
        update.update(
            ev(
                ROLE,
                "🚀 部署方案已就绪",
                detail=f"写入 {len(files)} 个文件"
                + (f"，其中启动脚本 {sum(1 for f in files if f.path.endswith('.sh'))} 个" if files else ""),
                status="warn" if warnings else "done",
            )
        )
        update["artifacts"] = list(files)
        update["run_log"] = [f"[devops] files -> {len(files)}"]
        return update

    def devops_docs(state: TeamState) -> dict[str, Any]:
        """收尾：补一份运行手册，并对整份交付物做一次一致性自检。

        质量门跑在运维之前，验证不了「Makefile 里 `bash deploy/start.sh` 指向的脚本
        是否存在」这类问题，所以这里补一道确定性自检，把结论写进 docs/DELIVERY_CHECK.md。
        """
        from mvp_team.tools.delivery_check import check_delivery, render_delivery_report

        root = project_dir(state)
        manual = root / "docs" / "RUNBOOK.md"
        new_docs: list = []
        events: list[Event] = []

        if not manual.is_file():
            test_report = state.get("test_report") or {}
            lines = [
                "# 运行手册",
                "",
                "## 1. 目录结构",
                "",
            ]
            lines += [f"- `{p}`" for p in scan_tree(root, limit=80)] or ["- （无）"]
            lines += [
                "",
                "## 2. 一键启动（推荐）",
                "",
                "```bash",
                f"cd {root}",
                "bash deploy/start.sh",
                "```",
                "",
                "## 3. 手动启动",
                "",
                "```bash",
                "# 后端（端口 8000）",
                "cd backend && python -m venv .venv && source .venv/bin/activate",
                "pip install -r requirements.txt",
                "uvicorn app.main:app --reload --port 8000",
                "",
                "# 前端（端口 5173）",
                "cd frontend && npm install && npm run dev",
                "```",
                "",
                "## 4. 质量门结论",
                "",
                f"- 是否放行：{'✅ 是' if state.get('qa_passed') else '❌ 否'}",
                f"- 测试轮次：{state.get('qa_round', 0)}",
                f"- 概述：{test_report.get('summary', '-')}",
                "",
            ]
            write_text(manual, "\n".join(lines))
            new_docs.append(artifact_for(manual, root, ROLE, state.get("project_name", "")))
            events.append(Event(role=ROLE, title="📖 补写运行手册", detail="docs/RUNBOOK.md"))

        # ---- 交付一致性自检 ----
        result = check_delivery(root)
        report_path = root / "docs" / "DELIVERY_CHECK.md"
        write_text(report_path, render_delivery_report(result))
        new_docs.append(artifact_for(report_path, root, ROLE, state.get("project_name", "")))

        findings = result["findings"]
        high = [f for f in findings if f["severity"] == "high"]
        detail = (
            f"检查 {result['files_checked']} 类必备文件，"
            + (f"发现 {len(findings)} 处不一致（high {len(high)}）" if findings else "未发现不一致")
        )
        events.append(
            Event(
                role=ROLE,
                title="🧾 交付自检完成",
                detail=detail + (f"：{high[0]['issue']}" if high else ""),
                status="warn" if high else "done",
                data={"findings": findings},
            )
        )

        # ---- 交付状态：质量门未通过就必须显式标注，绝不静默当成功交付 ----
        passed = bool(state.get("qa_passed"))
        delivery_status = "ok" if passed else "risk"
        report_data = state.get("test_report") or {}
        smoke = state.get("smoke_report") or {}

        if smoke:
            smoke_line = "✅ 通过" if smoke.get("ok") else "❌ 未通过"
        else:
            smoke_line = "（未执行）"

        status_lines = [
            "# 交付状态",
            "",
            f"- 结论：{'✅ **通过质量门**' if passed else '⚠️ **未通过质量门（带风险交付）**'}",
            f"- 质量门轮次：{state.get('qa_round', 0)}",
            f"- 测试结论：{report_data.get('verdict', '-')}",
            f"- 需要返工：{report_data.get('rework_for', 'none')}",
            f"- 冒烟测试：{smoke_line}",
            f"- 交付自检不一致项：{len(findings)}（其中 high {len(high)}）",
            "",
        ]
        if not passed:
            status_lines += [
                "## 未通过原因",
                "",
                str(report_data.get("summary", "") or "-"),
                "",
                "## 剩余缺陷",
                "",
            ]
            for item in (report_data.get("findings") or [])[:20]:
                status_lines.append(
                    f"- [{item.get('severity')}] `{item.get('where')}` {item.get('issue')}"
                )
            status_lines += [
                "",
                "> 本项目为**带风险交付**：返工轮次已用尽但质量门仍未放行。",
                "> 上方缺陷未修复，请勿直接用于生产环境。",
                "",
            ]

        status_path = root / "docs" / "DELIVERY_STATUS.md"
        write_text(status_path, "\n".join(status_lines))
        new_docs.append(artifact_for(status_path, root, ROLE, state.get("project_name", "")))
        events.append(
            Event(
                role=ROLE,
                title="🚦 交付状态已判定",
                detail="✅ 通过质量门" if passed else "⚠️ 未通过质量门（带风险交付）",
                status="done" if passed else "fail",
            )
        )

        update: dict[str, Any] = {
            "docs_files": new_docs,
            "artifacts": list(new_docs),
            "events": events,
            "delivery_status": delivery_status,
        }
        update["run_log"] = [
            f"[devops] delivery-check -> {len(findings)} findings",
            f"[devops] delivery-status -> {delivery_status}",
        ]
        return update

    return {"devops_deploy": devops_deploy, "devops_docs": devops_docs}
