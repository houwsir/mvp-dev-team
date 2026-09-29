"""对已生成的 MVP 产物做一次独立的复检（不调用模型）。

用法：
    PYTHONPATH=src python scripts/verify.py generated/mini-shop-admin
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

from mvp_team.tools.runner import collect_sources, run_pytest
from mvp_team.tools.static_checks import _split_routes, check_project


def parse_prd_routes(prd_md: Path) -> list[str]:
    routes: list[str] = []
    for line in prd_md.read_text(encoding="utf-8").splitlines():
        for cell in re.findall(r"`([^`]+)`", line):
            routes.extend(_split_routes(cell))
    return sorted({r for r in routes if r.startswith("/")})


def parse_api_contracts(arch_md: Path) -> list[str]:
    paths: list[str] = []
    for line in arch_md.read_text(encoding="utf-8").splitlines():
        m = re.match(r"^\|\s*`?(GET|POST|PUT|PATCH|DELETE)\s+(/[^`|]+)`?\s*\|", line)
        if m:
            paths.append(m.group(2).strip())
    return sorted(set(paths))


def main(root_arg: str) -> int:
    root = Path(root_arg).resolve()
    prd_md = root / "docs" / "PRD.md"
    arch_md = root / "docs" / "ARCHITECTURE.md"

    routes = parse_prd_routes(prd_md) if prd_md.is_file() else []
    apis = parse_api_contracts(arch_md) if arch_md.is_file() else []

    print(f"PRD 页面路由（{len(routes)} 条）：")
    for r in routes:
        print(f"  {r}")
    print(f"\n契约声明接口（{len(apis)} 个）")

    result = check_project(root, {"pages": [{"route": r} for r in routes]}, {"api_contract": [{"path": a} for a in apis]})

    print("\n--- 确定性静态体检 ---")
    findings = result["findings"]
    if not findings:
        print("✅ 未发现问题")
    for f in findings:
        print(f"  [{f['severity']}] {f['where']}: {f['issue']}")
        print(f"        修复建议：{f['fix']}")

    print("\n--- 真实执行 pytest ---")
    backend = root / "backend"
    ok, out = run_pytest(backend)
    print(f"pytest：{'✅ 通过' if ok else '❌ 未通过'}")
    tail = [line for line in out.splitlines() if line.strip()][-12:]
    for line in tail:
        print(f"  {line}")

    print("\n--- 源码规模 ---")
    sources = collect_sources(root, budget=10**9)
    print(f"  参与统计的源码字符数：{len(sources)}")

    passed = ok and not findings
    print(f"\n总体结论：{'✅ 放行' if passed else '⚠️ 仍有待处理项'}")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1] if len(sys.argv) > 1 else "generated/mini-shop-admin"))
