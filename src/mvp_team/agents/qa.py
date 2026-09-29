"""测试工程师（严过关）—— 真实执行的质量门。

流程分四步，尽量让结论落在**客观证据**上：

1. 让模型编写 pytest 用例（只允许写 `backend/tests/`，越界写入会被拦截）；
2. 跑一遍确定性静态体检（前后端路由/调用/依赖/导入是否对得上）；
3. **真的执行 pytest**，拿到原始输出；
4. 把「体检结果 + 测试输出 + 源码」交给模型出报告，并据此决定是否放行。

只要 pytest 没过、或存在 high 级缺陷，就退回给对应工程师返工。
"""

from __future__ import annotations

from typing import Any

from mvp_team.agents.base import (
    artifact_for,
    ev,
    persist_generated,
    project_dir,
    render_test_report_md,
    write_text,
)
from mvp_team.prompts import SYSTEM_QA, SYSTEM_QA_REPORT, memory_block
from mvp_team.schemas import TestReport
from mvp_team.state import Event, TeamState
from mvp_team.tools.runner import collect_sources, run_pytest
from mvp_team.tools.static_checks import check_project, format_facts

ROLE = "qa"


def _allow_test_path(path: str) -> bool:
    p = path.lstrip("/")
    return p.startswith("backend/tests/") or p.startswith("tests/")


def make_nodes(llm: Any, settings: Any) -> dict[str, Any]:
    def qa_test(state: TeamState) -> dict[str, Any]:
        root = project_dir(state)
        round_no = (state.get("qa_round") or 0) + 1
        prd = state.get("prd") or {}
        arch = state.get("architecture") or {}

        # ---------- 第 1 步：编写测试 ----------
        prompt = (
            memory_block("项目简报", state.get("brief"))
            + memory_block("PRD", prd)
            + memory_block("技术方案与 API 契约", arch)
            + "\n## 当前源码（逐文件）\n"
            + collect_sources(root, budget=60_000)
            + "\n\n请输出 `backend/tests/` 下的 pytest 测试文件。"
        )
        text = llm.say(ROLE, SYSTEM_QA, prompt)
        test_files, warnings = persist_generated(state, text, ROLE, allow=_allow_test_path)

        # ---------- 第 2 步：静态体检 ----------
        checks = check_project(root, prd, arch)
        findings = checks["findings"]
        high_count = sum(1 for f in findings if f.get("severity") == "high")

        # ---------- 第 3 步：真实执行 ----------
        env_note = ""
        if settings is not None and getattr(settings, "install_deps", True) and not getattr(settings, "dry_run", False):
            from mvp_team.tools.runner import pip_install_requirements

            dep_ok, dep_out = pip_install_requirements(root / "backend")
            if not dep_ok:
                env_note = f"\n⚠️ 依赖安装存在问题（这可能是 requirements.txt 的缺陷）：\n```text\n{dep_out}\n```\n"

        pytest_ok, pytest_out = run_pytest(root / "backend")
        pytest_out = env_note + pytest_out
        if settings is not None and getattr(settings, "verify_frontend", False):
            from mvp_team.tools.runner import run_npm_build

            fe_ok, fe_out = run_npm_build(root / "frontend")
            pytest_out += f"\n\n===== npm run build =====\n{fe_out}"
            pytest_ok = pytest_ok and fe_ok

        # 兜底：如果模型完全没产出测试文件，交给确定性结论
        llm_findings = "\n".join(
            f"- [{f['severity']}] {f['where']}: {f['issue']} → {f['fix']}"
            for f in findings[:25]
        ) or "- 未发现静态缺陷"

        # ---------- 第 4 步：出报告 ----------
        report = llm.structured(
            ROLE,
            SYSTEM_QA_REPORT,
            (
                f"## 第 {round_no} 轮质量门\n\n"
                f"### pytest 执行结果\n"
                f"- 是否通过：{'是' if pytest_ok else '否'}\n"
                f"```text\n{pytest_out[-6000:] or '（无输出）'}\n```\n\n"
                f"### 确定性静态体检（共 {len(findings)} 项，其中 high {high_count} 项）\n"
                f"{llm_findings}\n\n"
                f"### 体检原始事实\n```json\n{format_facts(checks['facts'])[:6000]}\n```\n\n"
                f"### 本轮新增测试文件\n"
                + ("\n".join(f"- {f.path}" for f in test_files) or "- 无")
                + "\n\n请输出测试报告 JSON。"
            ),
            TestReport,
        )

        if report is None:
            report = _fallback_report(pytest_ok, high_count, pytest_out, findings)

        data = report.model_dump()
        # 硬约束：客观证据为失败时，不允许模型判通过
        if not pytest_ok or high_count > 0:
            data["verdict"] = "fail"
            if data.get("rework_for", "none") == "none":
                data["rework_for"] = _infer_owner(findings) or "both"
            data["findings"] = _merge_findings(data.get("findings", []), findings)
        data.setdefault("rework_for", "none")

        passed = data["verdict"] == "pass"

        path = root / "docs" / f"TEST_REPORT_round{round_no}.md"
        write_text(path, render_test_report_md(data, pytest_out))

        # 返工反馈：把缺陷清单原文回灌给工程师
        feedback_lines = [f"【第 {round_no} 轮测试报告】{data.get('summary','')}"]
        for f in data["findings"][:15]:
            feedback_lines.append(
                f"- [{f.get('severity')}] {f.get('where')}: {f.get('issue')} → 建议：{f.get('fix')}"
            )
        if not pytest_ok:
            feedback_lines.append("pytest 原始输出（截断）：\n" + pytest_out[-2500:])
        feedback = "\n".join(feedback_lines)

        update: dict[str, Any] = {
            "test_files": test_files,
            "test_report": data,
            "qa_passed": passed,
            "qa_round": round_no,
        }
        if not passed:
            update["qa_feedback"] = [feedback]

        update.update(
            ev(
                ROLE,
                f"🔍 第 {round_no} 轮质量门：{'✅ 放行' if passed else '❌ 驳回'}",
                detail=(
                    f"pytest {'通过' if pytest_ok else '未通过'}｜静态 high 缺陷 {high_count} 项｜"
                    f"返工给 {data['rework_for']}"
                ),
                status="done" if passed else "fail",
                round=round_no,
                data={
                    "verdict": data["verdict"],
                    "rework_for": data["rework_for"],
                    "high_findings": high_count,
                    "pytest_passed": pytest_ok,
                    "pytest_output": pytest_out[-4000:],
                },
            )
        )
        update["docs_files"] = [artifact_for(path, root, ROLE, state.get("project_name", ""))]
        update["artifacts"] = list(test_files) + list(update["docs_files"])
        update["run_log"] = [f"[qa] round{round_no} verdict={data['verdict']} pytest={'ok' if pytest_ok else 'ng'}"]
        if warnings:
            update["events"].append(
                Event(role=ROLE, title="⚠️ 拦截越界写入", detail="；".join(warnings[:5]), status="warn")
            )
        return update

    return {"qa_test": qa_test}


def _infer_owner(findings: list[dict[str, str]]) -> str:
    owners = set()
    for f in findings:
        where = (f.get("where") or "").lower()
        if "frontend" in where:
            owners.add("frontend")
        if "backend" in where or "api" in where:
            owners.add("backend")
    if owners == {"frontend"}:
        return "frontend"
    if owners == {"backend"}:
        return "backend"
    return "both" if owners else ""


def _merge_findings(model_findings: list[dict[str, Any]], checks: list[dict[str, str]]) -> list[dict[str, Any]]:
    # 先丢掉模型偶尔输出的空占位行（where 和 issue 都为空）
    cleaned = [
        f for f in model_findings
        if str(f.get("where", "")).strip() or str(f.get("issue", "")).strip()
    ]
    seen = {(f.get("where"), f.get("issue")) for f in cleaned}
    merged = list(cleaned)
    for f in checks:
        key = (f.get("where"), f.get("issue"))
        if key not in seen:
            merged.append(dict(f))
            seen.add(key)
    # high 排前面
    order = {"high": 0, "medium": 1, "low": 2}
    return sorted(merged, key=lambda f: order.get(str(f.get("severity", "low")), 3))


def _fallback_report(
    pytest_ok: bool, high_count: int, pytest_out: str, findings: list[dict[str, str]]
) -> TestReport:
    passed = pytest_ok and high_count == 0
    return TestReport(
        verdict="pass" if passed else "fail",
        summary=(
            "自动化测试通过且未发现高危缺陷。" if passed
            else f"自动化测试{'通过' if pytest_ok else '未通过'}，静态体检发现 {high_count} 项高危缺陷。"
        ),
        executed=["pytest 执行", "路由/调用一致性检查", "依赖与导入完整性检查"],
        findings=[dict(f) for f in findings],
        risks=[] if passed else ["存在未修复缺陷，交付质量不达标"],
        rework_for="none" if passed else (_infer_owner(findings) or "both"),
    )
