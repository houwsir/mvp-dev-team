"""首席架构师（高见远）—— 技术选型、数据模型、API 契约。"""

from __future__ import annotations

from typing import Any

from mvp_team.agents.base import (
    artifact_for,
    ev,
    project_dir,
    render_architecture_md,
    write_text,
)
from mvp_team.prompts import STACK_PROFILE, SYSTEM_ARCHITECT, memory_block
from mvp_team.schemas import Architecture
from mvp_team.state import TeamState

ROLE = "architect"


def make_nodes(llm: Any, settings: Any) -> dict[str, Any]:
    def architect_design(state: TeamState) -> dict[str, Any]:
        user = (
            memory_block("原始需求", state.get("raw_idea", ""))
            + memory_block("项目简报", state.get("brief"))
            + memory_block("PRD", state.get("prd"))
            + memory_block("交付计划", state.get("plan"))
            + "\n请产出技术方案与 API 契约。"
        )
        arch = llm.structured(ROLE, SYSTEM_ARCHITECT, user, Architecture)
        if arch is None:
            arch = Architecture(overview="技术方案生成失败。", stack=dict(STACK_PROFILE))

        data = arch.model_dump()
        root = project_dir(state)
        path = root / "docs" / "ARCHITECTURE.md"
        write_text(path, render_architecture_md(data))

        update: dict[str, Any] = {"architecture": data}
        update.update(
            ev(
                ROLE,
                "🏛️ 技术方案与契约已冻结",
                detail=(
                    f"技术选型 {len(arch.stack)} 层 / 数据表 {len(arch.data_models)} 张 / "
                    f"接口 {len(arch.api_contract)} 个 / 交付文件 {len(arch.directory_layout)} 个"
                ),
            )
        )
        update["docs_files"] = [artifact_for(path, root, ROLE, state.get("project_name", ""))]
        update["artifacts"] = list(update["docs_files"])
        update["run_log"] = [f"[architect] contract -> {len(arch.api_contract)} endpoints"]
        return update

    return {"architect_design": architect_design}
