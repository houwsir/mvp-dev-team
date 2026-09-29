"""交付自检：核对「文档与脚本里承诺的文件，磁盘上是否真的存在」。

为什么需要它：质量门跑在运维工程师**之前**，所以它能验证代码，却验证不了
「Makefile 里 `bash deploy/start.sh` 指向的脚本到底存不存在」这类问题。
这类不一致非常典型——README 写了三条启动命令，其中两条指向不存在的文件。

检查项：
1. Makefile 里引用的仓库内路径是否都存在；
2. Makefile 调用的 `npm run <script>` 是否真的在 package.json 里定义；
3. docker-compose.yml 里的 dockerfile / context / 挂载路径是否存在；
4. README 里以反引号标注的仓库内文件路径是否存在；
5. 必备交付物是否齐全。
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

# 只检查这些前缀下的路径，避免把 README 里的示例路径全当成承诺
_REPO_PREFIXES = ("backend/", "frontend/", "deploy/", "docs/", "scripts/")

_REQUIRED_FILES = ("README.md", "Makefile", "backend/requirements.txt", "frontend/package.json")

# Makefile / shell 里出现的形如 deploy/start.sh、backend/app 的路径
_PATH_TOKEN_RE = re.compile(r"(?<![\w./-])((?:backend|frontend|deploy|docs|scripts)/[A-Za-z0-9_./-]+)")
_NPM_RUN_RE = re.compile(r"npm\s+(?:run\s+)?(?P<script>[A-Za-z0-9:_-]+)")
_COMPOSE_DOCKERFILE_RE = re.compile(r"dockerfile\s*:\s*(?P<p>[^\s#]+)")
_COMPOSE_CONTEXT_RE = re.compile(r"context\s*:\s*(?P<p>[^\s#]+)")
_README_BACKTICK_RE = re.compile(r"`([^`\n]+)`")


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


def _norm_candidate(token: str) -> str | None:
    token = token.strip().strip("`'\"()[]{};,")
    token = token.split("#")[0].strip()
    token = token.rstrip(".,;:")
    if not token or token.startswith(("http://", "https://", "git@", "-")):
        return None
    token = token.lstrip("./")
    if not token.startswith(_REPO_PREFIXES):
        return None
    # 去掉命令里的尾随参数，例如 `deploy/start.sh` 后面的东西
    token = token.split(" ")[0]
    return token or None


def _makefile_findings(root: Path, findings: list[dict[str, str]]) -> None:
    makefile = root / "Makefile"
    if not makefile.is_file():
        return
    text = _read(makefile)

    # 1) 引用的仓库内路径
    seen: set[str] = set()
    for match in _PATH_TOKEN_RE.finditer(text):
        candidate = _norm_candidate(match.group(1))
        if not candidate or candidate in seen:
            continue
        seen.add(candidate)
        if not (root / candidate).exists():
            findings.append(
                _f("high", "Makefile", f"引用了不存在的路径：{candidate}", "补齐该文件，或修正 Makefile 中的路径")
            )

    # 2) npm run <script> / npm test 是否真的存在
    pkg_path = root / "frontend" / "package.json"
    if pkg_path.is_file():
        try:
            scripts = set(json.loads(_read(pkg_path)).get("scripts", {}))
        except json.JSONDecodeError:
            scripts = set()
        for match in _NPM_RUN_RE.finditer(text):
            script = match.group("script")
            if script in {"install", "ci", "run"}:
                continue
            # `npm test` 等价于 `npm run test`
            if script not in scripts:
                findings.append(
                    _f(
                        "high",
                        "Makefile",
                        f"调用了前端不存在的 npm 脚本：{script}（package.json 里只有 {sorted(scripts)}）",
                        "在 package.json 里补上该脚本，或从 Makefile 移除该命令",
                    )
                )


def _compose_findings(root: Path, findings: list[dict[str, str]]) -> None:
    compose = root / "deploy" / "docker-compose.yml"
    if not compose.is_file():
        return
    text = _read(compose)
    for regex, label in ((_COMPOSE_DOCKERFILE_RE, "dockerfile"), (_COMPOSE_CONTEXT_RE, "context")):
        for match in regex.finditer(text):
            raw = match.group("p").strip().strip("'\"")
            if raw.startswith(("$", "http", "image:")):
                continue
            candidate = raw.lstrip("./")
            target = (root / "deploy" / candidate) if not candidate.startswith(("backend", "frontend", "deploy")) else (root / candidate)
            if not target.exists() and not (root / candidate).exists():
                findings.append(
                    _f("high", "deploy/docker-compose.yml", f"{label} 指向不存在的路径：{raw}", "补齐该文件或修正路径")
                )


def _readme_findings(root: Path, findings: list[dict[str, str]]) -> None:
    readme = root / "README.md"
    if not readme.is_file():
        return
    seen: set[str] = set()
    for match in _README_BACKTICK_RE.finditer(_read(readme)):
        candidate = _norm_candidate(match.group(1))
        if not candidate or candidate in seen:
            continue
        seen.add(candidate)
        if candidate.endswith("/"):
            continue
        if not (root / candidate).exists():
            findings.append(
                _f("medium", "README.md", f"文档里提到但不存在的文件：{candidate}", "补齐文件，或修正文档描述")
            )


def check_delivery(root: Path) -> dict[str, Any]:
    """对交付物做一轮一致性体检。"""
    findings: list[dict[str, str]] = []

    for rel in _REQUIRED_FILES:
        if not (root / rel).exists():
            findings.append(_f("high", "交付物", f"缺少必备文件：{rel}", "让运维工程师补齐"))

    _makefile_findings(root, findings)
    _compose_findings(root, findings)
    _readme_findings(root, findings)

    # 去重
    unique: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    order = {"high": 0, "medium": 1, "low": 2}
    for f in findings:
        key = (f["where"], f["issue"])
        if key not in seen:
            seen.add(key)
            unique.append(f)
    unique.sort(key=lambda f: order.get(f["severity"], 3))

    return {"findings": unique, "files_checked": len(_REQUIRED_FILES)}


def _f(severity: str, where: str, issue: str, fix: str) -> dict[str, str]:
    return {"severity": severity, "where": where, "issue": issue, "fix": fix}


def render_delivery_report(result: dict[str, Any]) -> str:
    findings = result["findings"]
    lines = [
        "# 交付自检报告",
        "",
        f"- 结论：{'✅ 通过' if not findings else f'⚠️ 发现 {len(findings)} 处不一致'}",
        f"- 说明：核对 Makefile / docker-compose / README 中承诺的文件与命令是否真实存在。",
        "",
    ]
    if findings:
        lines += ["| 严重度 | 位置 | 问题 | 建议 |", "| --- | --- | --- | --- |"]
        for f in findings:
            lines.append(f"| {f['severity']} | `{f['where']}` | {f['issue']} | {f['fix']} |")
    else:
        lines.append("未发现不一致：文档与脚本引用的路径、npm 脚本均已就位。")
    lines.append("")
    return "\n".join(lines)
