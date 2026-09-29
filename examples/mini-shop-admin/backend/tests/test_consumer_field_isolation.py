from fastapi.testclient import TestClient


def test_internal_note_is_not_exposed_in_order_list(
    authenticated_client: TestClient,
) -> None:
    listed = authenticated_client.get(
        "/api/orders",
        params={"status": "pending_shipment"},
    )
    assert listed.status_code == 200
    order = listed.json()["items"][0]

    saved = authenticated_client.patch(
        f"/api/orders/{order['id']}/internal-note",
        json={"internal_note": "仅后台可见"},
    )
    assert saved.status_code == 200

    searched = authenticated_client.get(
        "/api/orders",
        params={"order_no": order["order_no"]},
    )
    summary = searched.json()["items"][0]

    assert "internal_note" not in summary
    assert "buyer_message" not in summary


def test_internal_note_is_not_copied_to_status_history(
    authenticated_client: TestClient,
) -> None:
    order = authenticated_client.get(
        "/api/orders",
        params={"status": "pending_shipment"},
    ).json()["items"][0]

    response = authenticated_client.patch(
        f"/api/orders/{order['id']}/internal-note",
        json={"internal_note": "不要写入状态记录"},
    )

    assert response.status_code == 200
    detail = response.json()
    assert detail["internal_note"] == "不要写入状态记录"
    assert all(
        history["event_note"] != "不要写入状态记录"
        for history in detail["status_history"]
    )
