from datetime import timedelta

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.models import AdminSession, AdminUser, utc_now
from tests.conftest import TestingSessionLocal


def test_login_and_get_current_admin(client: TestClient) -> None:
    response = client.post(
        "/api/auth/login",
        json={"username": " admin ", "password": "admin123456"},
    )

    assert response.status_code == 200
    assert response.json()["admin"] == {
        "id": 1,
        "username": "admin",
        "display_name": "商城管理员",
    }
    assert response.json()["expires_at"].endswith("Z")
    assert response.cookies.get("admin_session")

    current_admin = client.get("/api/auth/me")
    assert current_admin.status_code == 200
    assert current_admin.json()["username"] == "admin"


def test_login_rejects_invalid_password(client: TestClient) -> None:
    response = client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "incorrect"},
    )

    assert response.status_code == 401
    assert response.json()["code"] == "INVALID_CREDENTIALS"


def test_login_rejects_blank_username(client: TestClient) -> None:
    response = client.post(
        "/api/auth/login",
        json={"username": "   ", "password": "admin123456"},
    )

    assert response.status_code == 422
    assert response.json()["code"] == "VALIDATION_ERROR"


def test_disabled_account_cannot_login(client: TestClient) -> None:
    with TestingSessionLocal() as db:
        admin = db.scalar(select(AdminUser).where(AdminUser.username == "admin"))
        assert admin is not None
        admin.is_active = False
        db.commit()

    response = client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "admin123456"},
    )

    assert response.status_code == 403
    assert response.json()["code"] == "ACCOUNT_DISABLED"


def test_expired_session_is_rejected(client: TestClient) -> None:
    login = client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "admin123456"},
    )
    assert login.status_code == 200

    with TestingSessionLocal() as db:
        session = db.scalar(
            select(AdminSession).order_by(AdminSession.created_at.desc())
        )
        assert session is not None
        session.expires_at = utc_now() - timedelta(seconds=1)
        db.commit()

    response = client.get("/api/auth/me")

    assert response.status_code == 401
    assert response.json()["code"] == "SESSION_EXPIRED"


def test_logout_revokes_session_and_is_idempotent(client: TestClient) -> None:
    login = client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "admin123456"},
    )
    assert login.status_code == 200

    first_logout = client.post("/api/auth/logout")
    second_logout = client.post("/api/auth/logout")

    assert first_logout.status_code == 200
    assert first_logout.json() == {"success": True}
    assert second_logout.status_code == 200
    assert second_logout.json() == {"success": True}

    current_admin = client.get("/api/auth/me")
    assert current_admin.status_code == 401
