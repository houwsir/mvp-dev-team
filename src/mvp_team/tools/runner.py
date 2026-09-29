"""子进程执行器：真实跑测试、真实构建，把原始输出交给测试工程师判断。"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path


def _python() -> str:
    return sys.executable or "python3"


def pip_install_requirements(backend_dir: Path, timeout: int = 600) -> tuple[bool, str]:
    """按生成产物的 requirements.txt 安装依赖，让质量门里的 pytest 有真实运行环境。

    依赖安装失败不直接判定为产品缺陷，而是作为「环境事实」写进报告，
    由测试工程师判断它到底是不是需求清单写错了。
    """
    req = backend_dir / "requirements.txt"
    if not req.is_file():
        pyproject = backend_dir / "pyproject.toml"
        if not pyproject.is_file():
            return True, "未发现 requirements.txt / pyproject.toml，跳过依赖安装"
        target = str(backend_dir)
    else:
        target = str(req)

    try:
        proc = subprocess.run(
            [_python(), "-m", "pip", "install", "-q", "--disable-pip-version-check", "-r" if req.is_file() else "-e", target],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return False, f"依赖安装超时（>{timeout}s）"
    except OSError as exc:
        return False, f"无法启动 pip：{exc}"

    if proc.returncode == 0:
        return True, "依赖安装成功"
    return False, ((proc.stdout or "") + "\n" + (proc.stderr or ""))[-3000:]


def run_pytest(backend_dir: Path, timeout: int = 300) -> tuple[bool, str]:
    """在 backend 目录下真实执行 pytest。返回 (是否通过, 原始输出)。"""
    if not backend_dir.is_dir():
        return False, f"目录不存在：{backend_dir}"
    tests = list(backend_dir.rglob("test_*.py")) + list(backend_dir.rglob("*_test.py"))
    if not tests:
        return False, "未发现任何测试文件（test_*.py）"

    env = dict(os.environ)
    env["PYTHONPATH"] = str(backend_dir) + os.pathsep + env.get("PYTHONPATH", "")
    env["PYTHONDONTWRITEBYTECODE"] = "1"

    cmd = [_python(), "-m", "pytest", "-q", "--no-header", "-p", "no:cacheprovider", "tests"]
    try:
        proc = subprocess.run(
            cmd,
            cwd=str(backend_dir),
            env=env,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return False, f"pytest 执行超时（>{timeout}s）"
    except OSError as exc:
        return False, f"无法启动 pytest：{exc}"

    output = (proc.stdout or "") + ("\n" + proc.stderr if proc.stderr else "")
    return proc.returncode == 0, output.strip()


def run_npm_build(frontend_dir: Path, timeout: int = 900) -> tuple[bool, str]:
    """真实安装依赖并构建前端（需要联网，默认关闭）。"""
    if not (frontend_dir / "package.json").is_file():
        return False, "frontend/package.json 不存在"
    npm = shutil.which("npm")
    if not npm:
        return False, "环境里找不到 npm"
    try:
        install = subprocess.run(
            [npm, "install", "--no-audit", "--no-fund"],
            cwd=str(frontend_dir),
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        if install.returncode != 0:
            return False, "npm install 失败：\n" + (install.stdout or "")[-4000:] + (install.stderr or "")[-2000:]
        build = subprocess.run(
            [npm, "run", "build"],
            cwd=str(frontend_dir),
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        out = (build.stdout or "") + ("\n" + build.stderr if build.stderr else "")
        return build.returncode == 0, out.strip()[-6000:]
    except subprocess.TimeoutExpired:
        return False, f"前端构建超时（>{timeout}s）"
    except OSError as exc:
        return False, f"无法启动 npm：{exc}"


def collect_sources(root: Path, budget: int = 90_000) -> str:
    """把项目源码汇总成一段文本（按预算截断），供审查使用。"""
    skip_dirs = {"node_modules", "dist", "__pycache__", ".pytest_cache", ".git"}
    exts = {".py", ".ts", ".tsx", ".js", ".jsx", ".json", ".css", ".html", ".md", ".txt", ".yml", ".yaml"}
    chunks: list[str] = []
    used = 0
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in exts:
            continue
        if skip_dirs & set(path.parts):
            continue
        rel = path.relative_to(root)
        if rel.parts and rel.parts[0] == "docs":
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        if len(text) > 12_000:
            text = text[:12_000] + "\n... [已截断]"
        block = f"\n===== FILE: {rel} =====\n{text}\n"
        if used + len(block) > budget:
            chunks.append(f"\n... [源码预算用尽，剩余文件未附上，共 {len(list(root.rglob('*')))} 个路径]")
            break
        chunks.append(block)
        used += len(block)
    return "".join(chunks)
