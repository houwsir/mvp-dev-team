"""确定性静态检查：不依赖模型，直接读磁盘上的源码找断裂点。

这些检查补上了 LLM 审查最容易漏的地方——前后端接口是否真的对得上、
文件是否真的存在、依赖是否真的齐。检查结果会作为「客观证据」喂给测试工程师，
避免它凭想象写一份漂亮但虚假的测试报告。
"""

from __future__ import annotations

import ast
import json
import re
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------- 路由 / 调用提取

_BACKEND_ROUTE_RE = re.compile(
    r"@(?P<owner>\w+)\.(?P<method>get|post|put|patch|delete)\(\s*[\"'`](?P<path>[^\"'`]*)[\"'`]",
    re.IGNORECASE | re.DOTALL,
)
# 对象式路由表：{ path: '/products', element: <Products/> }
_FRONTEND_ROUTE_OBJ_RE = re.compile(
    r"""\bpath\s*:\s*["'`](?P<path>/[^"'`]*)["'`]"""
)
_FRONTEND_JSX_ROUTE_RE = re.compile(r"<Route\s+[^>]*?path\s*=\s*[\"'{](?P<path>[^\"'}]+)[\"'}]")

# 请求调用：捕获 fetch/request/xxxRequest(...) 的第一个字符串实参
_FRONTEND_CALL_RE = re.compile(
    r"""(?:fetch|request|apiRequest|httpRequest|axios\.\w+)\s*(?:<[^<>()]*>)?\(\s*[`"'](?P<path>[^`"']+)[`"']"""
)
_PLACEHOLDER_RE = re.compile(r"\$\{[^}]*\}|\{[^}/]*\}")

# 这些文件由「运维工程师」在质量门之后产出，质量门阶段不应据此判缺陷
_DEPLOY_STAGE_PATTERNS = (
    "dockerfile",
    "docker-compose",
    "nginx.conf",
    ".env.example",
    "makefile",
    "readme.md",
    "deploy/",
    ".github/",
    "start.sh",
)


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


def _source_files(backend: Path) -> list[Path]:
    """backend 下参与路由扫描的 Python 源文件（排除测试与缓存目录）。

    注意：只按**相对 backend 的路径**判断，不能用绝对路径里的 "test" 关键字，
    否则临时目录（如 pytest 的 tmp_path）会把整个项目误过滤掉。
    """
    out: list[Path] = []
    for path in backend.rglob("*.py"):
        rel = path.relative_to(backend)
        if any(part in {"tests", "test", "__pycache__"} for part in rel.parts):
            continue
        out.append(path)
    return out


def backend_routes(backend: Path) -> set[str]:
    """从 FastAPI 源码中还原出路由集合（含 APIRouter prefix 与挂载 prefix）。

    实现要点：**按文件隔离路由变量**。实际项目里每个模块的路由变量常常都叫
    ``router``，若共用一张表就会互相覆盖归属前缀——这里按文件分别解析，
    再用 ``include_router(products.router, prefix="/api")`` 里的模块名回连挂载前缀。
    """
    files = _source_files(backend)
    texts = {p: _read(p) for p in files}

    # 1) 每个文件里：APIRouter 变量 → 局部 prefix
    local_prefix: dict[Path, dict[str, str]] = {}
    for path, text in texts.items():
        table: dict[str, str] = {}
        for m in re.finditer(
            r"^(?P<var>\w+)\s*=\s*APIRouter\((?P<args>.*?)\)\s*$",
            text,
            re.MULTILINE | re.DOTALL,
        ):
            pref = re.search(r"prefix\s*=\s*[\"'](?P<p>[^\"']*)[\"']", m.group("args"))
            table[m.group("var")] = pref.group("p") if pref else ""
        if table:
            local_prefix[path] = table

    # 2) include_router(<module>.<var>, prefix=...) → 模块名 → 挂载前缀
    mount_by_module: dict[str, str] = {}
    mount_by_var: dict[str, str] = {}
    for text in texts.values():
        for m in re.finditer(
            r"include_router\(\s*(?P<ref>[\w.]+)[^)]*?prefix\s*=\s*[\"'](?P<prefix>[^\"']*)[\"']",
            text,
            re.DOTALL,
        ):
            ref = m.group("ref")
            prefix = m.group("prefix")
            module = ref.split(".")[0]
            var = ref.split(".")[-1]
            mount_by_module[module] = prefix
            mount_by_var.setdefault(var, prefix)

    all_mounts = sorted(set(mount_by_module.values()) | set(mount_by_var.values()))

    # 3) 逐文件产出路由，并生成「带前缀 / 不带前缀」两种变体
    routes: set[str] = set()
    for path, text in texts.items():
        table = local_prefix.get(path, {})
        file_mounts = [mount_by_module.get(path.stem, "")]
        if not file_mounts[0]:
            file_mounts = [""] + all_mounts
        for m in _BACKEND_ROUTE_RE.finditer(text):
            owner, method, sub = m.group("owner"), m.group("method").upper(), m.group("path")
            local = table.get(owner, "")
            for mount in file_mounts:
                routes.add(f"{method} {_join(_join(mount, local), sub)}")
                routes.add(f"{method} {_join(local, sub)}")
    return routes


def _join(prefix: str, path: str) -> str:
    full = prefix.rstrip("/") + "/" + path.lstrip("/")
    return full.rstrip("/") or "/"


def _norm(path: str) -> str:
    """把路径归一化，便于比较。

    * 丢掉查询串与 hash：``/orders?page=1`` → ``/orders``；
    * 路径参数统一成 ``<>``：``/orders/{id}``、``/orders/123``、``/orders/${id}`` → ``/orders/<>``；
    * 注意 ``/orders${qs}`` 这种「模板串拼在末尾」不是路径参数，应当整段丢掉。
    """
    p = path.strip().split("?")[0].split("#")[0]
    # 只在 `${...}` / `{...}` / `:param` 紧跟 `/` 时视为路径参数（用哨兵避免被下一步误删）
    p = re.sub(r"/(\$\{[^}]*\}|\{[^}/]*\}|:[A-Za-z_]\w*|\*)", "/\x00", p)
    # 其余残留占位符直接删掉（多为查询串拼接）
    p = re.sub(r"\$\{[^}]*\}|\{[^}/]*\}|<[^/]*>", "", p)
    # 模板串里嵌套了大括号/括号时，末尾常残留 ) } , 之类的碎片
    p = re.sub(r"[\s)\]}>'\"`,;:]+$", "", p)
    # 未闭合的 `${...` 尾巴（嵌套模板串被截断）也一并丢掉
    p = re.sub(r"\$\{[^}]*$", "", p)
    p = p.replace("\x00", "<>").rstrip("/")
    return p or "/"


def _split_routes(value: str) -> list[str]:
    """PRD 的 route 字段偶尔会写多条路由，例如 ``/products/new 和 /products/:id/edit``。"""
    parts = re.split(r"\s*(?:和|或|以及|、|,|，|;|；|\|)\s*", str(value))
    out: list[str] = []
    for part in parts:
        token = _norm(part)
        if token.startswith("/") and token != "/":
            out.append(token)
    return out


def frontend_routes(frontend: Path) -> set[str]:
    """提取前端路由，同时支持 JSX 声明式与对象式路由表。"""
    routes: set[str] = set()
    for path in list(frontend.rglob("*.tsx")) + list(frontend.rglob("*.ts")):
        if "node_modules" in path.parts:
            continue
        text = _read(path)
        for m in _FRONTEND_JSX_ROUTE_RE.finditer(text):
            routes.add(m.group("path"))
        # 只在看起来像路由配置文件里用对象式匹配，避免把别的 path: 字段当路由
        if any(k in path.name.lower() for k in ("router", "route", "app", "main", "index")):
            for m in _FRONTEND_ROUTE_OBJ_RE.finditer(text):
                routes.add(m.group("path"))
    return routes


def frontend_api_calls(frontend: Path) -> set[str]:
    """提取前端真正发出的请求路径（只认 fetch/request 调用的第一个字符串实参）。"""
    calls: set[str] = set()
    for path in list(frontend.rglob("*.ts")) + list(frontend.rglob("*.tsx")):
        if "node_modules" in path.parts:
            continue
        for m in _FRONTEND_CALL_RE.finditer(_read(path)):
            raw = _norm(m.group("path"))
            if not raw.startswith("/"):
                continue
            # 去掉统一的 api 前缀，便于与后端路由比较
            for prefix in ("/api/v1", "/api"):
                if raw.startswith(prefix):
                    raw = raw[len(prefix) :] or "/"
                    break
            # 裸根路径（多半是 baseURL 常量本身）不作为接口调用比较
            if raw in {"/", ""}:
                continue
            calls.add(raw)
    return calls


# ---------------------------------------------------------------- Python 导入检查

def python_local_import_errors(backend: Path) -> list[str]:
    """检查 backend 内部相对本地包的导入是否指向真实存在的模块。

    注意：Python 3 支持**命名空间包**（目录里没有 ``__init__.py`` 也能导入），
    所以「目录存在且有 .py 文件」同样算合法，不能因为没有 ``__init__.py`` 就判缺陷。
    """
    errors: list[str] = []
    top_level = {
        p.name
        for p in backend.iterdir()
        if p.is_dir() and (p / "__init__.py").exists() or (p.is_dir() and any(p.glob("*.py")))
    }
    if not top_level:
        return errors

    for path in backend.rglob("*.py"):
        try:
            tree = ast.parse(_read(path))
        except SyntaxError as exc:
            errors.append(f"{path.relative_to(backend)} 语法错误：{exc}")
            continue
        for node in ast.walk(tree):
            names: list[str] = []
            if isinstance(node, ast.ImportFrom) and node.module:
                names = [node.module]
            elif isinstance(node, ast.Import):
                names = [a.name for a in node.names]
            for dotted in names:
                root = dotted.split(".")[0]
                if root not in top_level:
                    continue
                rel = Path(*dotted.split("."))
                if (backend / rel).with_suffix(".py").exists():
                    continue
                # 命名空间包 / 普通包：目录下有 .py 文件即可
                if (backend / rel).is_dir() and any((backend / rel).glob("*.py")):
                    continue
                if (backend / rel / "__init__.py").exists():
                    continue
                errors.append(f"{path.relative_to(backend)} 引用了不存在的模块：{dotted}")
    return sorted(set(errors))


def frontend_import_errors(frontend: Path) -> list[str]:
    """检查前端相对导入是否指向真实存在的文件。"""
    errors: list[str] = []
    pattern = re.compile(r"""from\s+["'](?P<path>\.{1,2}/[^"']+)["']""")
    for path in list(frontend.rglob("*.ts")) + list(frontend.rglob("*.tsx")):
        if "node_modules" in path.parts:
            continue
        for m in pattern.finditer(_read(path)):
            target = (path.parent / m.group("path")).resolve()
            candidates = [
                target,
                target.with_suffix(".ts"),
                target.with_suffix(".tsx"),
                target / "index.ts",
                target / "index.tsx",
            ]
            if not any(c.is_file() for c in candidates):
                errors.append(f"{path.relative_to(frontend)} 引用了不存在的文件：{m.group('path')}")
    return sorted(set(errors))


# ---------------------------------------------------------------- 汇总


def check_project(root: Path, prd: dict[str, Any], arch: dict[str, Any]) -> dict[str, Any]:
    """对生成的 MVP 项目做一轮客观体检。"""
    backend = root / "backend"
    frontend = root / "frontend"
    findings: list[dict[str, str]] = []
    facts: dict[str, Any] = {}

    # 1) 目录是否存在
    if not backend.exists():
        findings.append(_f("high", "backend/", "后端目录缺失", "让后端工程师补齐交付清单"))
    if not frontend.exists():
        findings.append(_f("high", "frontend/", "前端目录缺失", "让前端工程师补齐交付清单"))

    # 2) 后端路由 vs 架构契约
    declared = {_norm(e.get("path", "")) for e in arch.get("api_contract", [])}
    implemented_paths: set[str] = set()
    if backend.exists():
        implemented_paths = {_norm(sig.split(" ", 1)[1]) for sig in backend_routes(backend)}
    # 契约里可能带 /api 前缀而实现里由 include_router 补上，两边都归一化一次
    declared_bare = {_strip_api(p) for p in declared}
    implemented_bare = {_strip_api(p) for p in implemented_paths}
    facts["api_declared"] = sorted(declared)
    facts["api_implemented"] = sorted(implemented_paths)
    missing_api = {p for p in declared_bare if p and p not in implemented_bare}
    if missing_api:
        findings.append(
            _f("high", "backend", f"契约声明但未实现的路由：{sorted(missing_api)}", "补充对应 router")
        )

    # 3) 前端路由 vs PRD 页面
    prd_routes: set[str] = set()
    for page in prd.get("pages", []):
        prd_routes.update(_split_routes(page.get("route", "")))
    fe_routes: set[str] = set()
    if frontend.exists():
        fe_routes = {_norm(r) for r in frontend_routes(frontend)}
    facts["prd_routes"] = sorted(prd_routes)
    facts["frontend_routes"] = sorted(fe_routes)
    missing_pages = {r for r in prd_routes if r and r not in fe_routes}
    if missing_pages:
        findings.append(
            _f("high", "frontend", f"PRD 要求但未找到对应路由的页面：{sorted(missing_pages)}", "在路由表中注册这些页面")
        )

    # 4) 前端调用路径 vs 后端实现
    if frontend.exists() and backend.exists():
        calls = frontend_api_calls(frontend)
        facts["frontend_calls"] = sorted(calls)
        unresolved = {c for c in calls if c and c not in implemented_bare}
        if unresolved:
            findings.append(
                _f(
                    "medium",
                    "frontend/api",
                    f"前端调用的路径未在后端找到实现：{sorted(unresolved)[:8]}",
                    "对齐 API 契约中的路径",
                )
            )

    # 5) package.json 必备脚本
    pkg = frontend / "package.json"
    if frontend.exists():
        if not pkg.is_file():
            findings.append(_f("high", "frontend/package.json", "package.json 缺失", "补上 Vite + React 的 package.json"))
        else:
            try:
                data = json.loads(_read(pkg))
                scripts = data.get("scripts", {})
                facts["npm_scripts"] = sorted(scripts)
                for need in ("dev", "build"):
                    if need not in scripts:
                        findings.append(
                            _f("medium", "frontend/package.json", f"缺少 `{need}` 脚本", f"补充 \"{need}\" 命令")
                        )
                deps = {**data.get("dependencies", {}), **data.get("devDependencies", {})}
                facts["npm_deps"] = sorted(deps)
                for need in ("react", "react-dom", "vite", "typescript"):
                    if need not in deps:
                        findings.append(
                            _f("high", "frontend/package.json", f"缺少依赖 {need}", "写入 dependencies/devDependencies")
                        )
            except json.JSONDecodeError as exc:
                findings.append(_f("high", "frontend/package.json", f"JSON 解析失败：{exc}", "修正 JSON"))

    # 6) requirements.txt
    if backend.exists() and not (backend / "requirements.txt").is_file():
        findings.append(_f("medium", "backend/requirements.txt", "依赖清单缺失", "补上 requirements.txt"))

    # 7) 导入完整性
    if backend.exists():
        for err in python_local_import_errors(backend)[:10]:
            findings.append(_f("high", "backend", err, "修正导入或补齐模块"))
    if frontend.exists():
        for err in frontend_import_errors(frontend)[:10]:
            findings.append(_f("high", "frontend", err, "修正导入或补齐文件"))

    # 8) 交付清单 vs 实际文件（部署期产物由运维工程师在质量门之后补齐，此处不计）
    layout = [p for p in arch.get("directory_layout", []) if p]
    if layout:
        missing = []
        for item in layout:
            clean = _layout_path(item)
            if not clean or clean.endswith("/") or _is_deploy_stage(clean):
                continue
            if not (root / clean).exists():
                missing.append(clean)
        facts["declared_files_missing"] = missing[:15]
        if missing:
            findings.append(
                _f("medium", "交付清单", f"{len(missing)} 个声明文件未产出：{missing[:8]}", "补齐缺失文件")
            )

    return {"findings": findings, "facts": facts}


def _layout_path(item: str) -> str:
    """从交付清单的一行里抠出文件路径。

    架构师常写成 ``backend/app/main.py：创建 FastAPI 应用`` 这种「路径 + 全角冒号 + 说明」，
    粗暴按空格切会把说明一起当成路径，从而产生大量假缺陷。
    """
    s = str(item).strip().strip("`-*• ")
    # 常见的「路径 / 说明」分隔符：全角冒号、半角冒号、破折号、括号、顿号
    s = re.split(r"[：:（(【\[]|\s+[-—–]\s+|\s{2,}|[，、]", s)[0].strip()
    if " " in s:
        head = s.split(" ")[0]
        if "/" in head or "." in head:
            s = head
    s = s.strip("`'\"-*• ")
    # 只保留看起来像路径的项（含目录分隔符或扩展名）
    return s if ("/" in s or "." in s) else ""


def _strip_api(path: str) -> str:
    for prefix in ("/api/v1", "/api"):
        if path.startswith(prefix):
            return path[len(prefix) :] or "/"
    return path


def _is_deploy_stage(path: str) -> bool:
    low = path.lower()
    return any(pattern in low for pattern in _DEPLOY_STAGE_PATTERNS)


def _f(severity: str, where: str, issue: str, fix: str) -> dict[str, str]:
    return {"severity": severity, "where": where, "issue": issue, "fix": fix}


def format_facts(result: dict[str, Any]) -> str:
    return json.dumps(result, ensure_ascii=False, indent=2, default=str)
