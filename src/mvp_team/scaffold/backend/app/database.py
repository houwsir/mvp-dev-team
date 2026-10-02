"""数据库引擎、会话与声明基类。

工程骨架固定了这份「数据访问契约」，业务代码请按下面的方式使用：

* 定义模型：``from app.database import Base`` 后继承 ``Base``；
* 取会话：``Depends(get_db)``（FastAPI 路由）或 ``SessionLocal()``（脚本/后台任务）；
* 建表：应用启动时由 ``init_db()`` 统一完成，业务代码不要再自行 create_all。
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import settings

_url = settings.database_url

# SQLite 文件库：确保父目录存在，否则首次连接会失败
if _url.startswith("sqlite:///") and ":memory:" not in _url:
    _db_file = Path(_url[len("sqlite:///") :])
    if _db_file.parent and str(_db_file.parent) not in {"", "."}:
        _db_file.parent.mkdir(parents=True, exist_ok=True)

_connect_args = {"check_same_thread": False} if _url.startswith("sqlite") else {}

engine = create_engine(_url, connect_args=_connect_args, future=True)

# 注意：这里使用 SQLAlchemy 默认的 expire_on_commit=True。
# commit 后对象属性会失效并在下次访问时重新加载，可以避免「预加载的关联对象
# 在数据变更后仍读到旧值」这一整类难以排查的缺陷。
SessionLocal = sessionmaker(bind=engine, autoflush=False, future=True)


class Base(DeclarativeBase):
    """所有 ORM 模型的基类。"""


def get_db() -> Iterator[Session]:
    """FastAPI 依赖：为每个请求提供独立会话。"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """建表。调用前必须确保所有模型模块已被导入（否则表不会被注册）。"""
    from app import models  # noqa: F401  导入以触发模型注册

    Base.metadata.create_all(bind=engine)
