"""项目总监（大湾区靓仔）—— 开工拆解 + 收尾验收。"""

from __future__ import annotations

import json
import re
from typing import Any

from mvp_team.agents.base import artifact_for, ev, project_dir, write_text
from mvp_team.llm import TeamLLM
from mvp_team.prompts import (
    SYSTEM_DIRECTOR_BRIEF,
    SYSTEM_DIRECTOR_PLAN,
    SYSTEM_DIRECTOR_REVIEW,
    memory_block,
)
from mvp_team.schemas import DeliveryPlan, ProjectBrief
from mvp_team.state import TeamState
from mvp_team.tools.jsonx import extract_json

ROLE = "director"


def _slugify(text: str) -> str:
    ascii_part = re.sub(r"[^a-zA-Z0-9\- ]+", " ", text).strip().lower()
    ascii_part = re.sub(r"\s+", "-", ascii_part).strip("-")
    return ascii_part[:32] or "mvp-project"


def _fallback_brief(idea: str) -> ProjectBrief:
    return ProjectBrief(
        project_name="mvp-project",
        one_liner=idea.strip()[:60] or "一个最小可用产品",
        goal=idea.strip() or "把想法做成可运行的最小产品",
        target_users=["目标用户"],
        scenarios=[idea.strip()[:80]],
        scope_in=["核心主流程闭环"],
        scope_out=["支付", "多租户", "复杂权限"],
        acceptance=["核心流程可完整走通", "前后端可本地启动"],
    )


def make_nodes(llm: TeamLLM, settings: Any) -> dict[str, Any]:
    def director_brief(state: TeamState) -> dict[str, Any]:
        idea = state.get("raw_idea", "").strip()
        brief = llm.structured(ROLE, SYSTEM_DIRECTOR_BRIEF, f"用户原话：\n\n{idea}", ProjectBrief)
        if brief is None:
            brief = _fallback_brief(idea)

        project_name = brief.project_name or _slugify(idea)
        update: dict[str, Any] = {
            "brief": brief.model_dump(),
            "project_name": project_name,
            "summary": "",
        }
        update.update(
            ev(
                ROLE,
                "📌 锁定项目简报",
                detail=f"{brief.one_liner}｜范围 {len(brief.scope_in)} 项，明确不做 {len(brief.scope_out)} 项",
                data={"project_name": project_name},
            )
        )
        update["run_log"] = [f"[director] brief -> {project_name}"]
        return update

    def director_plan(state: TeamState) -> dict[str, Any]:
        user = memory_block("项目简报", state.get("brief")) + "\n请把交付拆解为任务并指派给团队成员。"
        plan = llm.structured(ROLE, SYSTEM_DIRECTOR_PLAN, user, DeliveryPlan)
        if plan is None:
            plan = DeliveryPlan(
                summary="按 8 人团队标准流水线交付：PRD → 设计 → 架构 → 前后端实现 → 测试 → 部署。",
                tasks=[],
            )
        root = project_dir(state)
        root.mkdir(parents=True, exist_ok=True)
        md = ["# 交付计划", "", f"{plan.summary}", "", "| 编号 | 任务 | 负责人 | 交付物 | 依赖 |", "| --- | --- | --- | --- | --- |"]
        for t in plan.tasks:
            md.append(
                f"| {t.id} | {t.title} | {t.owner} | {t.deliverable} | {'、'.join(t.depends_on) or '-'} |"
            )
        path = root / "docs" / "PLAN.md"
        write_text(path, "\n".join(md) + "\n")

        update: dict[str, Any] = {"plan": [t.model_dump() for t in plan.tasks]}
        update.update(
            ev(ROLE, "🗂️ 完成任务拆解", detail=f"{len(plan.tasks)} 个任务已指派给团队成员")
        )
        update["docs_files"] = [artifact_for(path, root, ROLE, state.get("project_name", ""))]
        update["artifacts"] = list(update["docs_files"])
        update["run_log"] = [f"[director] plan -> {len(plan.tasks)} tasks"]
        return update

    def director_review(state: TeamState) -> dict[str, Any]:
        root = project_dir(state)
        payload = {
            "brief": state.get("brief"),
            "plan": state.get("plan"),
            "test_report": state.get("test_report"),
            "qa_passed": state.get("qa_passed"),
            "files": sorted({a.path for a in state.get("artifacts", [])}),
        }
        text = llm.say(
            ROLE,
            SYSTEM_DIRECTOR_REVIEW,
            "以下是本次交付的全部事实依据：\n\n" + json.dumps(payload, ensure_ascii=False, indent=2)[:60000],
        )

        body, summary_obj = _split_summary(text)
        path = root / "docs" / "HANDOVER.md"
        write_text(path, body + "\n")

        update: dict[str, Any] = {"summary": body}
        update.update(
            ev(ROLE, "🎉 交付验收完成", detail=summary_obj.get("project_name", "") or "已输出交付说明")
        )
        update["docs_files"] = [artifact_for(path, root, ROLE, state.get("project_name", ""))]
        update["artifacts"] = list(update["docs_files"])
        update["run_log"] = ["[director] review -> handover written"]
        return update

    return {
        "director_brief": director_brief,
        "director_plan": director_plan,
        "director_review": director_review,
    }


def _split_summary(text: str) -> tuple[str, dict[str, Any]]:
    """把交付说明与结尾的 JSON 汇总拆开。"""
    matches = list(re.finditer(r"```json\s*(?P<body>.*?)```", text, re.DOTALL))
    if not matches:
        return text.strip(), {}
    last = matches[-1]
    obj = extract_json(last.group("body")) or {}
    body = (text[: last.start()] + text[last.end() :]).strip()
    return body, obj if isinstance(obj, dict) else {}
