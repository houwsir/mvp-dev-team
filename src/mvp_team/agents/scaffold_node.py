"""工程骨架节点（不走模型）。

在架构与设计开工之前，用**纯代码**把工程基线铺到产物目录：构建配置、
数据库/配置底座、测试脚手架、部署脚本、一键启动、Makefile。

为什么放在这么靠前：所有下游角色（架构师、设计师、两位工程师、测试、运维）
之后的提示词里都会带上「磁盘上真实存在的文件树」，让它们不再臆造路径；
同时骨架导出的符号（``get_settings`` / ``Base`` / ``get_db`` / ``client`` fixture）
成为上下游共享的**代码级契约**，取代过去靠各自猜的做法。
"""

from __future__ import annotations

from typing import Any

from mvp_team.agents.base import artifact_for, ev, project_dir
from mvp_team.state import TeamState
from mvp_team.tools.scaffold import (
    ensure_template_root,
    render_scaffold_summary,
    skeleton_paths,
    write_scaffold,
)

# 骨架属于「架构阶段的基础设施」，事件挂在架构师名下，保持 8 人叙事完整
ROLE = "architect"


def make_nodes(llm: Any, settings: Any) -> dict[str, Any]:
    def scaffold_baseline(state: TeamState) -> dict[str, Any]:
        # 模板缺失就直接失败：没有骨架的产物必然不可运行
        ensure_template_root()

        root = project_dir(state)
        results = write_scaffold(root)

        # 骨架文件也登记为产物，便于最终统计与交付说明
        artifacts = []
        for rel, action in results:
            if action == "kept":
                continue
            path = root / rel
            if path.is_file():
                artifacts.append(artifact_for(path, root, ROLE, state.get("project_name", "")))

        created = sum(1 for _, a in results if a == "created")
        updated = sum(1 for _, a in results if a == "updated")
        protected = len(skeleton_paths())

        detail = (
            f"{render_scaffold_summary(results)}｜其中 {protected} 个为受保护骨架文件（工程师不可覆盖）"
        )

        update: dict[str, Any] = {
            "scaffold_files": artifacts,
            "artifacts": list(artifacts),
            "run_log": [f"[scaffold] created={created} updated={updated} protected={protected}"],
        }
        update.update(
            ev(
                ROLE,
                "🧱 工程骨架已铺好",
                detail=detail,
                data={"files": [r for r, _ in results]},
            )
        )
        return update

    return {"scaffold_baseline": scaffold_baseline}


__all__ = ["make_nodes", "ROLE"]
