"""API AI (dữ liệu giả định). Mỗi route chỉ gọi service tương ứng trong app/ai/."""
from flask import Blueprint, jsonify, request

from ..ai.chatbot_service import ChatbotService
from ..ai.recommendation_service import MovieRecommendationService
from ..ai.seat_recommendation import SeatRecommendationService
from ..extensions import db
from ..models import Seat, Showtime
from ..services.booking_service import taken_seat_ids
from ..services.validation import ApiError, clean_str, int_arg, json_body

bp = Blueprint("ai", __name__, url_prefix="/api/ai")


@bp.get("/recommend-movies")
def recommend_movies():
    return jsonify(MovieRecommendationService().recommend(request.args.get("genre", "")[:50] or None,
                                                          int_arg("limit", 5, lo=1, hi=20)))


@bp.get("/recommend-seats")
def recommend_seats():
    st = db.session.get(Showtime, int_arg("showtime_id", 0))
    if not st:
        return jsonify({"message": "Không tìm thấy suất chiếu."}), 404
    taken = taken_seat_ids(st.id)
    seats = [{"id": s.id, "row": s.row_label, "number": s.number, "label": s.label, "booked": s.id in taken}
             for s in Seat.query.filter_by(room_id=st.room_id).all()]
    return jsonify(SeatRecommendationService().recommend(seats, int_arg("count", 2, lo=1, hi=4)))


@bp.post("/chat")
def chat():
    data = json_body()
    message = clean_str(data.get("message"), "Tin nhắn", required=True, max_len=500)
    return jsonify(ChatbotService().reply(message))
