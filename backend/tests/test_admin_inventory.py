import pytest


@pytest.mark.parametrize("path", ["/api/admin/foods", "/api/admin/products"])
def test_inventory_endpoints_are_admin_only(client, auth, path):
    assert client.get(path).status_code == 401
    assert client.get(path, headers=auth("user")).status_code == 403
    assert client.get(path, headers=auth("manager")).status_code == 403
    assert client.get(path, headers=auth("admin")).status_code == 200


def test_admin_can_manage_foods(client, auth):
    headers = auth("admin")
    response = client.post("/api/admin/foods", headers=headers, json={
        "name": "Combo test", "description": "Bắp và nước", "price": 85000,
        "is_combo": True, "available": True,
    })
    assert response.status_code == 201
    food_id = response.get_json()["id"]
    assert client.put(f"/api/admin/foods/{food_id}", headers=headers,
                      json={"available": False}).get_json()["available"] is False
    assert any(food["id"] == food_id for food in client.get("/api/admin/foods", headers=headers).get_json())


def test_admin_can_manage_product_inventory(client, auth):
    headers = auth("admin")
    response = client.post("/api/admin/products", headers=headers, json={
        "name": "Áo Cinevo", "category": "Quà lưu niệm", "description": "Áo phiên bản giới hạn",
        "price": 250000, "stock_quantity": 12, "active": True,
    })
    assert response.status_code == 201
    product_id = response.get_json()["id"]
    update = client.put(f"/api/admin/products/{product_id}", headers=headers,
                        json={"stock_quantity": 8})
    assert update.status_code == 200
    assert update.get_json()["stock_quantity"] == 8
    assert client.put(f"/api/admin/products/{product_id}", headers=auth("manager"),
                      json={"stock_quantity": 0}).status_code == 403


def test_inventory_rejects_invalid_values(client, auth):
    headers = auth("admin")
    response = client.post("/api/admin/products", headers=headers, json={
        "name": "Sản phẩm lỗi", "category": "Khác", "price": -1,
        "stock_quantity": 2, "active": True,
    })
    assert response.status_code == 400
