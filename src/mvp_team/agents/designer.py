"""UI/UX 设计师（颜好看）—— 设计规范、页面布局、设计令牌。"""

from __future__ import annotations

from typing import Any

from mvp_team.agents.base import (
    artifact_for,
    ev,
    project_dir,
    render_design_md,
    write_text,
)
from mvp_team.prompts import SYSTEM_DESIGNER, memory_block
from mvp_team.schemas import DesignSpec
from mvp_team.state import TeamState

ROLE = "designer"


def make_nodes(llm: Any, settings: Any) -> dict[str, Any]:
    def ui_design(state: TeamState) -> dict[str, Any]:
        user = (
            memory_block("项目简报", state.get("brief"))
            + memory_block("PRD", state.get("prd"))
            + "\n请产出 UI/UX 设计规范。"
        )
        spec = llm.structured(ROLE, SYSTEM_DESIGNER, user, DesignSpec)
        if spec is None:
            spec = DesignSpec(style_keywords=["简洁", "高信息密度"])

        data = spec.model_dump()
        root = project_dir(state)
        path = root / "docs" / "DESIGN.md"
        write_text(path, render_design_md(data))

        update: dict[str, Any] = {"design": data}
        update.update(
            ev(
                ROLE,
                "🎨 设计规范已交付",
                detail=(
                    f"风格 {'/'.join(spec.style_keywords[:3]) or '默认'} / "
                    f"色彩令牌 {len(spec.color_tokens)} 个 / 页面布局 {len(spec.layouts)} 个"
                ),
            )
        )
        update["docs_files"] = [artifact_for(path, root, ROLE, state.get("project_name", ""))]
        update["artifacts"] = list(update["docs_files"])
        update["run_log"] = [f"[designer] spec -> {len(spec.layouts)} layouts"]
        return update

    return {"ui_design": ui_design}
