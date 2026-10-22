"""Phân quyền backend: không tin frontend."""
import jwt
import pytest

ENDPOINTS = [  # (url, anon, user, manager, admin)
    ("/api/admin/users", 401, 403, 403, 200),
    ("/api/admin/dashboard", 401, 403, 403, 200),
    ("/api/admin/transactions", 401, 403, 403, 200),
    ("/api/manager/dashboard", 401, 403, 200, 200),
    ("/api/manager/bookings", 401, 403, 200, 200),
    ("/api/bookings/my", 401, 200, 200, 200),
]


@pytest.mark.parametrize("url,anon,user,manager,admin", ENDPOINTS)
def test_role_matrix(client, auth, url, anon, user, manager, admin):
    for role, expected in ((None, anon), ("user", user), ("manager", manager), ("admin", admin)):
        assert client.get(url, headers=auth(role)).status_code == expected, (url, role)


def test_manager_cannot_create_manager_or_lock_users(client, auth):
    assert client.post("/api/admin/managers", json={}, headers=auth("manager")).status_code == 403
    assert client.patch("/api/admin/users/1/status", json={"status": "LOCKED"}, headers=auth("manager")).status_code == 403


def test_forged_tokens_rejected(client, app):
    forged = [jwt.encode({"sub": "3", "role": "ADMIN"}, key="", algorithm="none"),
              jwt.encode({"sub": "3", "role": "ADMIN"}, "sai-khoa", algorithm="HS256"),
              jwt.encode({"sub": "3", "role": "ADMIN"}, "dev-secret-change-me", algorithm="HS256"),  # khóa mặc định cũ
              "abc.def.ghi", ""]
    for t in forged:
        assert client.get("/api/admin/users", headers={"Authorization": f"Bearer {t}"}).status_code == 401


def test_role_in_token_is_not_trusted_over_database(client, app, auth):
    """Token USER bị sửa role thành ADMIN (ký đúng khóa) vẫn không có quyền vì backend đọc role từ DB."""
    token = jwt.encode({"sub": "1", "role": "ADMIN"}, app.config["SECRET_KEY"], algorithm="HS256")
    assert client.get("/api/admin/users", headers={"Authorization": f"Bearer {token}"}).status_code == 403


def test_expired_token_rejected(client, app):
    token = jwt.encode({"sub": "3", "role": "ADMIN", "exp": 1}, app.config["SECRET_KEY"], algorithm="HS256")
    assert client.get("/api/admin/users", headers={"Authorization": f"Bearer {token}"}).status_code == 401


def test_admin_cannot_lock_self(client, auth):
    me = client.get("/api/auth/me", headers=auth("admin")).get_json()["user"]["id"]
    assert client.patch(f"/api/admin/users/{me}/status", json={"status": "LOCKED"}, headers=auth("admin")).status_code == 400
