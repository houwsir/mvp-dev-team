"""测试公共设施。

**这份 conftest 由工程骨架提供，是测试与实现之间的契约。**
测试代码请直接使用下面这些 fixture，不要再自己写一份 conftest，也不要重复定义同名 fixture。

可用 fixture：
* ``client``      —— 进程内共享的 ``TestClient``；首次使用时会启动应用（自动建表 + 注入种子数据）
* ``db_session``  —— 直连数据库的会话，用于准备/断言测试数据

实现约定（业务代码必须遵守，否则测试会失败）：
1. 应用入口是 ``app.main:app``；
2. 数据库连接串从环境变量 ``DATABASE_URL`` 读取（由本文件在导入 app 之前设置好）；
3. 模型必须继承 ``app.database.Base`` 并可从 ``app.models`` 导入，建表由
   ``app.database.init_db()`` 在应用启动时完成。
"""

from __future__ import annotations

import os
import shutil
import tempfile
from pathlib import Path

# ---- 必须在导入 app 之前设置测试环境 ----
# conftest.py 由 pytest 在收集测试模块之前导入，因此这里的赋值一定早于 app 的导入。
_TMP_DIR = Path(tempfile.mkdtemp(prefix="mvp-test-"))
os.environ["APP_ENV"] = "test"
os.environ["DATABASE_URL"] = f"sqlite:///{_TMP_DIR / 'test.db'}"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402


@pytest.fixture(scope="session")
def client():
    """共享 HTTP 客户端。使用 with 语句以确保 lifespan（建表/种子）被执行。"""
    from app.main import app

    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(scope="session")
def db_session():
    """直连数据库的会话，用于准备数据或校验落库结果。"""
    from app.database import SessionLocal

    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def pytest_sessionfinish(session, exitstatus):  # noqa: ARG001
    """测试结束后清理临时数据库目录。"""
    shutil.rmtree(_TMP_DIR, ignore_errors=True)
