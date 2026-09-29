"""MVP 开发专家团 —— 基于 LangGraph 的多智能体 MVP 开发工作流。

8 位专家角色分工协作，把「一句话需求」变成可运行的 MVP 产品源码：

    项目总监 → 产品经理 → {首席架构师, UI/UX 设计师} → {后端工程师, 前端工程师}
             → 测试工程师 → 运维工程师 → 项目总监（验收交付）
"""

from mvp_team.graph import build_graph, run_workflow
from mvp_team.state import TeamState, FileArtifact

__all__ = ["build_graph", "run_workflow", "TeamState", "FileArtifact"]
__version__ = "0.1.0"
