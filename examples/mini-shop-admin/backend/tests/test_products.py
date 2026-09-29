from fastapi.testclient import TestClient


def create_product(
    client: TestClient,
    payload: dict,
) -> dict:
    response = client.post("/api/products", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


def test_create_and_get_product(
    authenticated_client: TestClient,
    product_payload: dict,
) -> None:
    created = create_product(authenticated_client, product_payload)

    assert created["name"] == product_payload["name"]
    assert created["price"] == "99.90"
    assert created["stock"] == 8
    assert created["status"] == "inactive"

    response = authenticated_client.get(f"/api/products/{created['id']}")
    assert response.status_code == 200
    assert response.json() == created


def test_update_product_persists_changes(
    authenticated_client: TestClient,
    product_payload: dict,
) -> None:
    created = create_product(authenticated_client, product_payload)
    updated_payload = {
        **product_payload,
        "name": "编辑后的商品",
        "price": "128.50",
        "stock": 15,
        "description": "编辑后的描述",
    }

    update_response = authenticated_client.put(
        f"/api/products/{created['id']}",
        json=updated_payload,
    )

    assert update_response.status_code == 200
    assert update_response.json()["name"] == "编辑后的商品"
    assert update_response.json()["price"] == "128.50"

    detail = authenticated_client.get(f"/api/products/{created['id']}")
    assert detail.status_code == 200
    assert detail.json()["description"] == "编辑后的描述"
    assert detail.json()["stock"] == 15


def test_product_search_status_filter_and_pagination(
    authenticated_client: TestClient,
    product_payload: dict,
) -> None:
    created = create_product(
        authenticated_client,
        {**product_payload, "name": "唯一搜索词测试商品"},
    )

    activated = authenticated_client.patch(
        f"/api/products/{created['id']}/status",
        json={"status": "active"},
    )
    assert activated.status_code == 200

    response = authenticated_client.get(
        "/api/products",
        params={
            "page": 1,
            "page_size": 20,
            "keyword": "  唯一搜索词  ",
            "status": "active",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["page"] == 1
    assert body["page_size"] == 20
    assert body["total"] == 1
    assert body["total_pages"] == 1
    assert body["items"][0]["id"] == created["id"]


def test_update_stock_to_zero_automatically_deactivates_product(
    authenticated_client: TestClient,
    product_payload: dict,
) -> None:
    created = create_product(authenticated_client, product_payload)
    activate = authenticated_client.patch(
        f"/api/products/{created['id']}/status",
        json={"status": "active"},
    )
    assert activate.status_code == 200
    assert activate.json()["status"] == "active"

    response = authenticated_client.patch(
        f"/api/products/{created['id']}/stock",
        json={"stock": 0},
    )

    assert response.status_code == 200
    assert response.json()["stock"] == 0
    assert response.json()["status"] == "inactive"


def test_zero_stock_product_cannot_be_activated(
    authenticated_client: TestClient,
    product_payload: dict,
) -> None:
    created = create_product(
        authenticated_client,
        {**product_payload, "stock": 0},
    )

    response = authenticated_client.patch(
        f"/api/products/{created['id']}/status",
        json={"status": "active"},
    )

    assert response.status_code == 409
    assert response.json()["code"] == "PRODUCT_OUT_OF_STOCK"


def test_create_product_rejects_invalid_fields(
    authenticated_client: TestClient,
    product_payload: dict,
) -> None:
    invalid_payloads = [
        {**product_payload, "name": "   "},
        {**product_payload, "main_image_url": ""},
        {**product_payload, "main_image_url": "ftp://example.com/a.jpg"},
        {**product_payload, "price": "0"},
        {**product_payload, "price": "1.001"},
        {**product_payload, "stock": -1},
    ]

    for payload in invalid_payloads:
        response = authenticated_client.post("/api/products", json=payload)
        assert response.status_code == 422, (payload, response.text)
        assert response.json()["code"] == "VALIDATION_ERROR"


def test_product_rejects_invalid_pagination_and_status(
    authenticated_client: TestClient,
) -> None:
    invalid_requests = [
        {"page": 0},
        {"page_size": 10},
        {"status": "archived"},
    ]

    for params in invalid_requests:
        response = authenticated_client.get("/api/products", params=params)
        assert response.status_code == 422, (params, response.text)
        assert response.json()["code"] == "VALIDATION_ERROR"


def test_product_not_found_and_invalid_id(
    authenticated_client: TestClient,
) -> None:
    missing = authenticated_client.get("/api/products/999999")
    invalid = authenticated_client.get("/api/products/0")

    assert missing.status_code == 404
    assert missing.json()["code"] == "PRODUCT_NOT_FOUND"
    assert invalid.status_code == 422
    assert invalid.json()["code"] == "VALIDATION_ERROR"
