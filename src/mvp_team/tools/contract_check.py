"""契约一致性检查：纯确定性，不调用模型。

## 它解决什么问题

真实运行中，质量门两轮都驳回、返工后仍不收敛的根因是**函数级契约靠猜**：

* 测试写 ``from app.services.probe_service import probe_http``，实现里只有 ``probe_target``；
* ``conftest.py`` 只定义了 1 个 fixture，测试却用了 7 个；
* 测试往 ``LATENCY_DATABASE_PATH`` 写库，实现读的是 ``DATABASE_URL``。

这些都不是「代码写错了」，而是**两边对不上**。让模型去审查这类问题既慢又不可靠，
但它们完全可以被静态扫描出来——本模块就干这件事。

## 检查项

1. **符号级导入**：测试 ``from app.x import y`` 时，``y`` 必须在 ``app/x.py`` 里真的定义；
2. **fixture 契约**：测试函数参数里的自定义 fixture 名必须真的有定义（已扣除内置 fixture
   与 ``parametrize`` 的参数名）；
3. **环境变量契约**：测试设置的变量、实现读取的变量必须落在骨架约定的集合内，且两边要对得上；
4. **骨架导出完整性**：``config.py`` / ``database.py`` 约定的导出符号不能被破坏；
5. **前端必备文件**：构建必需文件不能被删掉。
"""

from __future__ import annotations

import ast
import json
import re
from pathlib import Path
from typing import Any

# ------------------------------------------------------------------ 契约常量

#: 骨架 ``app/config.py`` 约定的环境变量
CONTRACT_ENV_VARS: frozenset[str] = frozenset(
    {"APP_ENV", "DATABASE_URL", "API_PREFIX", "CORS_ORIGINS"}
)

#: 骨架文件必须保有的导出符号
SKELETON_EXPORTS: dict[str, frozenset[str]] = {
    "app/database.py": frozenset({"Base", "engine", "SessionLocal", "get_db", "init_db"}),
    "app/config.py": frozenset({"Settings", "get_settings", "settings"}),
}

#: 前端构建必需文件
FRONTEND_REQUIRED: tuple[str, ...] = (
    "package.json",
    "tsconfig.json",
    "vite.config.ts",
    "index.html",
    "src/main.tsx",
)

#: 前端 package.json 必须提供的 npm 脚本
FRONTEND_REQUIRED_SCRIPTS: tuple[str, ...] = ("dev", "build")

#: pytest 内置 fixture（含常用插件），不计入「自定义 fixture」检查
_BUILTIN_FIXTURES: frozenset[str] = frozenset(
    {
        "request", "tmp_path", "tmp_path_factory", "tmpdir", "tmpdir_factory",
        "monkeypatch", "capsys", "capfd", "capsysbinary", "capfdbinary",
        "caplog", "pytestconfig", "recwarn", "recorder", "doctest_namespace",
        "cache", "record_property", "record_xml_attribute", "pastebin",
        "anyio_backend", "event_loop", "benchmark",
    }
)

#: 这些环境变量由运行环境提供，不算契约违规
_SYSTEM_ENV_VARS: frozenset[str] = frozenset(
    {"PATH", "HOME", "PYTHONPATH", "PYTHONUNBUFFERED", "PYTHONDONTWRITEBYTECODE",
     "TMPDIR", "TEMP", "TMP", "LANG", "LC_ALL", "USER", "SHELL", "PWD", "VIRTUAL_ENV"}
)

_PY = "*.py"


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


def _parse(path: Path) -> ast.Module | None:
    try:
        return ast.parse(_read(path))
    except (SyntaxError, ValueError):
        return None


def _f(severity: str, where: str, issue: str, fix: str) -> dict[str, str]:
    return {"severity": severity, "where": where, "issue": issue, "fix": fix}


# ------------------------------------------------------------------ 1. 符号级导入


def module_symbols(path: Path) -> set[str]:
    """模块顶层定义的公共名字（函数/类/赋值/导入别名）。"""
    tree = _parse(path)
    if tree is None:
        return set()
    names: set[str] = set()
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names.add(node.name)
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    names.add(target.id)
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            names.add(node.target.id)
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            for alias in node.names:
                names.add(alias.asname or alias.name.split(".")[0])
    return names


def _resolve_module(backend: Path, dotted: str) -> Path | None:
    rel = Path(*dotted.split("."))
    for candidate in ((backend / rel).with_suffix(".py"), backend / rel / "__init__.py"):
        if candidate.is_file():
            return candidate
    return None


def symbol_import_findings(backend: Path) -> list[dict[str, str]]:
    """测试 ``from app.x import y`` 时，``y`` 必须真的存在。"""
    tests_dir = backend / "tests"
    if not tests_dir.is_dir():
        return []

    findings: list[dict[str, str]] = []
    cache: dict[Path, set[str]] = {}

    for path in sorted(tests_dir.rglob(_PY)):
        tree = _parse(path)
        if tree is None:
            continue
        for node in ast.walk(tree):
            if not isinstance(node, ast.ImportFrom) or not node.module:
                continue
            if not node.module.startswith("app"):
                continue
            target = _resolve_module(backend, node.module)
            if target is None:
                continue  # 模块本身缺失由 python_local_import_errors 报告，避免重复
            if target not in cache:
                cache[target] = module_symbols(target)
            available = cache[target]
            for alias in node.names:
                if alias.name == "*":
                    continue
                if alias.name not in available:
                    findings.append(
                        _f(
                            "high",
                            f"backend/tests/{path.name}",
                            f"导入了 {node.module} 中不存在的符号 `{alias.name}`",
                            f"{node.module} 实际导出：{sorted(available) or '（无）'}；"
                            "请对齐实现与测试的接口名",
                        )
                    )
    return findings


# ------------------------------------------------------------------ 2. fixture 契约


def _fixture_names(path: Path) -> set[str]:
    tree = _parse(path)
    if tree is None:
        return set()
    names: set[str] = set()
    for node in tree.body:
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for dec in node.decorator_list:
            target = dec.func if isinstance(dec, ast.Call) else dec
            dotted = ""
            if isinstance(target, ast.Attribute):
                dotted = f"{getattr(target.value, 'id', '')}.{target.attr}"
            elif isinstance(target, ast.Name):
                dotted = target.id
            if dotted in {"pytest.fixture", "fixture"}:
                names.add(node.name)
    return names


def _parametrize_params(path: Path) -> set[str]:
    """``@pytest.mark.parametrize("a,b", ...)`` 里的名字不是 fixture。"""
    tree = _parse(path)
    if tree is None:
        return set()
    out: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for dec in node.decorator_list:
            if not isinstance(dec, ast.Call):
                continue
            func = dec.func
            if not (isinstance(func, ast.Attribute) and func.attr == "parametrize"):
                continue
            if not dec.args:
                continue
            first = dec.args[0]
            if isinstance(first, ast.Constant) and isinstance(first.value, str):
                out.update(n.strip() for n in first.value.split(",") if n.strip())
            elif isinstance(first, (ast.List, ast.Tuple)):
                for elt in first.elts:
                    if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                        out.add(elt.value.strip())
    return out


def fixture_findings(backend: Path) -> list[dict[str, str]]:
    """测试函数参数里的自定义 fixture 必须有定义。"""
    tests_dir = backend / "tests"
    if not tests_dir.is_dir():
        return []

    test_paths = sorted(tests_dir.rglob("test_*.py"))
    conftests = sorted(tests_dir.rglob("conftest.py"))

    defined: set[str] = set()
    for path in conftests + test_paths:
        defined |= _fixture_names(path)

    findings: list[dict[str, str]] = []
    reported: set[tuple[str, str]] = set()

    for path in test_paths:
        tree = _parse(path)
        if tree is None:
            continue
        local = _fixture_names(path)
        params = _parametrize_params(path)
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            if not node.name.startswith("test"):
                continue
            for arg in node.args.args + node.args.kwonlyargs:
                name = arg.arg
                if name in {"self", "cls"} or name in params:
                    continue
                if name in _BUILTIN_FIXTURES or name in defined or name in local:
                    continue
                key = (path.name, name)
                if key in reported:
                    continue
                reported.add(key)
                findings.append(
                    _f(
                        "high",
                        f"backend/tests/{path.name}",
                        f"使用了未定义的 fixture `{name}`",
                        "骨架已提供 client / db_session；其余 fixture 需在测试文件或 "
                        "conftest.py 中定义，或改用已有 fixture",
                    )
                )
    return findings


# ------------------------------------------------------------------ 3. 环境变量契约

_ENV_READ_RE = re.compile(
    r"""os\.(?:environ\s*\.\s*get|environ\s*\[|getenv)\s*[\(\[]\s*["'](?P<name>[A-Z_][A-Z0-9_]*)["']"""
)
_ENV_WRITE_RE = re.compile(
    r"""os\.environ\s*\[\s*["'](?P<name>[A-Z_][A-Z0-9_]*)["']\s*\]\s*=(?!=)"""
)


def _env_names_in(paths: list[Path], pattern: re.Pattern[str]) -> dict[str, set[str]]:
    out: dict[str, set[str]] = {}
    for path in paths:
        for match in pattern.finditer(_read(path)):
            out.setdefault(match.group("name"), set()).add(path.name)
    return out


def env_contract_findings(backend: Path) -> list[dict[str, str]]:
    """测试设置的环境变量必须与实现读取的对得上。"""
    if not backend.is_dir():
        return []

    impl_paths = [
        p for p in backend.rglob(_PY)
        if "tests" not in p.relative_to(backend).parts and "__pycache__" not in p.parts
    ]
    tests_dir = backend / "tests"
    test_paths = sorted(tests_dir.rglob(_PY)) if tests_dir.is_dir() else []

    impl_reads = _env_names_in(impl_paths, _ENV_READ_RE)
    test_writes = _env_names_in(test_paths, _ENV_WRITE_RE)

    findings: list[dict[str, str]] = []
    for name, where in sorted(test_writes.items()):
        if name in _SYSTEM_ENV_VARS or name in impl_reads or name in CONTRACT_ENV_VARS:
            continue
        findings.append(
            _f(
                "high",
                f"backend/tests/{sorted(where)[0]}",
                f"测试设置了环境变量 `{name}`，但实现代码从未读取它",
                "环境变量名必须与实现一致：骨架约定数据库用 DATABASE_URL、"
                "运行环境用 APP_ENV、前缀用 API_PREFIX、跨域用 CORS_ORIGINS",
            )
        )
    return findings


# ------------------------------------------------------------------ 4/5. 骨架与前端完整性


def skeleton_integrity_findings(root: Path) -> list[dict[str, str]]:
    backend = root / "backend"
    findings: list[dict[str, str]] = []

    for rel, required in SKELETON_EXPORTS.items():
        path = backend / rel
        if not path.is_file():
            findings.append(
                _f("high", f"backend/{rel}", "骨架底座文件缺失或被删除", "必须保留该文件（由工程骨架提供）")
            )
            continue
        available = module_symbols(path)
        missing = sorted(required - available)
        if missing:
            findings.append(
                _f(
                    "high",
                    f"backend/{rel}",
                    f"骨架约定的导出符号被破坏，缺少：{missing}",
                    "请恢复这些符号，业务代码与测试都依赖它们",
                )
            )

    frontend = root / "frontend"
    if frontend.is_dir():
        for rel in FRONTEND_REQUIRED:
            if not (frontend / rel).is_file():
                findings.append(
                    _f("high", f"frontend/{rel}", "前端构建必需文件缺失", "必须保留（由工程骨架提供）")
                )
        pkg = frontend / "package.json"
        if pkg.is_file():
            try:
                scripts = json.loads(_read(pkg)).get("scripts", {})
            except json.JSONDecodeError:
                scripts = {}
            for name in FRONTEND_REQUIRED_SCRIPTS:
                if name not in scripts:
                    findings.append(
                        _f(
                            "high",
                            "frontend/package.json",
                            f"缺少必需的 npm 脚本 `{name}`",
                            f"package.json 必须提供 {list(FRONTEND_REQUIRED_SCRIPTS)}",
                        )
                    )
    return findings


# ------------------------------------------------------------------ 汇总


def check_contract(root: Path, arch: dict[str, Any] | None = None) -> dict[str, Any]:
    """跑一遍契约一致性检查。"""
    backend = root / "backend"
    findings: list[dict[str, str]] = []
    facts: dict[str, Any] = {}

    if not backend.is_dir():
        return {"findings": findings, "facts": facts}

    import_findings = symbol_import_findings(backend)
    fixture_issues = fixture_findings(backend)
    env_issues = env_contract_findings(backend)
    integrity_issues = skeleton_integrity_findings(root)

    findings.extend(import_findings)
    findings.extend(fixture_issues)
    findings.extend(env_issues)
    findings.extend(integrity_issues)

    facts["contract_symbol_errors"] = len(import_findings)
    facts["contract_fixture_errors"] = len(fixture_issues)
    facts["contract_env_errors"] = len(env_issues)
    facts["contract_skeleton_errors"] = len(integrity_issues)

    # 去重 + 排序
    order = {"high": 0, "medium": 1, "low": 2}
    unique: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for item in findings:
        key = (item["where"], item["issue"])
        if key in seen:
            continue
        seen.add(key)
        unique.append(item)
    unique.sort(key=lambda f: order.get(f["severity"], 3))

    return {"findings": unique, "facts": facts}


def render_contract_md(contract: dict[str, Any]) -> str:
    """把契约渲染成给人和模型看的文档。"""
    lines: list[str] = [
        "# 代码级契约",
        "",
        "> 本文档由工程骨架与架构方案共同确定，**后端、前端、测试三方都必须以它为准**，",
        "> 不需要再各自推断。质量门会按此逐项核验。",
        "",
        "## 1. 工程骨架已固定的接口",
        "",
        "以下模块由工程骨架提供，**禁止修改**；业务代码必须直接复用：",
        "",
        "| 模块 | 必须保有的导出 |",
        "| --- | --- |",
    ]
    for module, exports in (contract.get("skeleton_exports") or {}).items():
        lines.append(f"| `{module}` | {', '.join(f'`{e}`' for e in exports)} |")

    lines += [
        "",
        "## 2. 环境变量契约",
        "",
        "只允许使用下列环境变量；业务代码统一通过 `get_settings()` 读取：",
        "",
        "| 变量 | 用途 |",
        "| --- | --- |",
        "| `APP_ENV` | 运行环境（development / test / production） |",
        "| `DATABASE_URL` | 数据库连接串 |",
        "| `API_PREFIX` | 全局 API 前缀，默认 `/api` |",
        "| `CORS_ORIGINS` | 允许跨域来源，逗号分隔 |",
        "",
        "## 3. 测试契约",
        "",
        "`backend/tests/conftest.py` 由骨架提供，测试可直接使用：",
        "",
        "- `client`：进程内 `TestClient`，首次使用即启动应用（自动建表 + 注入种子数据）；",
        "- `db_session`：直连数据库的会话。",
        "",
        "测试文件统一放 `backend/tests/test_*.py`。**导入的符号必须真实存在，"
        "用到的 fixture 必须有定义**，否则 pytest 会在收集阶段中断。",
        "",
        "## 4. 前端契约",
        "",
        "构建必需文件（骨架提供，禁止删除）：",
        "",
    ]
    for item in contract.get("frontend_required") or []:
        lines.append(f"- `frontend/{item}`")

    lines += [
        "",
        f"package.json 必须提供脚本：{', '.join(f'`{s}`' for s in contract.get('npm_scripts') or [])}",
        "",
        "请求一律通过 `src/api/client.ts` 的 `api` 封装，路径写相对形式（不含 `/api` 前缀）。",
        "",
        "## 5. API 接口清单",
        "",
        "| 方法 | 路径 | 说明 |",
        "| --- | --- | --- |",
    ]
    for endpoint in contract.get("api_contract") or []:
        lines.append(
            f"| {endpoint.get('method', '')} | `{endpoint.get('path', '')}` | {endpoint.get('summary', '')} |"
        )

    lines.append("")
    return "\n".join(lines)


def build_contract(
    arch: dict[str, Any] | None = None, scaffold_files: list[str] | None = None
) -> dict[str, Any]:
    """汇总代码级契约（确定性构造，不调用模型）。"""
    return {
        "env_vars": sorted(CONTRACT_ENV_VARS),
        "skeleton_exports": {module: sorted(exports) for module, exports in SKELETON_EXPORTS.items()},
        "skeleton_files": sorted(scaffold_files or []),
        "frontend_required": list(FRONTEND_REQUIRED),
        "npm_scripts": list(FRONTEND_REQUIRED_SCRIPTS),
        "api_contract": list((arch or {}).get("api_contract") or []),
    }


__all__ = [
    "CONTRACT_ENV_VARS",
    "SKELETON_EXPORTS",
    "build_contract",
    "check_contract",
    "fixture_findings",
    "module_symbols",
    "env_contract_findings",
    "render_contract_md",
    "skeleton_integrity_findings",
    "symbol_import_findings",
]
