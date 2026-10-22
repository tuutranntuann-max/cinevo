from datetime import timedelta

from app.extensions import db
from app.models import Membership, User
from app.timeutil import utc_now


def test_chatbot_recommends_movies_in_vietnamese_and_english(client):
    vietnamese = client.post("/api/chatbot/chat", json={"message": "Tôi thích phim hành động"})
    english = client.post("/api/chatbot/chat", json={"message": "I like action movies"})

    assert vietnamese.status_code == 200
    assert vietnamese.get_json()["language"] == "vi"
    assert vietnamese.get_json()["movies"]
    assert english.status_code == 200
    assert english.get_json()["language"] == "en"
    assert english.get_json()["movies"]


def test_chatbot_returns_movie_information_and_showtimes(client):
    response = client.post("/api/chatbot/chat", json={"message": "Thông tin phim Mưa Đỏ"})
    result = response.get_json()

    assert response.status_code == 200
    assert result["movies"][0]["title"] == "Mưa Đỏ"
    assert "rating" in result["movies"][0]
    assert "showtimes" in result["movies"][0]

    english = client.post("/api/chatbot/chat", json={"message": "Tell me about Mưa Đỏ"})
    assert english.get_json()["language"] == "en"
    assert english.get_json()["movies"][0]["title"] == "Mưa Đỏ"


def test_chatbot_prioritizes_booking_and_error_help(client):
    booking = client.post(
        "/api/chatbot/chat",
        json={"message": "How do I book a ticket for Street Fighter?"},
    ).get_json()
    payment_error = client.post(
        "/api/chatbot/chat",
        json={"message": "I have a payment error"},
    ).get_json()

    assert booking["action"]["url"] == "/user/movies"
    assert "movies" not in booking
    assert "bank" in payment_error["reply"].lower()

def test_chatbot_requires_login_to_check_transactions(client):
    response = client.post("/api/chatbot/chat", json={"message": "Check my payment"})
    result = response.get_json()

    assert response.status_code == 200
    assert result["action"]["url"] == "/user/login"
    assert "transactions" not in result


def test_chatbot_only_returns_transactions_for_signed_in_user(app, client, auth):
    now = utc_now()
    with app.app_context():
        customer = User.query.filter_by(email="user@cinevo.vn").first()
        other_customer = User.query.filter_by(email="manager@cinevo.vn").first()
        db.session.add_all([
            Membership(
                user_id=customer.id, tier="SILVER", starts_at=now,
                expires_at=now + timedelta(days=30), status="PENDING",
                amount=1000, payment_ref="MEM-USER-PRIVATE",
            ),
            Membership(
                user_id=other_customer.id, tier="GOLD", starts_at=now,
                expires_at=now + timedelta(days=30), status="PENDING",
                amount=2000, payment_ref="MEM-OTHER-PRIVATE",
            ),
        ])
        db.session.commit()

    response = client.post(
        "/api/chatbot/chat",
        json={"message": "Check my payment"},
        headers=auth("user"),
    )
    result = response.get_json()

    assert response.status_code == 200
    assert [item["reference"] for item in result["transactions"]] == ["MEM-USER-PRIVATE"]
