import os
from collections.abc import Generator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker

TEST_DB = Path(__file__).with_name("test.db").resolve()

os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB.as_posix()}"
os.environ["SEED_ADMIN_USERNAME"] = "admin"
os.environ["SEED_ADMIN_PASSWORD"] = "admin123456"
os.environ["SESSION_COOKIE_SECURE"] = "false"

from app.database import get_db
from app.main import app
from app.models import Base
from app.seed import seed_database

test_engine = create_engine(
    f"sqlite:///{TEST_DB.as_posix()}",
    connect_args={"check_same_thread": False},
)
TestingSessionLocal = sessionmaker(
    bind=test_engine,
    class_=Session,
    expire_on_commit=False,
)


@event.listens_for(test_engine, "connect")
def enable_sqlite_constraints(dbapi_connection, connection_record) -> None:
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


def override_get_db() -> Generator[Session, None, None]:
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(autouse=True)
def reset_database() -> Generator[None, None, None]:
    Base.metadata.drop_all(test_engine)
    Base.metadata.create_all(test_engine)
    with TestingSessionLocal() as db:
        seed_database(db)

    yield

    Base.metadata.drop_all(test_engine)
    if TEST_DB.exists():
        TEST_DB.unlink()


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def admin_credentials() -> dict[str, str]:
    return {"username": "admin", "password": "admin123456"}


@pytest.fixture
def authenticated_client(client: TestClient) -> TestClient:
    response = client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "admin123456"},
    )
    assert response.status_code == 200, response.text
    assert client.cookies.get("admin_session")
    return client


@pytest.fixture
def product_payload() -> dict:
    return {
        "name": "自动化测试商品",
        "main_image_url": "https://example.com/product.jpg",
        "price": "99.90",
        "stock": 8,
        "description": "由 pytest 创建的商品",
    }
