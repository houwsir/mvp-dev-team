"""首席架构师（高见远）—— 技术选型、数据模型、API 契约、代码级契约冻结。"""

from __future__ import annotations

from typing import Any

from mvp_team.agents.base import (
    artifact_for,
    ev,
    project_dir,
    render_architecture_md,
    scan_tree,
    write_text,
)
from mvp_team.prompts import STACK_PROFILE, SYSTEM_ARCHITECT, memory_block
from mvp_team.schemas import Architecture
from mvp_team.state import TeamState
from mvp_team.tools.contract_check import build_contract, render_contract_md
from mvp_team.tools.scaffold import template_files

ROLE = "architect"


def make_nodes(llm: Any, settings: Any) -> dict[str, Any]:
    def architect_design(state: TeamState) -> dict[str, Any]:
        root = project_dir(state)
        tree = "\n".join(f"- {p}" for p in scan_tree(root, limit=140)) or "- （尚无文件）"

        user = (
            memory_block("原始需求", state.get("raw_idea", ""))
            + memory_block("项目简报", state.get("brief"))
            + memory_block("PRD", state.get("prd"))
            + memory_block("交付计划", state.get("plan"))
            + "\n## 磁盘上已存在的文件（工程骨架，不属于任何工程师的交付范围）\n"
            + tree
            + "\n\n请产出技术方案与 API 契约。"
            "`directory_layout` 只需列出**业务文件**，不要列骨架文件。"
        )
        arch = llm.structured(ROLE, SYSTEM_ARCHITECT, user, Architecture)
        if arch is None:
            arch = Architecture(overview="技术方案生成失败。", stack=dict(STACK_PROFILE))

        data = arch.model_dump()
        path = root / "docs" / "ARCHITECTURE.md"
        write_text(path, render_architecture_md(data))

        # ---- 代码级契约：把「骨架接口 + 环境变量 + 测试 fixture + 接口清单」冻结成文档 ----
        contract = build_contract(data, scaffold_files=template_files())
        contract_path = root / "docs" / "CONTRACT.md"
        write_text(contract_path, render_contract_md(contract))

        docs = [
            artifact_for(path, root, ROLE, state.get("project_name", "")),
            artifact_for(contract_path, root, ROLE, state.get("project_name", "")),
        ]

        update: dict[str, Any] = {"architecture": data, "contract": contract}
        update.update(
            ev(
                ROLE,
                "🏛️ 技术方案与契约已冻结",
                detail=(
                    f"技术选型 {len(arch.stack)} 层 / 数据表 {len(arch.data_models)} 张 / "
                    f"接口 {len(arch.api_contract)} 个 / 业务文件 {len(arch.directory_layout)} 个"
                ),
            )
        )
        update["docs_files"] = docs
        update["artifacts"] = list(docs)
        update["run_log"] = [f"[architect] contract -> {len(arch.api_contract)} endpoints"]
        return update

    return {"architect_design": architect_design}
