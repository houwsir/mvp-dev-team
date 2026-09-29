from fastapi.testclient import TestClient


def find_order(client: TestClient, status: str) -> dict:
    response = client.get("/api/orders", params={"status": status})
    assert response.status_code == 200, response.text
    items = response.json()["items"]
    assert items, f"No seeded order found with status {status}"
    return items[0]


def test_order_exact_search_pagination_and_detail(
    authenticated_client: TestClient,
) -> None:
    order = find_order(authenticated_client, "pending_shipment")

    search = authenticated_client.get(
        "/api/orders",
        params={
            "page": 1,
            "page_size": 20,
            "order_no": f"  {order['order_no']}  ",
            "status": "pending_shipment",
        },
    )

    assert search.status_code == 200
    assert search.json()["total"] == 1
    assert search.json()["items"][0]["order_no"] == order["order_no"]

    detail = authenticated_client.get(f"/api/orders/{order['id']}")
    assert detail.status_code == 200
    body = detail.json()
    assert body["items"]
    assert body["receiver"]["name"]
    assert body["status_history"]


def test_order_number_search_is_exact(
    authenticated_client: TestClient,
) -> None:
    order = find_order(authenticated_client, "pending_payment")

    response = authenticated_client.get(
        "/api/orders",
        params={"order_no": order["order_no"][:-1]},
    )

    assert response.status_code == 200
    assert response.json()["items"] == []
    assert response.json()["total"] == 0
    assert response.json()["total_pages"] == 0


def test_ship_pending_order(
    authenticated_client: TestClient,
) -> None:
    order = find_order(authenticated_client, "pending_shipment")

    response = authenticated_client.post(
        f"/api/orders/{order['id']}/ship",
        json={
            "logistics_company": " 顺丰速运 ",
            "tracking_no": " SF123456789 ",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "shipped"
    assert body["shipment"]["logistics_company"] == "顺丰速运"
    assert body["shipment"]["tracking_no"] == "SF123456789"
    assert body["status_history"][-1]["event_type"] == "shipped"
    assert body["status_history"][-1]["operator_type"] == "admin"
    assert body["status_history"][-1]["created_at"].endswith("Z")


def test_shipping_requires_both_logistics_fields(
    authenticated_client: TestClient,
) -> None:
    order = find_order(authenticated_client, "pending_shipment")
    invalid_payloads = [
        {"logistics_company": "", "tracking_no": "SF123"},
        {"logistics_company": "顺丰速运", "tracking_no": "   "},
        {"logistics_company": "顺丰速运"},
        {"tracking_no": "SF123"},
    ]

    for payload in invalid_payloads:
        response = authenticated_client.post(
            f"/api/orders/{order['id']}/ship",
            json=payload,
        )
        assert response.status_code == 422, (payload, response.text)
        assert response.json()["code"] == "VALIDATION_ERROR"

    detail = authenticated_client.get(f"/api/orders/{order['id']}").json()
    assert detail["status"] == "pending_shipment"
    assert detail["shipment"] is None


def test_repeated_shipping_conflicts(
    authenticated_client: TestClient,
) -> None:
    order = find_order(authenticated_client, "pending_shipment")
    payload = {
        "logistics_company": "顺丰速运",
        "tracking_no": "SF0001",
    }

    first = authenticated_client.post(
        f"/api/orders/{order['id']}/ship",
        json=payload,
    )
    second = authenticated_client.post(
        f"/api/orders/{order['id']}/ship",
        json=payload,
    )

    assert first.status_code == 200
    assert second.status_code == 409
    assert second.json()["code"] in {
        "ORDER_STATUS_CONFLICT",
        "SHIPMENT_ALREADY_EXISTS",
    }


def test_cancel_pending_payment_order(
    authenticated_client: TestClient,
) -> None:
    order = find_order(authenticated_client, "pending_payment")

    response = authenticated_client.post(
        f"/api/orders/{order['id']}/cancel",
        json={},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "cancelled"
    assert response.json()["status_history"][-1]["event_type"] == "cancelled"
    assert response.json()["status_history"][-1]["operator_type"] == "admin"


def test_completed_order_cannot_be_cancelled(
    authenticated_client: TestClient,
) -> None:
    order = find_order(authenticated_client, "completed")

    response = authenticated_client.post(
        f"/api/orders/{order['id']}/cancel",
        json={},
    )

    assert response.status_code == 409
    assert response.json()["code"] == "ORDER_STATUS_CONFLICT"


def test_internal_note_persists_and_can_be_cleared(
    authenticated_client: TestClient,
) -> None:
    order = find_order(authenticated_client, "pending_shipment")
    note_url = f"/api/orders/{order['id']}/internal-note"

    saved = authenticated_client.patch(
        note_url,
        json={"internal_note": "核对地址后再发货"},
    )
    assert saved.status_code == 200
    assert saved.json()["internal_note"] == "核对地址后再发货"

    detail = authenticated_client.get(f"/api/orders/{order['id']}")
    assert detail.status_code == 200
    assert detail.json()["internal_note"] == "核对地址后再发货"

    cleared = authenticated_client.patch(
        note_url,
        json={"internal_note": ""},
    )
    assert cleared.status_code == 200
    assert cleared.json()["internal_note"] is None


def test_internal_note_rejects_more_than_1000_characters(
    authenticated_client: TestClient,
) -> None:
    order = find_order(authenticated_client, "pending_shipment")

    response = authenticated_client.patch(
        f"/api/orders/{order['id']}/internal-note",
        json={"internal_note": "x" * 1001},
    )

    assert response.status_code == 422
    assert response.json()["code"] == "VALIDATION_ERROR"


def test_order_rejects_invalid_query_and_id(
    authenticated_client: TestClient,
) -> None:
    invalid_queries = [
        {"page": 0},
        {"page_size": 10},
        {"status": "refunded"},
    ]

    for params in invalid_queries:
        response = authenticated_client.get("/api/orders", params=params)
        assert response.status_code == 422, (params, response.text)
        assert response.json()["code"] == "VALIDATION_ERROR"

    invalid_id = authenticated_client.get("/api/orders/0")
    missing = authenticated_client.get("/api/orders/999999")

    assert invalid_id.status_code == 422
    assert invalid_id.json()["code"] == "VALIDATION_ERROR"
    assert missing.status_code == 404
    assert missing.json()["code"] == "ORDER_NOT_FOUND"
