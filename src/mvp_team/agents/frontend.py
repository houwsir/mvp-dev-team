"""前端工程师（贾思敏）—— 按设计规范与 API 契约实现前端页面。"""

from __future__ import annotations

from typing import Any

from mvp_team.agents.base import ev, persist_generated, rework_block
from mvp_team.prompts import SYSTEM_FRONTEND, memory_block
from mvp_team.state import TeamState

ROLE = "frontend"


def make_nodes(llm: Any, settings: Any) -> dict[str, Any]:
    def frontend_dev(state: TeamState) -> dict[str, Any]:
        user = (
            memory_block("原始需求", state.get("raw_idea", ""))
            + memory_block("项目简报", state.get("brief"))
            + memory_block("PRD（页面与路由以此为准）", state.get("prd"))
            + memory_block("技术方案与 API 契约（前端调用以此为准）", state.get("architecture"))
            + memory_block("UI/UX 设计规范（样式以此为准）", state.get("design"))
            + rework_block(state, ROLE)
            + "\n请输出前端的**全部**源码文件（含 package.json / vite.config.ts / tsconfig*.json / index.html）。"
            "再次强调：接口路径与字段必须与 API 契约一字不差，不要用假数据。"
        )
        text = llm.say(ROLE, SYSTEM_FRONTEND, user)
        files, warnings = persist_generated(state, text, ROLE)

        update: dict[str, Any] = {"frontend_files": files}
        update.update(
            ev(
                ROLE,
                "🖥️ 前端页面已实现",
                detail=f"写入 {len(files)} 个文件，共 {sum(f.lines for f in files)} 行"
                + (f"｜告警 {len(warnings)}" if warnings else ""),
                status="warn" if warnings else "done",
                data={"files": [f.path for f in files], "warnings": warnings},
            )
        )
        update["artifacts"] = list(files)
        update["run_log"] = [f"[frontend] files -> {len(files)}"]
        return update

    return {"frontend_dev": frontend_dev}
