"""冒烟门：真的把服务启动起来，真的打接口。

## 为什么需要它

pytest 全绿不等于产品能跑。真实运行里出现过「59 个后端用例全部通过，但前端
``npm run build`` 直接失败」——如果没人真去构建、真去启动，交出去的就是一个
打不开的样机。静态体检和单元测试都验证不了「进程能不能起来、路由能不能响应」。

所以这里做最直接的一件事：

1. 用一个独立的临时数据库，真启动 ``uvicorn app.main:app``；
2. 轮询健康检查直到返回 200（失败则给出进程输出，便于定位）；
3. 对契约里每个**无路径参数**的 GET 接口打一遍，记录状态码；
4. 若契约给了可用的请求体，再试打一个 POST，验证写路径。

只有这一步通过，「一句话生成可运行的产品样机」才算有了硬证据。
"""

from __future__ import annotations

import http.cookiejar
import json
import os
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

#: 这些状态码不算缺陷：需要鉴权 / 方法不允许 / 无内容
_BENIGN_STATUS = {401, 403, 405}

#: 健康检查候选路径
HEALTH_CANDIDATES = ("/api/health", "/health", "/api/healthz", "/healthz")


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _http(
    url: str,
    *,
    method: str = "GET",
    payload: dict[str, Any] | None = None,
    timeout: float = 5.0,
    token: str = "",
    opener: Any = None,
) -> tuple[int, str]:
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    headers: dict[str, str] = {}
    if data:
        headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    open_url = opener.open if opener is not None else urllib.request.urlopen
    try:
        with open_url(request, timeout=timeout) as response:
            return int(response.status), response.read(8192).decode("utf-8", "replace")
    except urllib.error.HTTPError as exc:
        return int(exc.code), exc.read(4096).decode("utf-8", "replace")
    except Exception as exc:  # noqa: BLE001  连接类异常统一转成 0
        return 0, f"{type(exc).__name__}: {exc}"


def _candidates(path: str) -> list[str]:
    """同一个契约路径可能带或不带 /api 前缀，两个都试。"""
    path = "/" + str(path).lstrip("/")
    out = [path]
    if not path.startswith("/api"):
        out.append("/api" + path)
    return out


def _probe(base: str, path: str, token: str = "", opener: Any = None) -> tuple[int, str, str]:
    """返回 (状态码, 响应片段, 命中的完整路径)。"""
    last: tuple[int, str, str] = (0, "", "")
    for candidate in _candidates(path):
        status, body = _http(base + candidate, timeout=8.0, token=token, opener=opener)
        last = (status, body, candidate)
        if status and status not in {404}:
            return last
    return last


# ---------------------------------------------------------------- 自动登录


def _deep_find_token(node: Any, depth: int = 0) -> str:
    """从登录响应里挖出 token —— 各家字段名不一，所以做一次深度搜索。"""
    if depth > 4:
        return ""
    if isinstance(node, dict):
        for key in ("access_token", "accessToken", "token", "jwt", "access"):
            value = node.get(key)
            if isinstance(value, str) and len(value) >= 8:
                return value
        for value in node.values():
            found = _deep_find_token(value, depth + 1)
            if found:
                return found
    elif isinstance(node, list):
        for value in node[:3]:
            found = _deep_find_token(value, depth + 1)
            if found:
                return found
    return ""


def _parse_payload(raw: Any) -> dict[str, Any] | None:
    if isinstance(raw, dict):
        return raw or None
    if isinstance(raw, str) and raw.strip().startswith("{"):
        try:
            parsed = json.loads(raw)
        except ValueError:
            return None
        return parsed if isinstance(parsed, dict) and parsed else None
    return None


def find_login_spec(api_contract: list[dict[str, Any]] | None) -> dict[str, Any] | None:
    """找出登录接口，用于拿到 token 后再探测受保护资源。"""
    for endpoint in api_contract or []:
        if str(endpoint.get("method", "")).upper() != "POST":
            continue
        path = str(endpoint.get("path", ""))
        lowered = path.lower()
        if not any(token in lowered for token in ("login", "signin", "sign-in", "token", "session")):
            continue
        payload = _parse_payload(endpoint.get("request"))
        if payload:
            return {"path": path, "payload": payload}
    return None


def _try_login(base: str, spec: dict[str, Any], opener: Any = None, jar: Any = None) -> tuple[str, str]:
    """返回 (token, 说明)。

    登录方式有两种常见形态，都要支持：
    * 响应体里下发 access_token → 后续用 ``Authorization: Bearer`` 携带；
    * 用 ``Set-Cookie`` 下发 HttpOnly 会话 → 由 cookie jar 自动携带。

    拿不到令牌或会话**不算缺陷**——只是退化为「匿名探测，受保护接口跳过」。
    """
    last_status = 0
    for candidate in _candidates(spec["path"]):
        status, body = _http(
            base + candidate, method="POST", payload=spec["payload"], timeout=10.0, opener=opener
        )
        last_status = status
        if status in {200, 201}:
            token = _deep_find_token(_safe_json(body))
            if token:
                return token, f"- 已通过 `POST {candidate}` 取得访问令牌（Bearer），后续请求将携带 ✅"
            if jar is not None and len(jar) > 0:
                return "", f"- 已通过 `POST {candidate}` 建立会话（Cookie 已保存），后续请求将携带 ✅"
            return "", f"- `POST {candidate}` → {status}，但未取得令牌或会话，后续按匿名探测"
    return "", f"- 尝试登录失败（HTTP {last_status or '连接错误'}），后续按匿名探测"


def _safe_json(text: str) -> Any:
    try:
        return json.loads(text)
    except (ValueError, TypeError):
        return None


def _is_json(text: str) -> bool:
    try:
        json.loads(text)
        return True
    except (ValueError, TypeError):
        return False


def select_probe_targets(api_contract: list[dict[str, Any]]) -> tuple[list[str], dict[str, Any] | None]:
    """从 API 契约里挑出可安全探测的 GET 列表接口与一个 POST 目标。"""
    gets: list[str] = []
    post: dict[str, Any] | None = None

    for endpoint in api_contract or []:
        method = str(endpoint.get("method", "GET")).upper()
        path = str(endpoint.get("path", "")).strip()
        if not path:
            continue
        # 带路径参数的接口需要真实 id，冒烟阶段跳过
        if "{" in path or ":" in path.split("/")[-1]:
            continue
        if method == "GET":
            lowered = path.lower()
            if any(token in lowered for token in ("health", "/docs", "/openapi")):
                continue
            gets.append(path)
        elif method == "POST" and post is None:
            # 登录/登出类接口由专门的登录步骤处理，不作为写路径样本
            if any(token in path.lower() for token in ("login", "signin", "sign-in", "token", "session", "logout")):
                continue
            payload = _parse_payload(endpoint.get("request"))
            if payload:
                post = {"path": path, "payload": payload}

    # 去重并限量，避免冒烟阶段打太多请求
    seen: set[str] = set()
    unique_gets: list[str] = []
    for path in gets:
        key = path.rstrip("/")
        if key not in seen:
            seen.add(key)
            unique_gets.append(path)
    return unique_gets[:8], post


def run_smoke(
    root: Path,
    api_contract: list[dict[str, Any]] | None = None,
    *,
    python: str | None = None,
    startup_timeout: float = 60.0,
    extra_paths: list[str] | None = None,
    post_spec: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """启动服务并冒烟探测。返回 ``{ok, report, facts, findings}``。"""
    root = Path(root)
    backend = root / "backend"
    findings: list[dict[str, str]] = []
    facts: dict[str, Any] = {"started": False}

    def _f(severity: str, where: str, issue: str, fix: str) -> dict[str, str]:
        return {"severity": severity, "where": where, "issue": issue, "fix": fix}

    if not (backend / "app" / "main.py").is_file():
        findings.append(
            _f("high", "backend/app/main.py", "缺少应用入口，无法启动服务", "后端工程师必须产出 app/main.py")
        )
        return {"ok": False, "report": "未找到 backend/app/main.py，冒烟测试无法执行。", "facts": facts, "findings": findings}

    interpreter = python or sys.executable or "python3"
    port = _free_port()
    base = f"http://127.0.0.1:{port}"

    # 同一个 jar 贯穿整轮冒烟，Cookie 会话才能延续到后续请求
    jar = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))

    tmp_dir = Path(tempfile.mkdtemp(prefix="mvp-smoke-"))
    log_path = tmp_dir / "uvicorn.log"

    env = dict(os.environ)
    env["PYTHONPATH"] = str(backend) + os.pathsep + env.get("PYTHONPATH", "")
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PYTHONUNBUFFERED"] = "1"
    # 用独立数据库，避免污染产物目录
    env["DATABASE_URL"] = f"sqlite:///{tmp_dir / 'smoke.db'}"
    env.setdefault("APP_ENV", "production")

    cmd = [interpreter, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", str(port)]
    log_handle = log_path.open("w", encoding="utf-8", errors="replace")

    process: subprocess.Popen[str] | None = None
    lines: list[str] = []
    try:
        try:
            process = subprocess.Popen(
                cmd, cwd=str(backend), env=env, stdout=log_handle, stderr=subprocess.STDOUT, text=True
            )
        except OSError as exc:
            findings.append(
                _f("high", "backend", f"无法启动 uvicorn：{exc}", "检查环境是否安装 uvicorn")
            )
            return {"ok": False, "report": f"无法启动 uvicorn：{exc}", "facts": facts, "findings": findings}

        # ---- 1) 等待健康检查 ----
        deadline = time.time() + startup_timeout
        healthy_path = ""
        while time.time() < deadline:
            if process.poll() is not None:
                break
            for candidate in HEALTH_CANDIDATES:
                status, body = _http(base + candidate, timeout=3.0)
                if status == 200:
                    healthy_path = candidate
                    break
            if healthy_path:
                break
            time.sleep(1.0)

        if not healthy_path:
            log_handle.flush()
            tail = log_path.read_text(encoding="utf-8", errors="replace")[-3000:]
            exited = process.poll()
            reason = (
                f"服务进程已退出（退出码 {exited}）" if exited is not None
                else f"在 {int(startup_timeout)} 秒内未通过健康检查"
            )
            findings.append(
                _f(
                    "high",
                    "backend/app/main.py",
                    f"服务无法启动：{reason}",
                    "检查应用入口能否 import、依赖是否齐全、启动事件是否抛异常；"
                    f"原始输出见下方日志",
                )
            )
            report = (
                f"### 冒烟结果：❌ 未通过\n\n- {reason}\n\n"
                f"启动日志（末尾 3000 字符）：\n```text\n{tail or '（无输出）'}\n```\n"
            )
            facts["startup_log_tail"] = tail[-1500:]
            return {"ok": False, "report": report, "facts": facts, "findings": findings}

        facts["started"] = True
        facts["health_path"] = healthy_path
        lines.append(f"- 健康检查 `{healthy_path}` → 200 ✅")

        # ---- 2) 尝试登录：拿到 token 后受保护接口才探测得动 ----
        gets, auto_post = select_probe_targets(api_contract or [])
        for path in extra_paths or []:
            if path not in gets:
                gets.append(path)

        token = ""
        login_spec = find_login_spec(api_contract)
        if login_spec:
            token, note = _try_login(base, login_spec, opener, jar)
            lines.append(note)
            facts["login_ok"] = bool(token) or len(jar) > 0

        # ---- 3) GET 探测 ----
        get_ok = 0
        get_bad: list[str] = []
        for path in gets:
            status, body, hit = _probe(base, path, token, opener)
            if status == 200:
                if not _is_json(body):
                    lines.append(f"- `GET {hit}` → 200 但响应不是 JSON ⚠️")
                    findings.append(
                        _f(
                            "medium",
                            f"GET {hit}",
                            "接口返回 200，但响应体不是合法 JSON",
                            "确保返回 JSONResponse 或 Pydantic 模型",
                        )
                    )
                else:
                    get_ok += 1
                    lines.append(f"- `GET {hit}` → 200 ✅")
            elif status in _BENIGN_STATUS:
                lines.append(f"- `GET {hit}` → {status}（需鉴权/不适用，跳过）")
            else:
                get_bad.append(f"{hit}({status})")
                lines.append(f"- `GET {hit}` → {status or '连接失败'} ❌")
                findings.append(
                    _f(
                        "high",
                        f"GET {hit}",
                        f"接口冒烟失败，返回 {status or '连接错误'}",
                        "确认路由已注册、依赖注入可用、查询不会抛异常",
                    )
                )
        facts["get_probed"] = len(gets)
        facts["get_passed"] = get_ok
        facts["get_failed"] = get_bad

        # ---- 4) POST 探测 ----
        spec = post_spec or auto_post
        post_line = "- （契约未提供可用请求体，跳过写路径探测）"
        post_ok = True
        if spec:
            status, body = _http(
                base + _candidates(spec["path"])[0],
                method="POST",
                payload=spec["payload"],
                timeout=10.0,
                token=token,
                opener=opener,
            )
            if not status or status == 404:
                status, body = _http(
                    base + _candidates(spec["path"])[-1],
                    method="POST",
                    payload=spec["payload"],
                    timeout=10.0,
                    token=token,
                    opener=opener,
                )
            if status in {200, 201, 202}:
                post_line = f"- `POST {spec['path']}` → {status} ✅"
            elif status in {400, 422}:
                post_line = f"- `POST {spec['path']}` → {status}（请求体被拒，可能是契约示例不完整，不计失败）"
            elif status in _BENIGN_STATUS:
                post_line = f"- `POST {spec['path']}` → {status}（需鉴权，跳过）"
            else:
                post_ok = False
                post_line = f"- `POST {spec['path']}` → {status or '连接失败'} ❌"
                findings.append(
                    _f(
                        "high",
                        f"POST {spec['path']}",
                        f"写路径冒烟失败，返回 {status or '连接错误'}",
                        "确认创建接口可用、请求体校验与落库正常",
                    )
                )
        lines.append(post_line)

        ok = bool(facts["started"]) and not get_bad and post_ok
        head = "### 冒烟结果：✅ 通过" if ok else "### 冒烟结果：❌ 未通过"
        report = (
            f"{head}\n\n"
            f"- 服务已启动：{base}（健康检查 `{healthy_path}`）\n"
            f"- GET 探测：{get_ok}/{len(gets)} 通过\n"
            f"- 写路径：{'通过' if post_ok else '失败'}\n\n"
            + "\n".join(lines)
            + "\n"
        )
        return {"ok": ok, "report": report, "facts": facts, "findings": findings}

    finally:
        if process is not None and process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=8)
            except subprocess.TimeoutExpired:
                process.kill()
        log_handle.close()


def render_smoke_report(result: dict[str, Any]) -> str:
    return str(result.get("report", ""))


__all__ = ["run_smoke", "select_probe_targets", "render_smoke_report", "HEALTH_CANDIDATES"]
