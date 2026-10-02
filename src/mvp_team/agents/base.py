"""节点公共设施：渲染文档、落盘产物、构造事件。"""

from __future__ import annotations

import json
import os
import re
from dataclasses import asdict
from pathlib import Path
from typing import Any

from mvp_team.prompts import PERSONAS, memory_block
from mvp_team.state import Event, FileArtifact, TeamState
from mvp_team.tools.codeblocks import materialize, parse_file_blocks


def output_root(state: TeamState) -> Path:
    return Path(state["output_dir"]).expanduser().resolve()


def project_dir(state: TeamState) -> Path:
    """本次产物的目录：``<output_dir>/<project_name>``。"""
    name = state.get("project_name") or "mvp-project"
    return output_root(state) / name


def write_text(path: Path, content: str) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return content


def artifact_for(path: Path, root: Path, role: str, project: str = "") -> FileArtifact:
    rel = str(path.relative_to(root)) if str(path).startswith(str(root)) else str(path)
    text = path.read_text(encoding="utf-8", errors="ignore") if path.is_file() else ""
    return FileArtifact(
        path=rel,
        role=role,
        project=project,
        bytes=len(text.encode("utf-8")),
        lines=text.count("\n"),
    )


def _norm_rel(path: str) -> str:
    """把模型写出的路径归一成相对项目根的 POSIX 形式，便于与骨架清单比对。"""
    return path.strip().lstrip("/").removeprefix("./")


def persist_generated(
    state: TeamState,
    text: str,
    role: str,
    allow=None,
    forbid=None,
) -> tuple[list[FileArtifact], list[str]]:
    """把模型输出里的 ```file: 代码块写入项目目录。

    * ``allow``：可选过滤器 ``(path) -> bool``，用来限制某个角色只能写自己该写的目录
      （例如测试工程师只允许写 ``backend/tests/``）；
    * ``forbid``：可选集合，列出**禁止覆盖**的路径（工程骨架文件）。

    被拦截的写入不会落盘，而是作为告警返回，最终会出现在事件流里，便于审计。
    """
    root = project_dir(state)
    root.mkdir(parents=True, exist_ok=True)
    parsed = parse_file_blocks(text, role=role)
    warnings: list[str] = []
    blocked = {_norm_rel(p) for p in (forbid or ())}

    kept = []
    for item in parsed:
        rel = _norm_rel(item.path)
        if allow is not None and not allow(item.path):
            warnings.append(f"越界写入被拦截：{item.path}")
            continue
        if rel in blocked:
            warnings.append(f"骨架文件受保护，已拦截覆盖：{item.path}")
            continue
        kept.append(item)
    parsed = kept

    files, more_warnings = materialize(parsed, root, role=role, project=state.get("project_name", ""))
    return files, warnings + more_warnings


def scan_tree(root: Path, limit: int = 200) -> list[str]:
    """列出项目目录下的文件（相对路径），供下游角色核对交付清单。"""
    if not root.exists():
        return []
    out: list[str] = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in {"__pycache__", ".git", "node_modules", ".pytest_cache", "dist"}]
        for name in sorted(filenames):
            rel = Path(dirpath, name).relative_to(root)
            out.append(str(rel))
            if len(out) >= limit:
                return out
    return out


def ev(role: str, title: str, **kwargs: Any) -> dict[str, Any]:
    return {"events": [Event(role=role, title=title, **kwargs)]}


def role_label(role: str) -> str:
    p = PERSONAS[role]
    return f"{p['emoji']} {p['title']}·{p['name']}"


_REWORK_FILE_RE = re.compile(
    r"((?:backend|frontend)/[A-Za-z0-9_./\-]+\.(?:py|ts|tsx|js|jsx|json|css|html|sh|yml|yaml|toml|md))"
)


def _rework_file_contents(body: str, root: Path, limit: int = 6, budget: int = 40_000) -> tuple[str, list[str]]:
    """从缺陷清单里解析出被点名的文件，附上它们的当前内容。

    这是返工能否收敛的关键：只给「文件清单」工程师看不到自己上一轮写了什么，
    只能凭记忆重写，很容易改坏别处；给「当前内容」才能做定点修复。
    """
    picked: list[str] = []
    for match in _REWORK_FILE_RE.finditer(body):
        rel = match.group(1).removeprefix("./")
        if rel not in picked and (root / rel).is_file():
            picked.append(rel)
    if not picked:
        return "", []

    chunks: list[str] = []
    used = 0
    attached: list[str] = []
    for rel in picked[:limit]:
        text = (root / rel).read_text(encoding="utf-8", errors="ignore")
        if len(text) > 12_000:
            text = text[:12_000] + "\n# ... [内容过长已截断]"
        block = f"\n===== FILE: {rel} =====\n{text}\n"
        if used + len(block) > budget:
            break
        chunks.append(block)
        attached.append(rel)
        used += len(block)
    return "".join(chunks), attached


def rework_block(state: TeamState, role: str) -> str:
    """返工轮次里，把缺陷清单**连同被点名文件的当前内容**一起回灌给工程师。"""
    feedback = state.get("qa_feedback") or []
    if not feedback or (state.get("qa_round") or 0) == 0:
        return ""
    relevant = [f for f in feedback if role in f.lower() or "both" in f.lower()]
    body = "\n\n".join(relevant[-2:] if relevant else feedback[-2:])

    root = project_dir(state)
    contents, attached = _rework_file_contents(body, root)
    listing = "\n".join(f"- {p}" for p in scan_tree(root, limit=80)) or "- （尚无文件）"

    parts = [
        "\n## ⚠️ 返工要求（本轮必须修复以下问题）\n",
        body,
        "\n",
    ]
    if contents:
        parts += [
            "\n## 📄 被点名文件的当前内容（磁盘上的真实版本）\n",
            "请在下面这些内容的基础上**做定点修改**，不要凭空重写：\n",
            contents,
            "\n",
        ]
    else:
        parts += [
            "\n## 📄 未能定位到具体文件\n",
            "请先根据上面的缺陷描述与文件清单，自行定位相关文件后再修改。\n",
        ]
    parts += [
        "\n## 当前磁盘上已有的文件\n",
        listing,
        "\n\n",
        "请只输出被修复的**完整文件**（覆盖旧版本），其余文件不要重复输出。\n",
        "注意：工程骨架文件（`app/config.py`、`app/database.py`、`tests/conftest.py`、"
        "`package.json`、`tsconfig.json`、`vite.config.ts`、`deploy/` 下的文件等）"
        "**不可修改**，写入会被拦截。\n",
    ]
    return "".join(parts)


# ---------------------------------------------------------------------------------------
# 文档渲染（不走模型，降低 token 成本并保证格式稳定）
# ---------------------------------------------------------------------------------------


def render_prd_md(prd: dict[str, Any], brief: dict[str, Any]) -> str:
    lines: list[str] = ["# 产品需求文档（PRD）", ""]
    lines += [f"> 产品定位：{brief.get('one_liner', '-')}", ""]
    lines += ["## 1. 概述", "", str(prd.get("overview", "")), ""]

    lines += ["## 2. 用户故事", "", "| 编号 | 角色 | 诉求 | 价值 | 优先级 |", "| --- | --- | --- | --- | --- |"]
    for s in prd.get("user_stories", []):
        lines.append(
            f"| {s.get('id','')} | {s.get('as_a','')} | {s.get('i_want','')} | {s.get('so_that','')} | {s.get('priority','')} |"
        )
    lines.append("")

    lines += ["## 3. 功能清单", "", "| 编号 | 功能 | 说明 | 使用角色 | 优先级 |", "| --- | --- | --- | --- | --- |"]
    for f in prd.get("features", []):
        lines.append(
            f"| {f.get('id','')} | {f.get('name','')} | {f.get('description','')} | {f.get('role','')} | {f.get('priority','')} |"
        )
    lines.append("")

    lines += ["## 4. 页面清单", "", "| 页面 | 路由 | 目的 | 关键元素 |", "| --- | --- | --- | --- |"]
    for p in prd.get("pages", []):
        lines.append(
            f"| {p.get('name','')} | `{p.get('route','')}` | {p.get('purpose','')} | {'、'.join(p.get('key_elements', []))} |"
        )
    lines.append("")

    lines += ["## 5. 数据实体", ""]
    for e in prd.get("entities", []):
        lines += [f"### {e.get('name','')}", "", f"{e.get('description','')}", "", "| 字段 | 类型 | 必填 | 说明 |", "| --- | --- | --- | --- |"]
        for f in e.get("fields", []):
            lines.append(
                f"| `{f.get('name','')}` | {f.get('type','')} | {'是' if f.get('required') else '否'} | {f.get('description','')} |"
            )
        lines.append("")

    if prd.get("out_of_scope"):
        lines += ["## 6. 本期不做", ""]
        lines += [f"- {x}" for x in prd["out_of_scope"]]
        lines.append("")
    return "\n".join(lines)


def render_architecture_md(arch: dict[str, Any]) -> str:
    lines = ["# 技术方案与 API 契约", "", "## 1. 方案概述", "", str(arch.get("overview", "")), ""]
    if arch.get("stack"):
        lines += ["## 2. 技术选型", "", "| 层次 | 选型 |", "| --- | --- |"]
        lines += [f"| {k} | {v} |" for k, v in arch["stack"].items()]
        lines.append("")
    if arch.get("data_models"):
        lines += ["## 3. 数据模型", ""]
        for m in arch["data_models"]:
            lines += [f"### {m.get('name','')} → 表 `{m.get('table','')}`", ""]
            lines += [f"- `{c}`" for c in m.get("columns", [])]
            lines.append("")
    if arch.get("api_contract"):
        lines += ["## 4. API 契约", "", "| 方法 | 路径 | 说明 |", "| --- | --- | --- |"]
        for a in arch["api_contract"]:
            lines.append(f"| {a.get('method','')} | `{a.get('path','')}` | {a.get('summary','')} |")
        lines.append("")
        for a in arch["api_contract"]:
            lines += [f"### `{a.get('method','')} {a.get('path','')}`", "", str(a.get("summary", "")), ""]
            if a.get("request"):
                lines += ["请求：", "", "```json", str(a["request"]), "```", ""]
            if a.get("response"):
                lines += ["响应：", "", "```json", str(a["response"]), "```", ""]
    if arch.get("directory_layout"):
        lines += ["## 5. 目录与交付清单", ""]
        lines += [f"- `{p}`" for p in arch["directory_layout"]]
        lines.append("")
    if arch.get("risks"):
        lines += ["## 6. 风险", ""]
        lines += [f"- {r}" for r in arch["risks"]]
        lines.append("")
    return "\n".join(lines)


def render_design_md(spec: dict[str, Any]) -> str:
    lines = ["# UI/UX 设计规范", ""]
    if spec.get("style_keywords"):
        lines += ["## 风格关键词", "", " ".join(f"`{k}`" for k in spec["style_keywords"]), ""]
    for section, title in (("color_tokens", "色彩令牌"), ("typography", "字体令牌")):
        if spec.get(section):
            lines += [f"## {title}", "", "| 名称 | 值 | 用途 |", "| --- | --- | --- |"]
            lines += [f"| `{t.get('name','')}` | `{t.get('value','')}` | {t.get('usage','')} |" for t in spec[section]]
            lines.append("")
    if spec.get("layouts"):
        lines += ["## 页面布局", ""]
        for lay in spec["layouts"]:
            lines += [f"### {lay.get('page','')} (`{lay.get('route','')}`)", ""]
            lines += [f"- 布局：{lay.get('layout','')}"]
            lines += [f"- 组件：{'、'.join(lay.get('components', []))}"]
            lines += [f"- 状态：{'、'.join(lay.get('states', []))}"]
            lines.append("")
    if spec.get("interaction_notes"):
        lines += ["## 交互说明", ""]
        lines += [f"- {n}" for n in spec["interaction_notes"]]
        lines.append("")
    return "\n".join(lines)


def render_test_report_md(report: dict[str, Any], pytest_output: str = "", smoke_report: str = "") -> str:
    verdict = report.get("verdict", "unknown")
    lines = [
        "# 测试报告",
        "",
        f"- 结论：**{'✅ 通过' if verdict == 'pass' else '❌ 未通过'}**",
        f"- 概述：{report.get('summary', '')}",
        "",
        "## 已执行的校验",
        "",
    ]
    lines += [f"- [x] {x}" for x in report.get("executed", [])] or ["- （无）"]
    if smoke_report:
        lines += ["", "## 冒烟测试（真启动服务打接口）", "", smoke_report.strip(), ""]
    lines += ["", "## 缺陷清单", "", "| 严重度 | 位置 | 问题 | 建议修复 |", "| --- | --- | --- | --- |"]
    findings = report.get("findings", [])
    if findings:
        for f in findings:
            lines.append(
                f"| {f.get('severity','')} | `{f.get('where','')}` | {f.get('issue','')} | {f.get('fix','')} |"
            )
    else:
        lines.append("| - | - | 未发现缺陷 | - |")
    lines.append("")
    if report.get("risks"):
        lines += ["## 风险", ""] + [f"- {r}" for r in report["risks"]] + [""]
    lines += ["## 需要返工", "", f"`{report.get('rework_for', 'none')}`", ""]
    if pytest_output:
        lines += ["## 自动化测试原始输出", "", "```text", pytest_output.strip()[:8000], "```", ""]
    return "\n".join(lines)


def to_plain(value: Any) -> Any:
    if isinstance(value, FileArtifact):
        return asdict(value)
    return value


__all__ = [
    "output_root",
    "project_dir",
    "persist_generated",
    "scan_tree",
    "ev",
    "role_label",
    "rework_block",
    "write_text",
    "artifact_for",
    "render_prd_md",
    "render_architecture_md",
    "render_design_md",
    "render_test_report_md",
    "memory_block",
    "PERSONAS",
]
