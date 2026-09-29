"""运维工程师（卜宕机）—— 让项目一条命令跑起来。"""

from __future__ import annotations

import os
from typing import Any

from mvp_team.agents.base import ev, memory_block, persist_generated, project_dir, scan_tree
from mvp_team.prompts import SYSTEM_DEVOPS
from mvp_team.state import TeamState

ROLE = "devops"


def make_nodes(llm: Any, settings: Any) -> dict[str, Any]:
    def devops_deploy(state: TeamState) -> dict[str, Any]:
        root = project_dir(state)
        layout = "\n".join(f"- {p}" for p in scan_tree(root, limit=120))
        user = (
            memory_block("项目简报", state.get("brief"))
            + memory_block("技术方案", state.get("architecture"))
            + memory_block("测试结论", state.get("test_report"))
            + "\n## 磁盘上真实存在的文件（以此为准，不要臆造路径）\n"
            + (layout or "- （无）")
            + "\n\n请输出部署与启动相关的全部文件。"
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
        """补一份运行手册；即使模型没写 README，也保证交付有说明。"""
        root = project_dir(state)
        manual = root / "docs" / "RUNBOOK.md"
        if manual.is_file():
            return ev(ROLE, "📖 运行手册已存在", detail="跳过后补", status="done")
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
            "cd " + str(root),
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
        from mvp_team.agents.base import write_text as _w

        _w(manual, "\n".join(lines))
        from mvp_team.agents.base import artifact_for

        art = artifact_for(manual, root, ROLE, state.get("project_name", ""))
        update: dict[str, Any] = {"docs_files": [art], "artifacts": [art]}
        update.update(ev(ROLE, "📖 补写运行手册", detail="docs/RUNBOOK.md"))
        update["run_log"] = ["[devops] runbook written"]
        return update

    return {"devops_deploy": devops_deploy, "devops_docs": devops_docs}
