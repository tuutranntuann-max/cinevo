"""Cờ tính năng: AI tắt mặc định (theo lộ trình), bật được khi cần và vẫn an toàn."""
import pytest


AI_URLS = ["/api/ai/recommend-movies", "/api/ai/recommend-seats?showtime_id=1", "/api/ai/chat"]


def test_config_reports_ai_off_by_default(client):
    assert client.get("/api/config").get_json() == {"features": {"ai": False}}


@pytest.mark.parametrize("url", AI_URLS)
def test_ai_endpoints_do_not_exist_when_disabled(client, url):
    assert client.get(url).status_code == 404
    assert client.post(url, json={"message": "xin chào"}).status_code == 404


def test_admin_ai_settings_hidden_when_disabled(client, auth):
    assert client.get("/api/admin/ai-settings", headers=auth("admin")).status_code == 404
    assert client.get("/api/admin/ai-settings", headers=auth("user")).status_code == 403   # vẫn kiểm quyền trước


def test_core_flow_unaffected_by_ai_flag(client):
    assert client.get("/api/movies").status_code == 200
    assert client.get("/api/showtimes").status_code == 200


# ---- khi được phép bật lại ----
def test_ai_works_when_enabled(ai_client):
    assert ai_client.get("/api/config").get_json()["features"]["ai"] is True
    assert ai_client.get("/api/ai/recommend-movies").status_code == 200
    assert ai_client.post("/api/ai/chat", json={"message": "đặt vé thế nào"}).status_code == 200


def test_ai_input_validation_when_enabled(ai_client):
    assert ai_client.post("/api/ai/chat", json={"message": "x" * 600}).status_code == 400
    assert ai_client.get("/api/ai/recommend-seats?showtime_id=x").status_code == 400
    assert ai_client.get("/api/ai/recommend-movies?limit=-1").status_code == 400


def test_admin_ai_settings_available_when_enabled(ai_client):
    token = ai_client.post("/api/auth/login", json={"email": "admin@cinevo.vn", "password": "Admin@123"}).get_json()["token"]
    assert ai_client.get("/api/admin/ai-settings", headers={"Authorization": f"Bearer {token}"}).status_code == 200
