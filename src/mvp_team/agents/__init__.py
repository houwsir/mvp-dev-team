"""把 8 位专家装配成一组可供 LangGraph 使用的节点函数。"""

from __future__ import annotations

from typing import Any, Callable

from mvp_team.agents import (
    architect,
    backend,
    designer,
    devops,
    director,
    frontend,
    pm,
    qa,
    scaffold_node,
)
from mvp_team.prompts import PERSONAS

# 团队花名册（顺序即汇报顺序）
ROSTER: list[tuple[str, str, str]] = [
    ("director", "大湾区靓仔", "项目总监"),
    ("pm", "许清楚", "产品经理"),
    ("designer", "颜好看", "UI/UX 设计师"),
    ("architect", "高见远", "首席架构师"),
    ("frontend", "贾思敏", "前端工程师"),
    ("backend", "贝洛奇", "后端工程师"),
    ("qa", "严过关", "测试工程师"),
    ("devops", "卜宕机", "运维工程师"),
]


def build_nodes(llm: Any, settings: Any) -> dict[str, Callable[..., dict[str, Any]]]:
    """返回 ``节点名 -> 节点函数`` 的映射。

    ``scaffold_node`` 不走模型，它在架构/设计开工前把工程基线铺好。
    """
    nodes: dict[str, Callable[..., dict[str, Any]]] = {}
    for module in (
        director, pm, scaffold_node, architect, designer, backend, frontend, qa, devops,
    ):
        nodes.update(module.make_nodes(llm, settings))
    return nodes


def roster_text() -> str:
    lines = ["| 角色 | 姓名 | 职责 |", "| --- | --- | --- |"]
    for role, name, _ in ROSTER:
        p = PERSONAS[role]
        lines.append(f"| {p['emoji']} {p['title']} | {name} | {p['duty']} |")
    return "\n".join(lines)


__all__ = ["build_nodes", "ROSTER", "roster_text"]
