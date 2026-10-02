"""前端工程师（贾思敏）—— 按设计规范与 API 契约实现前端业务代码。"""

from __future__ import annotations

from typing import Any

from mvp_team.agents.base import (
    declared_files_block,
    ev,
    persist_generated,
    project_dir,
    rework_block,
    scan_tree,
)
from mvp_team.prompts import SYSTEM_FRONTEND, memory_block
from mvp_team.state import Event, TeamState
from mvp_team.tools.scaffold import skeleton_paths

ROLE = "frontend"


def make_nodes(llm: Any, settings: Any) -> dict[str, Any]:
    def frontend_dev(state: TeamState) -> dict[str, Any]:
        root = project_dir(state)
        tree = "\n".join(f"- {p}" for p in scan_tree(root, limit=160)) or "- （尚无文件）"

        user = (
            memory_block("原始需求", state.get("raw_idea", ""))
            + memory_block("项目简报", state.get("brief"))
            + memory_block("PRD（页面与路由以此为准）", state.get("prd"))
            + memory_block("技术方案与 API 契约（前端调用以此为准）", state.get("architecture"))
            + memory_block("UI/UX 设计规范（样式以此为准）", state.get("design"))
            + "\n## 磁盘上已存在的文件（工程骨架，不可修改）\n"
            + tree
            + declared_files_block(state, "frontend/src/")
            + "\n\n请严格按上面的文件树确定自己的落点：只输出 `frontend/src/` 下的**业务文件**"
            "（App.tsx / pages/*.tsx / components/*.tsx / api/client.ts / types.ts / styles/*.css），"
            "不要重复输出 `package.json`、`tsconfig.json`、`vite.config.ts`、`index.html`、"
            "`src/main.tsx`、`src/vite-env.d.ts` 这些骨架文件。\n"
            "接口路径与字段必须与 API 契约一字不差，不要用假数据。"
            + rework_block(state, ROLE)
        )
        text = llm.say(ROLE, SYSTEM_FRONTEND, user)
        files, warnings = persist_generated(state, text, ROLE, forbid=skeleton_paths())

        update: dict[str, Any] = {"frontend_files": files}
        update.update(
            ev(
                ROLE,
                "🖥️ 前端页面已实现",
                detail=f"写入 {len(files)} 个文件，共 {sum(f.lines for f in files)} 行"
                + (f"｜告警 {len(warnings)}" if warnings else "")
                + ("｜⚠️ 本轮未产出任何文件" if not files else ""),
                status="warn" if warnings else "done",
                data={"files": [f.path for f in files], "warnings": warnings},
            )
        )
        if warnings:
            update["events"].append(
                Event(role=ROLE, title="🛡️ 骨架文件保护拦截", detail="；".join(warnings[:5]), status="warn")
            )
        if not files:
            update["events"].append(
                Event(
                    role=ROLE,
                    title="⚠️ 本轮未产出任何前端文件",
                    detail=(
                        "落盘协议没有解析出任何 ```file: 块。"
                        "若这是返工轮，说明上一轮的缺陷没有被修复，质量门大概率会再次驳回。"
                    ),
                    status="warn",
                )
            )
        update["artifacts"] = list(files)
        update["run_log"] = [f"[frontend] files -> {len(files)}"]
        return update

    return {"frontend_dev": frontend_dev}
