"""LangGraph 拓扑：把 8 位专家编排成一条可执行、可回退的 MVP 交付流水线。

    ┌──────────────────┐
    │  START           │
    └────────┬─────────┘
             ▼
    ┌──────────────────┐        🎬 项目总监
    │ director_brief   │  锁定项目简报、项目代号
    └────────┬─────────┘
             ▼
    │ director_plan    │  任务拆解 + 角色指派
             ▼
    │ pm_analyze       │  📋 产品经理 → PRD
             ▼
    │ scaffold_baseline│  🧱 工程骨架（不走模型）：构建配置 / 数据库底座 /
             ▼                测试脚手架 / 部署脚本，并冻结代码级契约
        ╭────┴────╮   ←── 并行扇出（同一个 superstep）
        ▼         ▼
   architect   ui_design      🏛️ 技术方案 + API 契约 ／ 🎨 设计规范
        ╰────┬────╯
        ╭────┴────╮   ←── 菱形汇聚：两位工程师都依赖两份上游产出
        ▼         ▼
   backend_dev  frontend_dev  ⚙️ 后端服务 ／ 🖥️ 前端页面
        ╰────┬────╯
             ▼
      ┌──────────────┐
      │   qa_test    │  🔍 质量门四道证据：契约一致性 → 静态体检 →
      └──────┬───────┘     真跑 pytest → 真启动服务冒烟打接口
             ▼
      ┌──────────────┐   未通过且未超轮数 → 打回工程师返工
      │ route_after  │──────────────────────────┐
      └──────┬───────┘                          │
             ▼ 通过                              │
      devops_deploy  🚀 部署核对                │
             ▼                                  │
      devops_docs    📖 运行手册 + 交付自检 + 交付状态
             ▼                                  │
      director_review 🎬 验收交付                │
             ▼                                  │
            END  ◄─────────────────────────────┘（回到 backend_dev / frontend_dev）
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Send

from mvp_team.agents import build_nodes
from mvp_team.config import Settings
from mvp_team.llm import TeamLLM
from mvp_team.state import TeamState, new_state


# ---------------------------------------------------------------------------------------
# 条件路由
# ---------------------------------------------------------------------------------------


def route_after_qa(state: TeamState, settings: Settings) -> str | list[Send]:
    """质量门之后的走向。

    * 通过 → 进入部署阶段；
    * 未通过且还有返工额度 → 用 Send 把任务**并发送回**对应工程师；
    * 未通过但额度用尽 → 带风险继续部署——此时 `delivery_status` 会被标为 `risk`，
      交付文档与事件流都会明确写出「未通过质量门」，不会静默当成功交付。
    """
    passed = bool(state.get("qa_passed"))
    rounds = int(state.get("qa_round") or 0)
    if passed:
        return "devops_deploy"
    if rounds >= settings.max_qa_rounds:
        return "devops_deploy"

    report = state.get("test_report") or {}
    owner = str(report.get("rework_for") or "both").lower()
    if owner == "backend":
        return [Send("backend_dev", state)]
    if owner == "frontend":
        return [Send("frontend_dev", state)]
    return [Send("backend_dev", state), Send("frontend_dev", state)]


# ---------------------------------------------------------------------------------------
# 构图
# ---------------------------------------------------------------------------------------


def build_graph(settings: Settings, llm: TeamLLM | None = None, checkpointer: Any = None):
    """编译并返回可执行的 LangGraph 应用。"""
    llm = llm or TeamLLM(settings)
    nodes = build_nodes(llm, settings)

    graph = StateGraph(TeamState)

    # ---- 注册节点 ----
    for name, fn in nodes.items():
        graph.add_node(name, fn)

    # ---- 主线 ----
    graph.add_edge(START, "director_brief")
    graph.add_edge("director_brief", "director_plan")
    graph.add_edge("director_plan", "pm_analyze")

    # ---- 工程骨架：在架构与设计开工前，用确定性代码把工程基线铺好 ----
    #      这样所有下游角色都能看到真实的文件树，不再臆造路径；
    #      骨架导出的符号（get_settings / Base / get_db / client fixture）即代码级契约。
    graph.add_edge("pm_analyze", "scaffold_baseline")

    # ---- 并行扇出：骨架就绪后，架构与设计同时开工（同一 superstep）----
    graph.add_edge("scaffold_baseline", "architect_design")
    graph.add_edge("scaffold_baseline", "ui_design")

    # ---- 菱形汇聚：两位工程师都必须等到「架构 + 设计」都完成 ----
    graph.add_edge("architect_design", "backend_dev")
    graph.add_edge("architect_design", "frontend_dev")
    graph.add_edge("ui_design", "backend_dev")
    graph.add_edge("ui_design", "frontend_dev")

    # ---- 汇流到质量门 ----
    graph.add_edge("backend_dev", "qa_test")
    graph.add_edge("frontend_dev", "qa_test")

    # ---- 条件路由：放行 or 打回返工 ----
    graph.add_conditional_edges(
        "qa_test",
        lambda state: route_after_qa(state, settings),
        ["devops_deploy", "backend_dev", "frontend_dev"],
    )

    graph.add_edge("devops_deploy", "devops_docs")
    graph.add_edge("devops_docs", "director_review")
    graph.add_edge("director_review", END)

    return graph.compile(checkpointer=checkpointer or MemorySaver())


# ---------------------------------------------------------------------------------------
# 运行入口
# ---------------------------------------------------------------------------------------


def run_workflow(
    idea: str,
    output_dir: str | Path = "generated",
    settings: Settings | None = None,
    on_event: Callable[[dict[str, Any]], None] | None = None,
    thread_id: str = "mvp-run",
) -> TeamState:
    """跑一次完整流水线，返回最终状态。

    ``on_event`` 会在每个节点完成后被调用，用于 CLI 实时打印进度。
    """
    settings = settings or Settings.load()
    settings.validate()

    app = build_graph(settings)
    initial = new_state(idea=idea, output_dir=str(Path(output_dir).expanduser().resolve()))
    config = {"configurable": {"thread_id": thread_id}, "recursion_limit": 60}

    final: dict[str, Any] = dict(initial)
    collected_events: list[Any] = []
    for chunk in app.stream(initial, config=config, stream_mode="updates"):
        for node_name, update in chunk.items():
            if not isinstance(update, dict):
                continue
            for key, value in update.items():
                if key == "events":
                    for e in value:
                        collected_events.append(e)
                        if on_event:
                            on_event({"node": node_name, "event": e})
                    continue
                if key in {"artifacts", "docs_files", "qa_feedback", "run_log"}:
                    final[key] = list(final.get(key, [])) + list(value)
                else:
                    final[key] = value
    # 事件流同样并入最终状态，便于 --json 摘要与外部系统消费
    final["events"] = collected_events
    return final  # type: ignore[return-value]
