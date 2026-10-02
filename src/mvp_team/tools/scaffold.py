"""工程骨架：把「不属于业务逻辑的工程基线」用代码铺好，不再交给模型发挥。

## 为什么要有这个模块

MVP 的技术栈是固定的（FastAPI + SQLAlchemy + React + Vite）。既然如此，
构建配置、测试脚手架、一键启动脚本、容器化文件这些东西**没有任何创造空间**，
交给模型每次重写只会带来缺陷。真实运行中反复出现的问题全部属于这一类：

* ``Makefile`` 引用了 ``deploy/start.sh``，但那个文件根本没生成；
* ``docker-compose.yml`` 指向 ``deploy/Dockerfile.backend``，文件不存在；
* ``tsconfig.node.json`` 配置错误，``npm run build`` 直接失败；
* ``vite.config.ts`` 混入 vitest 的 ``test`` 字段，构建报错；
* ``conftest.py`` 只定义了 1 个 fixture，测试却用了 7 个。

所以这里把工程基线**确定性地**铺好，工程师只负责写业务代码。

## 两类文件

* **skeleton（骨架）**：构建配置、数据库/配置底座、测试脚手架、部署脚本。
  工程师**禁止覆盖**，越界写入会被 ``persist_generated`` 拦截。
* **seed（种子）**：兜底可用版本（``App.tsx``、``api/client.ts``、设计令牌、
  ``README.md``）。工程师应当覆盖它们——但万一模型漏写，项目仍然能构建、能启动。

这两类合起来构成「代码级契约」：包结构、模块导出、环境变量名、fixture 名、
npm 脚本名都由骨架固定，上下游角色不再需要靠猜。
"""

from __future__ import annotations

import os
from pathlib import Path

_SKELETON_ROOT = Path(__file__).resolve().parents[1] / "scaffold"

# 工程师可以覆盖的兜底文件（相对项目根目录，POSIX 风格）
SEED_PATHS: frozenset[str] = frozenset(
    {
        "frontend/src/App.tsx",
        "frontend/src/api/client.ts",
        "frontend/src/styles/tokens.css",
        "frontend/src/styles/global.css",
        "README.md",
    }
)

# 需要可执行位的文件
_EXECUTABLE = ("deploy/start.sh",)


def template_root() -> Path:
    """骨架模板所在目录。"""
    return _SKELETON_ROOT


def ensure_template_root() -> None:
    """骨架模板不可用时**立刻报错**。

    没铺骨架的产物必然拿不到「可运行」的结论（缺构建配置、缺测试脚手架、
    缺部署脚本），静默跳过只会让问题推迟到交付时才暴露。
    """
    if not _SKELETON_ROOT.is_dir() or not template_files():
        raise RuntimeError(
            f"工程骨架模板不可用：{_SKELETON_ROOT}\n"
            "请确认 src/mvp_team/scaffold/ 目录完整；"
            "若从 wheel 安装，请改用 `pip install -e .` 或把 src 挂到 PYTHONPATH。"
        )


def template_files() -> list[str]:
    """骨架模板里的全部相对路径（POSIX 风格）。"""
    if not _SKELETON_ROOT.is_dir():
        return []
    out: list[str] = []
    for path in sorted(_SKELETON_ROOT.rglob("*")):
        if path.is_file():
            out.append(path.relative_to(_SKELETON_ROOT).as_posix())
    return out


def skeleton_paths() -> frozenset[str]:
    """骨架文件清单 —— 工程师禁止写入这些路径。"""
    return frozenset(p for p in template_files() if p not in SEED_PATHS)


def scaffold_paths() -> frozenset[str]:
    """骨架 + 种子的全部路径。"""
    return frozenset(template_files())


def write_scaffold(
    root: Path,
    *,
    include_seeds: bool = True,
    overwrite_skeleton: bool = True,
) -> list[tuple[str, str]]:
    """把骨架铺到项目目录。

    返回 ``[(相对路径, 动作)]``，动作取值 ``created`` / ``updated`` / ``kept``。

    * 骨架文件：默认覆盖（它是基线，必须与当前版本一致）；
    * 种子文件：只在缺失时写入，绝不覆盖已有内容。
    """
    root = Path(root)
    results: list[tuple[str, str]] = []

    for rel in template_files():
        is_seed = rel in SEED_PATHS
        if is_seed and not include_seeds:
            continue

        source = _SKELETON_ROOT / rel
        target = root / rel
        existed = target.is_file()

        if is_seed and existed:
            results.append((rel, "kept"))
            continue
        if not is_seed and existed and not overwrite_skeleton:
            results.append((rel, "kept"))
            continue

        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
        results.append((rel, "updated" if existed else "created"))

        if rel in _EXECUTABLE:
            try:
                os.chmod(target, 0o755)
            except OSError:
                pass

    return results


def render_scaffold_summary(results: list[tuple[str, str]]) -> str:
    created = [p for p, a in results if a == "created"]
    updated = [p for p, a in results if a == "updated"]
    kept = [p for p, a in results if a == "kept"]
    parts = [f"新建 {len(created)}"]
    if updated:
        parts.append(f"刷写 {len(updated)}")
    if kept:
        parts.append(f"保留 {len(kept)}")
    return "｜".join(parts)


__all__ = [
    "SEED_PATHS",
    "ensure_template_root",
    "scaffold_paths",
    "skeleton_paths",
    "template_files",
    "template_root",
    "write_scaffold",
    "render_scaffold_summary",
]
