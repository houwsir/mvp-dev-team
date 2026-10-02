"""测试工程师（严过关）—— 真实执行的质量门。

流程分五步，结论全部落在**客观证据**上：

1. 让模型按契约编写 pytest 用例（只允许写 ``backend/tests/test_*.py``，骨架的
   ``conftest.py`` 受保护不可覆盖）；
2. 跑**契约一致性检查**（纯确定性）：测试导入的符号是否存在、用到的 fixture 是否有定义、
   环境变量名是否与实现一致、骨架导出是否被破坏；
3. 跑**静态体检**：前后端路由/调用/依赖/导入是否对得上；
4. 跑**真实验证**：pytest 真执行；再用独立数据库真启动服务做冒烟探测——这一步才真正
   回答「产品能不能跑起来」；
5. 把上述全部证据交给模型出报告，并据此决定是否放行。

只要 pytest 没过、冒烟没过、或存在 high 级缺陷，就退回给对应工程师返工。
"""

from __future__ import annotations

import sys
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
from mvp_team.tools.scaffold import skeleton_paths
from mvp_team.tools.smoke import run_smoke
from mvp_team.tools.static_checks import check_project, format_facts

ROLE = "qa"


def _allow_test_path(path: str) -> bool:
    """测试工程师只能写测试用例，不能覆盖骨架提供的 conftest。"""
    p = path.lstrip("/").removeprefix("./")
    if not (p.startswith("backend/tests/") or p.startswith("tests/")):
        return False
    return not p.endswith("conftest.py")


def make_nodes(llm: Any, settings: Any) -> dict[str, Any]:
    def qa_test(state: TeamState) -> dict[str, Any]:
        root = project_dir(state)
        round_no = (state.get("qa_round") or 0) + 1
        prd = state.get("prd") or {}
        arch = state.get("architecture") or {}

        dry_run = bool(getattr(settings, "dry_run", False))

        # ---------- 第 1 步：编写测试 ----------
        prompt = (
            memory_block("项目简报", state.get("brief"))
            + memory_block("PRD", prd)
            + memory_block("技术方案与 API 契约", arch)
            + memory_block("代码级契约（必须遵守）", state.get("contract"))
            + "\n## 当前源码（逐文件）\n"
            + collect_sources(root, budget=60_000)
            + "\n\n请输出 `backend/tests/` 下的 pytest 测试文件（文件名形如 `test_<资源>.py`）。"
            "注意：`tests/conftest.py` 由工程骨架提供且受保护，你不需要也不允许重写它。"
        )
        text = llm.say(ROLE, SYSTEM_QA, prompt)
        test_files, warnings = persist_generated(
            state, text, ROLE, allow=_allow_test_path, forbid=skeleton_paths()
        )

        # ---------- 第 2/3 步：契约一致性 + 静态体检（check_project 已内含契约检查）----------
        checks = check_project(root, prd, arch)
        findings = checks["findings"]
        high_count = sum(1 for f in findings if f.get("severity") == "high")
        contract_facts = (checks.get("facts") or {}).get("contract") or {}

        # ---------- 第 4 步：真实验证 ----------
        env_note = ""
        if settings is not None and getattr(settings, "install_deps", True) and not dry_run:
            from mvp_team.tools.runner import pip_install_requirements

            dep_ok, dep_out = pip_install_requirements(root / "backend")
            if not dep_ok:
                env_note = f"\n⚠️ 依赖安装存在问题（这可能是 requirements.txt 的缺陷）：\n```text\n{dep_out}\n```\n"

        pytest_ok, pytest_out = run_pytest(root / "backend")
        pytest_out = env_note + pytest_out

        if settings is not None and getattr(settings, "verify_frontend", False) and not dry_run:
            from mvp_team.tools.runner import run_npm_build

            fe_ok, fe_out = run_npm_build(root / "frontend")
            pytest_out += f"\n\n===== npm run build =====\n{fe_out}"
            pytest_ok = pytest_ok and fe_ok

        # ---- 冒烟门：真启动服务打接口（dry-run 下没有真实后端，跳过）----
        smoke: dict[str, Any] = {"ok": True, "report": "", "facts": {"skipped": True}, "findings": []}
        if not dry_run and getattr(settings, "run_smoke", True):
            smoke = run_smoke(
                root,
                arch.get("api_contract") or [],
                python=sys.executable,
                startup_timeout=float(getattr(settings, "smoke_timeout", 60)),
            )
            for f in smoke.get("findings", []):
                if f.get("severity") == "high":
                    high_count += 1

        smoke_ok = bool(smoke.get("ok"))

        # ---------- 第 5 步：出报告 ----------
        llm_findings = "\n".join(
            f"- [{f['severity']}] {f['where']}: {f['issue']} → {f['fix']}"
            for f in findings[:25]
        ) or "- 未发现静态缺陷"

        report = llm.structured(
            ROLE,
            SYSTEM_QA_REPORT,
            (
                f"## 第 {round_no} 轮质量门\n\n"
                f"### 冒烟测试（真启动服务打接口）\n"
                f"- 是否通过：{'是' if smoke_ok else '否'}\n"
                f"{smoke.get('report') or '（未执行：离线演练模式）'}\n\n"
                f"### pytest 执行结果\n"
                f"- 是否通过：{'是' if pytest_ok else '否'}\n"
                f"```text\n{pytest_out[-6000:] or '（无输出）'}\n```\n\n"
                f"### 契约一致性检查\n"
                f"```json\n{format_facts(contract_facts)[:2000]}\n```\n\n"
                f"### 确定性静态体检（共 {len(findings)} 项，其中 high {high_count} 项）\n"
                f"{llm_findings}\n\n"
                f"### 体检原始事实\n```json\n{format_facts(checks['facts'])[:5000]}\n```\n\n"
                f"### 本轮新增测试文件\n"
                + ("\n".join(f"- {f.path}" for f in test_files) or "- 无")
                + "\n\n请输出测试报告 JSON。"
            ),
            TestReport,
        )

        if report is None:
            report = _fallback_report(pytest_ok, smoke_ok, high_count, pytest_out, findings)

        data = report.model_dump()
        # 硬约束：客观证据为失败时，不允许模型判通过
        if not pytest_ok or not smoke_ok or high_count > 0:
            data["verdict"] = "fail"
            if data.get("rework_for", "none") == "none":
                data["rework_for"] = _infer_owner(findings) or "both"
            data["findings"] = _merge_findings(data.get("findings", []), findings)
        data.setdefault("rework_for", "none")

        passed = data["verdict"] == "pass"

        path = root / "docs" / f"TEST_REPORT_round{round_no}.md"
        write_text(path, render_test_report_md(data, pytest_out, smoke.get("report", "")))

        # 返工反馈：把缺陷清单 + 冒烟结论原文回灌给工程师
        feedback_lines = [f"【第 {round_no} 轮测试报告】{data.get('summary','')}"]
        if not smoke_ok and smoke.get("report"):
            feedback_lines.append("冒烟测试未通过：\n" + smoke["report"][-2000:])
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
            "smoke_report": smoke,
        }
        if not passed:
            update["qa_feedback"] = [feedback]

        detail = (
            f"冒烟 {'通过' if smoke_ok else '未通过'}｜pytest {'通过' if pytest_ok else '未通过'}｜"
            f"契约/静态 high {high_count} 项｜返工给 {data['rework_for']}"
        )
        if not test_files:
            # 测试工程师一份测试都没产出，是个独立且可操作的信号：
            # 它不是「测试失败」，而是「根本没测」。必须显式喊出来，
            # 否则容易被 pytest 的失败输出掩盖过去。
            detail += "｜⚠️ 本轮未产出任何测试文件"
        update.update(
            ev(
                ROLE,
                f"🔍 第 {round_no} 轮质量门：{'✅ 放行' if passed else '❌ 驳回'}",
                detail=detail,
                status="done" if passed else "fail",
                round=round_no,
                data={
                    "verdict": data["verdict"],
                    "rework_for": data["rework_for"],
                    "high_findings": high_count,
                    "pytest_passed": pytest_ok,
                    "smoke_passed": smoke_ok,
                    "pytest_output": pytest_out[-4000:],
                    "smoke_report": smoke.get("report", "")[-3000:],
                },
            )
        )
        update["docs_files"] = [artifact_for(path, root, ROLE, state.get("project_name", ""))]
        update["artifacts"] = list(test_files) + list(update["docs_files"])
        update["run_log"] = [
            f"[qa] round{round_no} verdict={data['verdict']} "
            f"pytest={'ok' if pytest_ok else 'ng'} smoke={'ok' if smoke_ok else 'ng'}"
        ]
        if warnings:
            update["events"].append(
                Event(role=ROLE, title="⚠️ 拦截越界写入", detail="；".join(warnings[:5]), status="warn")
            )
        if not test_files:
            update["events"].append(
                Event(
                    role=ROLE,
                    title="⚠️ 本轮未产出任何测试文件",
                    detail=(
                        "测试工程师的落盘协议没有解析出任何 ```file: 块。"
                        "常见原因：模型只回了说明文字、输出被截断，或写到了 backend/tests/ 之外。"
                        "pytest 因此「无测试可跑」，不等于代码通过。"
                    ),
                    status="warn",
                )
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
        if "tests" in where:
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
    pytest_ok: bool,
    smoke_ok: bool,
    high_count: int,
    pytest_out: str,
    findings: list[dict[str, str]],
) -> TestReport:
    passed = pytest_ok and smoke_ok and high_count == 0
    reasons = []
    if not smoke_ok:
        reasons.append("冒烟测试未通过（服务无法启动或有接口异常）")
    if not pytest_ok:
        reasons.append("自动化测试未通过")
    if high_count:
        reasons.append(f"存在 {high_count} 项高危缺陷")
    return TestReport(
        verdict="pass" if passed else "fail",
        summary="冒烟、自动化测试与静态检查全部通过。" if passed else "；".join(reasons) + "。",
        executed=["服务启动与接口冒烟", "契约一致性检查", "pytest 执行", "路由/调用一致性检查", "依赖与导入完整性检查"],
        findings=[dict(f) for f in findings],
        risks=[] if passed else ["存在未修复缺陷，交付质量不达标"],
        rework_for="none" if passed else (_infer_owner(findings) or "both"),
    )
