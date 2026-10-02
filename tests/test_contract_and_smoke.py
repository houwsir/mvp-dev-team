"""新增能力的回归测试：工程骨架、契约一致性检查、冒烟门的选路逻辑、骨架禁写保护。"""

from __future__ import annotations

from pathlib import Path

from mvp_team.tools.contract_check import check_contract, fixture_findings, symbol_import_findings
from mvp_team.tools.scaffold import skeleton_paths, template_files, write_scaffold


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _backend_with_scaffold(tmp_path: Path) -> Path:
    root = tmp_path / "demo"
    write_scaffold(root)
    return root


# ------------------------------------------------------------------ 工程骨架


def test_scaffold_is_idempotent_and_protects_seeds(tmp_path: Path):
    root = tmp_path / "demo"

    first = dict(write_scaffold(root))
    assert sum(1 for a in first.values() if a == "created") == len(template_files())

    # 种子文件被工程师改写后，再跑骨架不应覆盖它
    seed = root / "frontend" / "src" / "App.tsx"
    seed.write_text("// 工程师写的", encoding="utf-8")
    second = dict(write_scaffold(root))
    assert second["frontend/src/App.tsx"] == "kept"
    assert seed.read_text(encoding="utf-8") == "// 工程师写的"


def test_scaffold_restores_damaged_skeleton(tmp_path: Path):
    root = tmp_path / "demo"
    write_scaffold(root)

    config = root / "backend" / "app" / "config.py"
    config.write_text("# 被模型破坏了", encoding="utf-8")

    write_scaffold(root)
    assert "get_settings" in config.read_text(encoding="utf-8")


def test_skeleton_paths_exclude_seeds():
    skeleton = skeleton_paths()
    assert "backend/app/database.py" in skeleton
    assert "backend/tests/conftest.py" in skeleton
    assert "frontend/tsconfig.json" in skeleton
    # 种子文件允许工程师覆盖，不在禁写清单里
    assert "frontend/src/App.tsx" not in skeleton
    assert "README.md" not in skeleton


def test_start_script_is_executable(tmp_path: Path):
    root = tmp_path / "demo"
    write_scaffold(root)
    mode = (root / "deploy" / "start.sh").stat().st_mode
    assert mode & 0o111, "start.sh 需要可执行位"


def test_scaffold_only_baseline_is_contract_clean(tmp_path: Path):
    """只有骨架、还没写业务代码时，契约检查不应产生任何缺陷。"""
    root = _backend_with_scaffold(tmp_path)
    result = check_contract(root)
    assert result["findings"] == [], result["findings"]


# ------------------------------------------------------------------ 契约一致性


def test_contract_catches_missing_symbol_import(tmp_path: Path):
    root = _backend_with_scaffold(tmp_path)
    _write(root / "backend" / "app" / "services" / "svc.py", "def probe_target():\n    return 1\n")
    _write(
        root / "backend" / "tests" / "test_svc.py",
        "from app.services.svc import probe_http\n\ndef test_x(client):\n    assert probe_http\n",
    )
    findings = symbol_import_findings(root / "backend")
    assert len(findings) == 1
    assert "probe_http" in findings[0]["issue"]
    assert findings[0]["severity"] == "high"


def test_contract_catches_undefined_fixture(tmp_path: Path):
    root = _backend_with_scaffold(tmp_path)
    _write(
        root / "backend" / "tests" / "test_fixtures.py",
        "def test_a(target_factory):\n    assert target_factory\n",
    )
    findings = fixture_findings(root / "backend")
    assert any("target_factory" in f["issue"] for f in findings)
    # 骨架提供的 fixture 不算缺陷
    assert not any("client" in f["issue"] for f in findings)


def test_contract_ignores_parametrize_params(tmp_path: Path):
    root = _backend_with_scaffold(tmp_path)
    _write(
        root / "backend" / "tests" / "test_param.py",
        "import pytest\n\n"
        "@pytest.mark.parametrize('value,expect', [(1, 1)])\n"
        "def test_p(value, expect, client):\n"
        "    assert value == expect\n",
    )
    assert fixture_findings(root / "backend") == []


def test_contract_catches_unknown_env_var(tmp_path: Path):
    root = _backend_with_scaffold(tmp_path)
    _write(
        root / "backend" / "tests" / "test_env.py",
        'import os\n\nos.environ["LEDGER_DATABASE_PATH"] = "/tmp/x.db"\n\n'
        "def test_ok(client):\n    assert client\n",
    )
    findings = check_contract(root)["findings"]
    assert any("LEDGER_DATABASE_PATH" in f["issue"] for f in findings)


def test_contract_flags_broken_skeleton_export(tmp_path: Path):
    root = _backend_with_scaffold(tmp_path)
    _write(
        root / "backend" / "app" / "database.py",
        "class Base:\n    pass\n",
    )
    findings = check_contract(root)["findings"]
    assert any("导出符号被破坏" in f["issue"] for f in findings)


def test_contract_flags_missing_frontend_required(tmp_path: Path):
    root = _backend_with_scaffold(tmp_path)
    (root / "frontend" / "vite.config.ts").unlink()
    findings = check_contract(root)["findings"]
    assert any(f["where"] == "frontend/vite.config.ts" for f in findings), findings


# ------------------------------------------------------------------ 骨架禁写保护


def test_persist_generated_blocks_skeleton_overwrite(tmp_path: Path):
    from mvp_team.agents.base import persist_generated, project_dir

    state = {"output_dir": str(tmp_path), "project_name": "demo"}
    root = project_dir(state)
    write_scaffold(root)

    text = (
        "```file:backend/app/config.py\n# 被乱改的配置\n```\n\n"
        "```file:backend/app/models.py\nclass Item:\n    pass\n```\n"
    )
    files, warnings = persist_generated(state, text, "backend", forbid=skeleton_paths())

    assert [f.path for f in files] == ["backend/app/models.py"]
    assert any("骨架文件受保护" in w for w in warnings)
    assert "get_settings" in (root / "backend" / "app" / "config.py").read_text(encoding="utf-8")


# ------------------------------------------------------------------ 返工闭环


def test_rework_block_attaches_file_contents(tmp_path: Path):
    from mvp_team.agents.base import project_dir, rework_block, write_text

    state = {
        "output_dir": str(tmp_path),
        "project_name": "demo",
        "qa_round": 1,
        "qa_feedback": [
            "【第 1 轮测试报告】返工\n"
            "- [high] backend/app/services/svc.py: 函数签名对不上 → 建议：对齐实现与测试"
        ],
    }
    root = project_dir(state)
    write_text(root / "backend" / "app" / "services" / "svc.py", "def probe_target():\n    return 1\n")

    block = rework_block(state, "backend")
    assert "被点名文件的当前内容" in block
    assert "def probe_target():" in block
    # 骨架保护提示也要出现，避免工程师白写被拦截
    assert "不可修改" in block


def test_rework_block_empty_without_feedback(tmp_path: Path):
    from mvp_team.agents.base import rework_block

    state = {"output_dir": str(tmp_path), "project_name": "demo", "qa_round": 0, "qa_feedback": []}
    assert rework_block(state, "backend") == ""


# --------------------------------------------------- 架构师声明清单的硬约束


def test_declared_files_block_filters_by_prefix():
    from mvp_team.agents.base import declared_files_block

    state = {
        "architecture": {
            "directory_layout": [
                "backend/app/models/bookmark.py",
                "backend/app/services/bookmarks.py：书签业务逻辑",
                "`frontend/src/pages/Home.tsx`",
                "deploy/start.sh",
            ]
        }
    }
    backend_block = declared_files_block(state, "backend/app/")
    assert "backend/app/models/bookmark.py" in backend_block
    # 「路径 + 全角冒号 + 说明」要被归一化成纯路径
    assert "- backend/app/services/bookmarks.py" in backend_block
    assert "书签业务逻辑" not in backend_block
    assert "frontend/src/pages/Home.tsx" not in backend_block
    assert "硬约束：2 个" in backend_block

    frontend_block = declared_files_block(state, "frontend/src/")
    # 反引号包裹的路径也要被识别
    assert "frontend/src/pages/Home.tsx" in frontend_block
    assert "backend/app/models/bookmark.py" not in frontend_block


def test_declared_files_block_empty_when_nothing_matches():
    from mvp_team.agents.base import declared_files_block

    assert declared_files_block({}, "backend/app/") == ""
    assert declared_files_block({"architecture": {"directory_layout": []}}, "backend/app/") == ""
    assert (
        declared_files_block({"architecture": {"directory_layout": ["frontend/src/App.tsx"]}}, "backend/app/")
        == ""
    )


# --------------------------------------------------- 产物计数（返工后不归零）


def test_count_products_survives_rework_round_writing_nothing(tmp_path: Path):
    """返工轮写了 0 个文件时，汇总不能显示成 0——要按磁盘实际内容统计。"""
    from mvp_team.cli import _count_products

    root = tmp_path / "out" / "demo"
    write_scaffold(root)
    # 模拟「第 1 轮写了文件、第 3 轮返工写了 0 个」
    _write(root / "backend/app/models/bookmark.py", "class Bookmark: ...\n")
    _write(root / "backend/app/services/bookmark_service.py", "def f(): ...\n")
    _write(root / "backend/tests/test_bookmarks.py", "def test_x():\n    assert True\n")
    _write(root / "frontend/src/pages/Home.tsx", "export default function Home() { return null }\n")

    # 关键：最后一轮的 state 清单是空的（覆盖语义导致）
    final = {
        "output_dir": str(tmp_path / "out"),
        "project_name": "demo",
        "backend_files": [],
        "frontend_files": [],
        "test_files": [],
    }
    counted = _count_products(final)
    assert counted["backend"] == 2, counted
    assert counted["tests"] == 1, counted
    assert counted["frontend"] >= 1, counted
    # 骨架文件不计入业务类别
    assert counted["backend"] < 2 + len(skeleton_paths())


def test_count_products_returns_zeros_when_nothing_on_disk(tmp_path: Path):
    from mvp_team.cli import _count_products

    counted = _count_products(
        {"output_dir": str(tmp_path / "nope"), "project_name": "x", "backend_files": []}
    )
    assert counted == {"backend": 0, "frontend": 0, "tests": 0, "deploy": 0}


# ------------------------------------------------------------------ 冒烟选路


def test_smoke_selects_safe_probe_targets():
    from mvp_team.tools.smoke import select_probe_targets

    contract = [
        {"method": "GET", "path": "/api/health"},
        {"method": "GET", "path": "/api/products"},
        {"method": "GET", "path": "/api/products/{product_id}"},
        {"method": "POST", "path": "/api/auth/login", "request": '{"username":"a","password":"b"}'},
        {"method": "POST", "path": "/api/products", "request": '{"name":"x"}'},
    ]
    gets, post = select_probe_targets(contract)

    assert "/api/products" in gets
    # 健康检查由专门的步骤处理，不重复探测
    assert "/api/health" not in gets
    # 带路径参数的接口需要真实 id，冒烟阶段跳过
    assert all("{" not in path for path in gets)
    # 登录接口不作为「写路径」样本
    assert post is not None and post["path"] == "/api/products"


def test_smoke_finds_login_spec():
    from mvp_team.tools.smoke import find_login_spec

    spec = find_login_spec(
        [{"method": "POST", "path": "/api/auth/login", "request": '{"username":"a","password":"b"}'}]
    )
    assert spec is not None and spec["path"] == "/api/auth/login"
    assert find_login_spec([]) is None
    assert find_login_spec([{"method": "GET", "path": "/api/login"}]) is None


def test_smoke_deep_finds_nested_token():
    from mvp_team.tools.smoke import _deep_find_token

    assert _deep_find_token({"data": {"access_token": "abcdefgh12345"}}) == "abcdefgh12345"
    assert _deep_find_token({"token": "short"}) == ""
    assert _deep_find_token({"items": []}) == ""
