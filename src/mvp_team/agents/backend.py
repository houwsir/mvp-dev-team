"""后端工程师（贝洛奇）—— 按 API 契约实现后端业务代码。"""

from __future__ import annotations

from typing import Any

from mvp_team.agents.base import ev, persist_generated, project_dir, rework_block, scan_tree
from mvp_team.prompts import SYSTEM_BACKEND, memory_block
from mvp_team.state import TeamState
from mvp_team.tools.scaffold import skeleton_paths

ROLE = "backend"


def make_nodes(llm: Any, settings: Any) -> dict[str, Any]:
    def backend_dev(state: TeamState) -> dict[str, Any]:
        root = project_dir(state)
        tree = "\n".join(f"- {p}" for p in scan_tree(root, limit=140)) or "- （尚无文件）"

        user = (
            memory_block("原始需求", state.get("raw_idea", ""))
            + memory_block("项目简报", state.get("brief"))
            + memory_block("PRD", state.get("prd"))
            + memory_block("技术方案与 API 契约（必须严格实现）", state.get("architecture"))
            + "\n## 磁盘上已存在的文件（工程骨架，不可修改）\n"
            + tree
            + "\n\n请严格按上面的文件树确定自己的落点：只输出 `backend/app/` 下的**业务文件**"
            "（models / schemas / repositories / services / api/routes / api/router / main / seed），"
            "不要重复输出 `requirements.txt`、`app/config.py`、`app/database.py`、"
            "`app/**/__init__.py`、`tests/conftest.py` 这些骨架文件。\n"
            "再次强调：不要写占位符，每个文件都要完整可运行。"
            + rework_block(state, ROLE)
        )
        text = llm.say(ROLE, SYSTEM_BACKEND, user)
        files, warnings = persist_generated(
            state, text, ROLE, forbid=skeleton_paths()
        )

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
        if warnings:
            from mvp_team.state import Event

            update["events"].append(
                Event(role=ROLE, title="🛡️ 骨架文件保护拦截", detail="；".join(warnings[:5]), status="warn")
            )
        update["artifacts"] = list(files)
        update["run_log"] = [f"[backend] files -> {len(files)}"]
        return update

    return {"backend_dev": backend_dev}
