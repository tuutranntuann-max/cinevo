from datetime import datetime, time, timedelta

from app.extensions import db
from app.models import Booking, Expense, Payment, Showtime, User
from app.timeutil import local_now


def test_admin_dashboard_returns_paid_revenue_by_week_month_and_year(client, auth, app):
    today = local_now().date()
    payment_time = datetime.combine(today, time(10)) - timedelta(hours=7)
    amounts = [120000, 85000]

    with app.app_context():
        user = User.query.filter_by(email="user@cinevo.vn").one()
        showtime = Showtime.query.first()
        for index, amount in enumerate(amounts):
            booking = Booking(
                user_id=user.id,
                showtime_id=showtime.id,
                code=f"REVTEST{index}",
                status="PAID",
                total_amount=amount,
            )
            db.session.add(booking)
            db.session.flush()
            db.session.add(Payment(
                booking_id=booking.id,
                method="QR",
                amount=amount,
                status="PAID",
                paid_at=payment_time,
            ))
        db.session.add(Expense(
            description="Dashboard test expense",
            amount=32000,
            spent_on=today,
        ))
        db.session.commit()

    response = client.get("/api/admin/dashboard", headers=auth("admin"))
    assert response.status_code == 200
    revenue = response.get_json()["revenue"]
    expected_total = sum(amounts)

    assert revenue["week"]["total"] == expected_total
    assert revenue["month"]["total"] == expected_total
    assert revenue["year"]["total"] == expected_total
    assert revenue["week"]["items"][today.weekday()]["amount"] == expected_total
    assert revenue["month"]["items"][(today.day - 1) // 7]["amount"] == expected_total
    assert revenue["year"]["items"][today.month - 1]["amount"] == expected_total
    assert len(revenue["week"]["items"]) == 7
    assert len(revenue["month"]["items"]) == 5
    assert len(revenue["year"]["items"]) == 12
    finance = response.get_json()["finance"]
    for period in ("week", "month", "year"):
        assert finance[period]["income"] == expected_total
        assert finance[period]["expense"] == 32000
        assert finance[period]["profit"] == expected_total - 32000


def test_admin_can_create_and_delete_expense_but_manager_cannot(client, auth):
    payload = {"spent_on": local_now().date().isoformat(), "description": "Điện tháng này", "amount": 145000}
    forbidden = client.post("/api/admin/expenses", headers=auth("manager"), json=payload)
    assert forbidden.status_code == 403

    created = client.post("/api/admin/expenses", headers=auth("admin"), json=payload)
    assert created.status_code == 201
    item = created.get_json()
    assert item["description"] == payload["description"]
    assert item["amount"] == payload["amount"]
    assert item["spent_on"] == payload["spent_on"]

    dashboard = client.get("/api/admin/dashboard", headers=auth("admin")).get_json()
    assert any(row["id"] == item["id"] for row in dashboard["expenses"])
    deleted = client.delete(f"/api/admin/expenses/{item['id']}", headers=auth("admin"))
    assert deleted.status_code == 200
    assert all(row["id"] != item["id"] for row in
               client.get("/api/admin/dashboard", headers=auth("admin")).get_json()["expenses"])


def test_expense_input_is_validated(client, auth):
    response = client.post(
        "/api/admin/expenses",
        headers=auth("admin"),
        json={"spent_on": "yesterday", "description": "", "amount": -1},
    )
    assert response.status_code == 400
