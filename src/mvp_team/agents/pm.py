"""产品经理（许清楚）—— 把一句话需求变成可执行的 PRD。"""

from __future__ import annotations

from typing import Any

from mvp_team.agents.base import (
    artifact_for,
    ev,
    project_dir,
    render_prd_md,
    write_text,
)
from mvp_team.prompts import SYSTEM_PM, memory_block
from mvp_team.schemas import PRD
from mvp_team.state import TeamState

ROLE = "pm"


def make_nodes(llm: Any, settings: Any) -> dict[str, Any]:
    def pm_analyze(state: TeamState) -> dict[str, Any]:
        user = (
            memory_block("原始需求", state.get("raw_idea", ""))
            + memory_block("项目简报", state.get("brief"))
            + memory_block("交付计划", state.get("plan"))
            + "\n请据此产出 MVP PRD。"
        )
        prd = llm.structured(ROLE, SYSTEM_PM, user, PRD)
        if prd is None:
            prd = PRD(overview="PRD 生成失败，请检查模型输出格式。")

        data = prd.model_dump()
        root = project_dir(state)
        path = root / "docs" / "PRD.md"
        write_text(path, render_prd_md(data, state.get("brief", {})))

        update: dict[str, Any] = {"prd": data}
        update.update(
            ev(
                ROLE,
                "📋 PRD 已定稿",
                detail=(
                    f"用户故事 {len(prd.user_stories)} 条 / 功能 {len(prd.features)} 项 / "
                    f"页面 {len(prd.pages)} 个 / 实体 {len(prd.entities)} 个"
                ),
            )
        )
        update["docs_files"] = [artifact_for(path, root, ROLE, state.get("project_name", ""))]
        update["artifacts"] = list(update["docs_files"])
        update["run_log"] = [f"[pm] prd -> {len(prd.features)} features"]
        return update

    return {"pm_analyze": pm_analyze}
