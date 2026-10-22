from app.models import StaffApplication, StaffPasswordResetRequest, User
from app.extensions import db


def application_payload(**updates):
    return {
        "full_name": "Nguyen Thi Mai",
        "email": "mai.staff@example.com",
        "phone": "0912345678",
        "citizen_id": "012345678901",
        "address": "12 Nguyen Trai, Ha Noi",
        "gender": "Nữ",
        "occupation": "Sinh viên",
        "requested_role": "EMPLOYEE",
        "accept_privacy": True,
        **updates,
    }


def test_staff_application_requires_admin_approval_and_one_time_invite(client, auth, app):
    endpoint = "/api/staff-accounts/applications"
    assert client.get("/api/staff-accounts/applications").status_code == 401
    assert client.get(
        "/api/staff-accounts/applications",
        headers=auth("manager"),
    ).status_code == 403
    created = client.post(endpoint, json=application_payload())
    assert created.status_code == 201

    application_id = created.get_json()["application_id"]
    assert client.post(
        f"/api/staff-accounts/applications/{application_id}/approve",
        headers=auth("manager"),
        json={"role": "EMPLOYEE"},
    ).status_code == 403

    listed = client.get("/api/staff-accounts/applications", headers=auth("admin"))
    assert listed.status_code == 200
    application = listed.get_json()["applications"][0]
    assert application["citizen_id"] == "012345678901"
    assert "invite_hash" not in application
    with app.app_context():
        stored = db.session.get(StaffApplication, application_id)
        assert "012345678901" not in stored.citizen_id_ciphertext
        assert "12 Nguyen Trai" not in stored.address_ciphertext
        assert stored.citizen_id == "012345678901"
        assert stored.address == "12 Nguyen Trai, Ha Noi"

    approved = client.post(
        f"/api/staff-accounts/applications/{application_id}/approve",
        headers=auth("admin"),
        json={"role": "EMPLOYEE"},
    )
    assert approved.status_code == 200
    code = approved.get_json()["invite_code"]
    assert len(code) == 32
    assert client.get("/api/staff-accounts/applications", headers=auth("admin")).get_json()[
        "applications"
    ][0]["status"] == "INVITED"

    invalid = client.post("/api/staff-accounts/complete", json={
        "email": "mai.staff@example.com",
        "invite_code": "A" * 32,
        "password": "StaffPass123",
        "confirm_password": "StaffPass123",
    })
    assert invalid.status_code == 400

    completed = client.post("/api/staff-accounts/complete", json={
        "email": "mai.staff@example.com",
        "invite_code": code,
        "password": "StaffPass123",
        "confirm_password": "StaffPass123",
    })
    assert completed.status_code == 201
    assert completed.get_json()["user"]["role"] == "EMPLOYEE"
    assert client.post("/api/staff-accounts/complete", json={
        "email": "mai.staff@example.com",
        "invite_code": code,
        "password": "StaffPass123",
        "confirm_password": "StaffPass123",
    }).status_code == 400

    login = client.post("/api/auth/login", json={
        "email": "mai.staff@example.com",
        "password": "StaffPass123",
    })
    assert login.status_code == 200
    assert login.get_json()["user"]["role"] == "EMPLOYEE"
    assert client.get("/api/manager/dashboard", headers={
        "Authorization": f"Bearer {login.get_json()['token']}",
    }).status_code == 200
    assert any(
        staff["email"] == "mai.staff@example.com"
        for staff in client.get("/api/admin/managers", headers=auth("admin")).get_json()
    )
    assert client.post("/api/admin/managers", headers=auth("admin"), json={}).status_code == 410


def test_staff_application_validates_required_personal_details_and_role(client, auth):
    invalid_id = client.post(
        "/api/staff-accounts/applications",
        json=application_payload(citizen_id="123"),
    )
    assert invalid_id.status_code == 400
    invalid_role = client.post(
        "/api/staff-accounts/applications",
        json=application_payload(requested_role="ADMIN"),
    )
    assert invalid_role.status_code == 400
    no_consent = client.post(
        "/api/staff-accounts/applications",
        json=application_payload(accept_privacy=False),
    )
    assert no_consent.status_code == 400

    submitted = client.post(
        "/api/staff-accounts/applications",
        headers=auth("user"),
        json=application_payload(),
    )
    assert submitted.status_code == 201
    application_id = submitted.get_json()["application_id"]
    rejected = client.post(
        f"/api/staff-accounts/applications/{application_id}/reject",
        headers=auth("admin"),
        json={},
    )
    assert rejected.status_code == 200
    resubmitted = client.post(
        "/api/staff-accounts/applications",
        json=application_payload(occupation="Công nhân"),
    )
    assert resubmitted.status_code == 201


def test_admin_can_reissue_invite_and_old_code_stops_working(client, auth):
    application_id = client.post(
        "/api/staff-accounts/applications",
        json=application_payload(email="replace-code@example.com"),
    ).get_json()["application_id"]
    first_code = client.post(
        f"/api/staff-accounts/applications/{application_id}/approve",
        headers=auth("admin"),
        json={},
    ).get_json()["invite_code"]
    second_code = client.post(
        f"/api/staff-accounts/applications/{application_id}/invite",
        headers=auth("admin"),
        json={},
    ).get_json()["invite_code"]
    assert second_code != first_code

    old_code = client.post("/api/staff-accounts/complete", json={
        "email": "replace-code@example.com",
        "invite_code": first_code,
        "password": "StaffPass123",
        "confirm_password": "StaffPass123",
    })
    assert old_code.status_code == 400
    activated = client.post("/api/staff-accounts/complete", json={
        "email": "replace-code@example.com",
        "invite_code": second_code,
        "password": "StaffPass123",
        "confirm_password": "StaffPass123",
    })
    assert activated.status_code == 201


def test_password_reset_request_does_not_reveal_account_existence_and_is_admin_only(
    client, auth, monkeypatch
):
    from app.routes import staff_accounts

    generated_codes = iter((1, 2))
    monkeypatch.setattr(
        staff_accounts.secrets,
        "randbelow",
        lambda _limit: next(generated_codes),
    )
    staff_headers = auth("manager")
    old_token = staff_headers["Authorization"]
    staff_email = "manager@cinevo.vn"
    known = client.post("/api/staff-accounts/password-resets", json={"email": staff_email})
    unknown = client.post("/api/staff-accounts/password-resets", json={"email": "missing@example.com"})
    customer = client.post("/api/staff-accounts/password-resets", json={"email": "user@cinevo.vn"})

    assert known.status_code == unknown.status_code == customer.status_code == 202
    assert known.get_json() == unknown.get_json() == customer.get_json()
    assert client.get("/api/staff-accounts/password-resets").status_code == 401
    assert client.get(
        "/api/staff-accounts/password-resets",
        headers=auth("manager"),
    ).status_code == 403
    assert client.get(
        "/api/staff-accounts/password-resets/count",
        headers=auth("admin"),
    ).get_json()["pending_count"] == 1

    with client.application.app_context():
        assert StaffPasswordResetRequest.query.count() == 1

    requests = client.get(
        "/api/staff-accounts/password-resets",
        headers=auth("admin"),
    ).get_json()["requests"]
    assert len(requests) == 1
    assert requests[0]["email"] == staff_email
    assert client.post(
        f"/api/staff-accounts/password-resets/{requests[0]['id']}/issue",
        headers=auth("manager"),
        json={},
    ).status_code == 403

    issued = client.post(
        f"/api/staff-accounts/password-resets/{requests[0]['id']}/issue",
        headers=auth("admin"),
        json={},
    )
    assert issued.status_code == 200
    code = issued.get_json()["reset_code"]
    assert len(code) == 8 and code.isdigit()
    assert "code_hash" not in issued.get_json()["request"]
    renewed = client.post(
        f"/api/staff-accounts/password-resets/{requests[0]['id']}/issue",
        headers=auth("admin"),
        json={},
    )
    replacement_code = renewed.get_json()["reset_code"]
    assert replacement_code == "00000002"

    invalid = client.post("/api/staff-accounts/password-resets/complete", json={
        "email": staff_email,
        "reset_code": code,
        "password": "NewManagerPass123",
        "confirm_password": "NewManagerPass123",
    })
    assert invalid.status_code == 400

    completed = client.post("/api/staff-accounts/password-resets/complete", json={
        "email": staff_email,
        "reset_code": replacement_code,
        "password": "NewManagerPass123",
        "confirm_password": "NewManagerPass123",
    })
    assert completed.status_code == 200
    assert client.post("/api/staff-accounts/password-resets/complete", json={
        "email": staff_email,
        "reset_code": code,
        "password": "AnotherPass123",
        "confirm_password": "AnotherPass123",
    }).status_code == 400
    assert client.get("/api/manager/dashboard", headers={
        "Authorization": old_token,
    }).status_code == 401
    assert client.post("/api/auth/login", json={
        "email": staff_email,
        "password": "Manager@123",
    }).status_code == 401
    assert client.post("/api/auth/login", json={
        "email": staff_email,
        "password": "NewManagerPass123",
    }).status_code == 200
    with client.application.app_context():
        assert User.query.filter_by(email=staff_email).one().auth_version == 1
