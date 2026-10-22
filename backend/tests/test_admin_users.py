from datetime import timedelta

from app.extensions import db
from app.models import ActivityLog, Booking, OtpCode, ROLE_USER, Role, Showtime, STATUS_ACTIVE, User
from app.timeutil import iso_utc, utc_now


def create_user(email):
    user = User(
        full_name="Temporary User",
        email=email,
        role=Role.query.filter_by(name=ROLE_USER).one(),
        status=STATUS_ACTIVE,
    )
    user.set_password("Temporary@123")
    db.session.add(user)
    db.session.commit()
    return user


def test_admin_can_delete_user_without_booking_and_preserve_audit_logs(client, auth, app):
    with app.app_context():
        user = create_user("delete-me@cinevo.vn")
        user_id = user.id
        db.session.add(OtpCode(
            user_id=user_id,
            code="123456",
            expires_at=utc_now() + timedelta(minutes=5),
        ))
        activity = ActivityLog(user_id=user_id, action="TEST_USER_EVENT", detail="Preserve this log")
        db.session.add(activity)
        db.session.commit()
        activity_id = activity.id

    assert client.delete("/api/admin/users/999999", headers=auth("user")).status_code == 403
    assert client.delete("/api/admin/users/999999", headers=auth("manager")).status_code == 403

    deleted = client.delete(f"/api/admin/users/{user_id}", headers=auth("admin"))
    assert deleted.status_code == 200
    assert deleted.get_json()["id"] == user_id

    with app.app_context():
        assert db.session.get(User, user_id) is None
        assert OtpCode.query.filter_by(user_id=user_id).count() == 0
        preserved_log = db.session.get(ActivityLog, activity_id)
        assert preserved_log is not None
        assert preserved_log.user_id is None
        assert ActivityLog.query.filter_by(action="USER_DELETED", detail="delete-me@cinevo.vn").count() == 1


def test_admin_users_include_latest_login_timestamp(client, auth, app):
    with app.app_context():
        user = create_user("last-login@cinevo.vn")
        user_id = user.id
        previous_login = ActivityLog(
            user_id=user_id,
            action="LOGIN",
            detail=user.email,
            created_at=utc_now() - timedelta(days=40),
        )
        latest_login = ActivityLog(
            user_id=user_id,
            action="LOGIN",
            detail=user.email,
            created_at=utc_now() - timedelta(days=2),
        )
        expected_last_login = iso_utc(latest_login.created_at)
        db.session.add_all([previous_login, latest_login])
        db.session.commit()

    response = client.get("/api/admin/users", headers=auth("admin"))
    assert response.status_code == 200
    account = next(user for user in response.get_json() if user["id"] == user_id)
    assert account["last_login_at"] == expected_last_login


def test_admin_cannot_delete_self_privileged_accounts_or_users_with_bookings(client, auth, app):
    with app.app_context():
        target = create_user("has-booking@cinevo.vn")
        target_id = target.id
        showtime = Showtime.query.first()
        db.session.add(Booking(
            code="DELBOOKING",
            user_id=target_id,
            showtime_id=showtime.id,
        ))
        db.session.commit()
        manager_id = User.query.filter_by(email="manager@cinevo.vn").one().id
        admin_id = User.query.filter_by(email="admin@cinevo.vn").one().id

    self_delete = client.delete(f"/api/admin/users/{admin_id}", headers=auth("admin"))
    assert self_delete.status_code == 400

    booking_delete = client.delete(f"/api/admin/users/{target_id}", headers=auth("admin"))
    assert booking_delete.status_code == 409
    assert "lịch sử đặt vé" in booking_delete.get_json()["message"]

    with app.app_context():
        assert db.session.get(User, target_id) is not None
        assert db.session.get(User, manager_id) is not None


def test_admin_can_delete_only_the_two_named_demo_privileged_accounts(client, auth, app):
    with app.app_context():
        admin = User(
            full_name="Deletion Test Admin",
            email="deletion-admin@cinevo.vn",
            role=Role.query.filter_by(name="ADMIN").one(),
            status=STATUS_ACTIVE,
        )
        admin.set_password("Temporary@123")
        db.session.add(admin)
        db.session.commit()

    login = client.post(
        "/api/auth/login",
        json={"email": "deletion-admin@cinevo.vn", "password": "Temporary@123"},
    )
    deletion_auth = {"Authorization": f"Bearer {login.get_json()['token']}"}

    for email, name in (
        ("manager@cinevo.vn", "Quản lý Demo"),
        ("admin@cinevo.vn", "Admin Demo"),
    ):
        with app.app_context():
            user = User.query.filter_by(email=email).one()
            user_id = user.id
            assert user.full_name == name
            assert Booking.query.filter_by(user_id=user_id).count() == 0

        result = client.delete(f"/api/admin/users/{user_id}", headers=deletion_auth)
        assert result.status_code == 200
        assert result.get_json()["id"] == user_id

        with app.app_context():
            assert db.session.get(User, user_id) is None


def test_admin_cannot_delete_other_manager_or_admin_accounts(client, auth, app):
    with app.app_context():
        manager_role = Role.query.filter_by(name="MANAGER").one()
        manager = User(
            full_name="Real Manager",
            email="real-manager@cinevo.vn",
            role=manager_role,
            status=STATUS_ACTIVE,
        )
        manager.set_password("Temporary@123")
        db.session.add(manager)
        db.session.commit()
        manager_id = manager.id

    result = client.delete(f"/api/admin/users/{manager_id}", headers=auth("admin"))
    assert result.status_code == 400
    with app.app_context():
        assert db.session.get(User, manager_id) is not None
