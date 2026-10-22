"""Dữ liệu sai, quá dài, sai kiểu phải trả 4xx (không bao giờ 500)."""
import pytest


def test_bad_json_returns_400(client):
    r = client.post("/api/auth/login", data="{khong-phai-json", content_type="application/json")
    assert r.status_code == 400 and r.get_json()["code"] == "BAD_JSON"


def test_json_array_instead_of_object_returns_400(client):
    assert client.post("/api/auth/login", json=[1, 2]).status_code == 400


@pytest.mark.parametrize("field,value", [("full_name", "A" * 5000), ("email", "x" * 500 + "@a.com"),
                                           ("phone", "abc"), ("password", "p" * 1000)])
def test_register_rejects_oversized_or_invalid_fields(client, register_payload, field, value):
    payload = {**register_payload, field: value, "confirm_password": value if field == "password" else "abc123"}
    assert client.post("/api/auth/register", json=payload).status_code == 400


def test_terms_must_be_accepted(client, register_payload):
    assert client.post("/api/auth/register", json={**register_payload, "accept_terms": False}).status_code == 400


def test_manager_movie_validation(client, auth):
    h = auth("manager")
    assert client.post("/api/manager/movies", json={"title": "T", "status": "hacked"}, headers=h).status_code == 400
    assert client.post("/api/manager/movies", json={"title": "T" * 500}, headers=h).status_code == 400
    assert client.post("/api/manager/movies", json={"title": "T", "duration_minutes": -5}, headers=h).status_code == 400
    assert client.post("/api/manager/movies", json={"title": "Phim mới", "status": "coming_soon"}, headers=h).status_code == 201


@pytest.mark.parametrize("url", ["/api/showtimes?movie_id=abc", "/api/showtimes?date=khong-phai-ngay"])
def test_bad_query_params_return_400_not_500(client, url):
    assert client.get(url).status_code == 400
