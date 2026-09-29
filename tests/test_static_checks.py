"""确定性静态体检的行为测试。

这些用例是为了「防误报」而写的——检查器一旦误报，质量门就会把好代码打回返工，
所以每一条曾经踩过的坑都固化成一个用例。
"""

from __future__ import annotations

from pathlib import Path

from mvp_team.tools.static_checks import (
    _is_deploy_stage,
    _layout_path,
    _norm,
    _split_routes,
    backend_routes,
    check_project,
    python_local_import_errors,
)


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


# ------------------------------------------------------------------ 路径归一化


def test_norm_strips_query_and_hash():
    assert _norm("/orders?page=1&q=x") == "/orders"
    assert _norm("/dashboard#top") == "/dashboard"


def test_norm_path_params():
    assert _norm("/products/{product_id}") == "/products/<>"
    assert _norm("/products/${id}") == "/products/<>"
    assert _norm("/orders/{oid}/ship") == "/orders/<>/ship"


def test_norm_drops_trailing_template_concat():
    # `/orders${qs}` 是「路径 + 查询串拼接」，不是路径参数
    assert _norm("/orders${qs}") == "/orders"
    assert _norm('/orders${qs ? `?${page}` : ""}') == "/orders"
    assert _norm("/products)}") == "/products"
    assert _norm("/") == "/"


def test_norm_colon_params_match_braces_params():
    assert _norm("/products/:product_id/edit") == "/products/<>/edit"
    assert _norm("/products/{product_id}/edit") == "/products/<>/edit"


def test_norm_is_idempotent():
    """归一化结果再次归一化必须保持不变，否则二次处理会造出 /products//edit 这种假路径。"""
    for raw in ("/products/:id/edit", "/orders/${oid}", "/a?b=1", "/x/y"):
        once = _norm(raw)
        assert _norm(once) == once, raw


def test_split_routes_handles_multiple_routes_in_one_field():
    assert _split_routes("/products/new 和 /products/:id/edit") == ["/products/new", "/products/<>/edit"]
    assert _split_routes("/dashboard") == ["/dashboard"]
    assert _split_routes("") == []


# ------------------------------------------------------------------ 交付清单解析


def test_layout_path_splits_on_fullwidth_colon():
    assert _layout_path("backend/app/main.py：创建 FastAPI 应用") == "backend/app/main.py"
    assert _layout_path("app/core/errors.py：业务异常、错误处理") == "app/core/errors.py"


def test_layout_path_handles_plain_and_dashed_forms():
    assert _layout_path("- `frontend/src/main.tsx` 前端入口") == "frontend/src/main.tsx"
    assert _layout_path("docs/PRD.md - 产品需求文档") == "docs/PRD.md"


# ------------------------------------------------------------------ 命名空间包


def test_namespace_package_import_is_not_an_error(tmp_path: Path):
    """Python 3 没有 __init__.py 也能导入（命名空间包），不能误报。"""
    backend = tmp_path / "backend"
    _write(backend / "app" / "__init__.py", "")
    _write(backend / "app" / "api" / "routes" / "products.py", "router = 1\n")
    _write(backend / "app" / "services" / "product.py", "def f(): ...\n")
    _write(
        backend / "app" / "api" / "router.py",
        "from app.api.routes import products\nfrom app.services.product import f\n",
    )
    assert python_local_import_errors(backend) == []


def test_missing_module_import_is_reported(tmp_path: Path):
    backend = tmp_path / "backend"
    _write(backend / "app" / "__init__.py", "")
    _write(backend / "app" / "main.py", "from app.nowhere import thing\n")
    errors = python_local_import_errors(backend)
    assert errors and "app.nowhere" in errors[0]


# ------------------------------------------------------------------ 路由提取


def test_backend_routes_isolates_router_prefix_per_file(tmp_path: Path):
    """各模块的路由变量常同名 router，前缀不能互相覆盖。"""
    backend = tmp_path / "backend"
    _write(backend / "app" / "__init__.py", "")
    _write(backend / "app" / "main.py", "app.include_router(products.router, prefix='/api')\n")
    _write(
        backend / "app" / "api" / "products.py",
        'from fastapi import APIRouter\nrouter = APIRouter(prefix="/products")\n\n@router.get("")\ndef a(): ...\n\n@router.get("/{pid}")\ndef b(): ...\n',
    )
    _write(
        backend / "app" / "api" / "orders.py",
        'from fastapi import APIRouter\nrouter = APIRouter(prefix="/orders")\n\n@router.get("")\ndef c(): ...\n',
    )
    routes = backend_routes(backend)
    assert "GET /products" in routes
    assert "GET /orders" in routes
    assert "GET /products/{pid}" in routes


def test_backend_routes_handles_multiline_decorator(tmp_path: Path):
    backend = tmp_path / "backend"
    _write(backend / "app" / "__init__.py", "")
    _write(
        backend / "app" / "api" / "x.py",
        'from fastapi import APIRouter\nrouter = APIRouter(prefix="/x")\n\n@router.get(\n    "/y",\n)\ndef f(): ...\n',
    )
    assert "GET /x/y" in backend_routes(backend)


# ------------------------------------------------------------------ 部署期文件


def test_deploy_stage_files_excluded_from_quality_gate():
    for name in ("docker-compose.yml", "deploy/start.sh", "Makefile", "README.md", ".env.example", "frontend/nginx.conf"):
        assert _is_deploy_stage(name), name
    assert not _is_deploy_stage("backend/app/main.py")


def test_check_project_clean_on_consistent_skeleton(tmp_path: Path):
    root = tmp_path / "demo"
    _write(root / "backend" / "app" / "__init__.py", "")
    _write(
        root / "backend" / "app" / "main.py",
        "from fastapi import FastAPI\napp = FastAPI()\n\n@app.get('/api/health')\ndef h(): ...\n",
    )
    _write(root / "backend" / "requirements.txt", "fastapi\n")
    _write(
        root / "frontend" / "package.json",
        '{"scripts": {"dev": "vite", "build": "vite build"},'
        ' "dependencies": {"react": "^18", "react-dom": "^18"},'
        ' "devDependencies": {"vite": "^5", "typescript": "^5"}}',
    )
    _write(
        root / "frontend" / "src" / "App.tsx",
        "const routes = [{ path: '/dashboard', element: 1 }];\n"
        "fetch('/api/health');\n",
    )
    prd = {"pages": [{"route": "/dashboard"}]}
    arch = {"api_contract": [{"path": "/api/health"}], "directory_layout": ["backend/app/main.py：入口"]}
    result = check_project(root, prd, arch)
    assert result["findings"] == []
