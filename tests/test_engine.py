"""工作流引擎自身的单元测试（不依赖网络与模型）。"""

from __future__ import annotations

from pathlib import Path

import pytest

from mvp_team.config import Settings
from mvp_team.graph import build_graph
from mvp_team.tools.codeblocks import parse_file_blocks
from mvp_team.tools.jsonx import extract_json

# ------------------------------------------------------------------ 代码块解析


def test_parse_file_blocks_basic():
    text = """
说明文字。

```file:backend/app/main.py
from fastapi import FastAPI
app = FastAPI()
```

```file:frontend/package.json
{"name": "demo"}
```
"""
    files = parse_file_blocks(text)
    assert [f.path for f in files] == ["backend/app/main.py", "frontend/package.json"]
    assert "FastAPI()" in files[0].content
    assert files[1].content.strip().endswith("}")


def test_parse_file_blocks_ignores_plain_blocks():
    text = """
```python
print("这是示例片段，不应落盘")
```

```file:README.md
# 标题
```
"""
    files = parse_file_blocks(text)
    assert len(files) == 1
    assert files[0].path == "README.md"


def test_parse_file_blocks_supports_file_equals():
    files = parse_file_blocks("```ts file=src/api.ts\nexport const x = 1;\n```")
    assert files[0].path == "src/api.ts"


# ------------------------------------------------------------------ JSON 抽取


@pytest.mark.parametrize(
    "raw",
    [
        '{"a": 1}',
        '```json\n{"a": 1}\n```',
        '好的，结果如下：\n```json\n{"a": 1}\n```\n希望有帮助。',
        '{"a": 1,}',
        '{“a”: 1}',
    ],
)
def test_extract_json_variants(raw):
    assert extract_json(raw) == {"a": 1}


def test_extract_json_gives_up_gracefully():
    assert extract_json("这里完全没有 JSON") is None


# ------------------------------------------------------------------ 拓扑


def test_graph_compiles_and_has_expected_nodes():
    settings = Settings.load(dotenv=False)
    settings.dry_run = True
    app = build_graph(settings)
    nodes = set(app.get_graph().nodes)
    expected = {
        "director_brief",
        "director_plan",
        "pm_analyze",
        "architect_design",
        "ui_design",
        "backend_dev",
        "frontend_dev",
        "qa_test",
        "devops_deploy",
        "devops_docs",
        "director_review",
    }
    assert expected.issubset(nodes)


def test_route_after_qa_rules():
    from mvp_team.graph import route_after_qa

    settings = Settings.load(dotenv=False)
    settings.max_qa_rounds = 2

    assert route_after_qa({"qa_passed": True}, settings) == "devops_deploy"

    # 未通过且还有额度 → 打回
    sends = route_after_qa({"qa_passed": False, "qa_round": 1, "test_report": {"rework_for": "backend"}}, settings)
    assert isinstance(sends, list) and len(sends) == 1

    # 未通过但额度用尽 → 放行（带风险）
    assert route_after_qa({"qa_passed": False, "qa_round": 2}, settings) == "devops_deploy"


# ------------------------------------------------------------------ 端到端（离线）


def test_dry_run_end_to_end(tmp_path: Path):
    from mvp_team.agents.base import project_dir, write_text
    from mvp_team.graph import run_workflow

    settings = Settings.load(dotenv=False)
    settings.dry_run = True
    settings.max_qa_rounds = 1

    events: list[dict] = []
    final = run_workflow(
        idea="我想做一个电商小程序后台",
        output_dir=tmp_path,
        settings=settings,
        on_event=events.append,
    )

    # 每个角色都留下了痕迹
    roles = {e["event"].role for e in events}
    assert {"director", "pm", "designer", "architect", "backend", "frontend", "qa", "devops"} <= roles

    # 关键状态字段齐全
    assert final.get("brief")
    assert final.get("prd") is not None
    assert final.get("architecture") is not None
    assert final.get("design") is not None
    assert final.get("qa_round", 0) >= 1
    assert final.get("summary")

    # 产物目录里确实有文件
    root = project_dir(final)
    assert root.exists()
    assert any(root.rglob("*.md"))


def test_output_guard_blocks_escape(tmp_path: Path):
    from mvp_team.agents.base import project_dir, persist_generated
    from mvp_team.state import new_state

    state = new_state("x", str(tmp_path), project_name="demo")
    state["project_name"] = "demo"
    files, warnings = persist_generated(state, "```file:../../evil.txt\nboom\n```", "backend")
    assert files == [] and warnings
    assert not (tmp_path.parent / "evil.txt").exists()
    assert project_dir(state).parent == tmp_path
