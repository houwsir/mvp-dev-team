from fastapi.testclient import TestClient


def test_health_check_does_not_require_authentication(client: TestClient) -> None:
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_protected_resource_requires_authentication(client: TestClient) -> None:
    response = client.get("/api/products")

    assert response.status_code == 401
    assert response.json() == {
        "detail": "请先登录",
        "code": "AUTH_REQUIRED",
    }
