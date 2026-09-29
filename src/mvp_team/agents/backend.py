"""后端工程师（贝洛奇）—— 按 API 契约实现后端服务。"""

from __future__ import annotations

from typing import Any

from mvp_team.agents.base import ev, persist_generated, rework_block
from mvp_team.prompts import SYSTEM_BACKEND, memory_block
from mvp_team.state import TeamState

ROLE = "backend"


def make_nodes(llm: Any, settings: Any) -> dict[str, Any]:
    def backend_dev(state: TeamState) -> dict[str, Any]:
        user = (
            memory_block("原始需求", state.get("raw_idea", ""))
            + memory_block("项目简报", state.get("brief"))
            + memory_block("PRD", state.get("prd"))
            + memory_block("技术方案与 API 契约（必须严格实现）", state.get("architecture"))
            + rework_block(state, ROLE)
            + "\n请输出后端的**全部**源码文件（含 requirements.txt）。再次强调：不要写占位符，"
            "每个文件都要完整可运行，路径严格按架构师的目录交付清单。"
        )
        text = llm.say(ROLE, SYSTEM_BACKEND, user)
        files, warnings = persist_generated(state, text, ROLE)

        update: dict[str, Any] = {"backend_files": files}
        update.update(
            ev(
                ROLE,
                "⚙️ 后端服务已实现",
                detail=f"写入 {len(files)} 个文件，共 {sum(f.lines for f in files)} 行"
                + (f"｜告警 {len(warnings)}" if warnings else ""),
                status="warn" if warnings else "done",
                data={"files": [f.path for f in files], "warnings": warnings},
            )
        )
        update["artifacts"] = list(files)
        update["run_log"] = [f"[backend] files -> {len(files)}"]
        return update

    return {"backend_dev": backend_dev}
