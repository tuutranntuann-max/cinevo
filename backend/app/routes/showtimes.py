"""API suất chiếu và sơ đồ ghế (công khai)."""
from datetime import datetime, timedelta

from flask import Blueprint, jsonify, request

from ..extensions import db
from ..models import Cinema, Movie, MovieCancellation, Room, Seat, SeatHold, Showtime
from ..services.booking_service import taken_seat_ids
from ..services.seat_reservations import expire_seat_holds
from ..services.validation import int_arg
from ..timeutil import local_now, utc_now

bp = Blueprint("showtimes", __name__, url_prefix="/api/showtimes")


@bp.get("")
def list_showtimes():
    """?movie_id= &cinema_id= &city= &date=YYYY-MM-DD (chỉ trả suất chưa bắt đầu)."""
    query = (Showtime.query.join(Room).join(Cinema)
             .filter(Showtime.start_time >= local_now())
             .filter(~Showtime.movie_id.in_(db.session.query(Movie.id).filter(Movie.status == "ended")))
             .filter(~Showtime.movie_id.in_(db.session.query(MovieCancellation.movie_id))))
    if (v := int_arg("movie_id")) is not None:
        query = query.filter(Showtime.movie_id == v)
    if (v := int_arg("cinema_id")) is not None:
        query = query.filter(Cinema.id == v)
    if v := request.args.get("city"):
        query = query.filter(Cinema.city == v)
    if v := request.args.get("date"):
        try:
            day = datetime.strptime(v, "%Y-%m-%d")
        except ValueError:
            return jsonify({"message": "Ngày không hợp lệ."}), 400
        query = query.filter(Showtime.start_time >= day, Showtime.start_time < day + timedelta(days=1))
    return jsonify([s.to_dict() for s in query.order_by(Showtime.start_time).all()])


@bp.get("/<int:showtime_id>/seats")
def seat_map(showtime_id):
    expire_seat_holds()
    st = db.session.get(Showtime, showtime_id)
    movie = db.session.get(Movie, st.movie_id) if st else None
    if not st or not movie or db.session.get(MovieCancellation, st.movie_id) or movie.status == "ended":
        return jsonify({"message": "Không tìm thấy suất chiếu."}), 404
    taken = taken_seat_ids(showtime_id)
    held = {
        row.seat_id
        for row in SeatHold.query.filter_by(showtime_id=showtime_id)
        .filter(SeatHold.expires_at > utc_now()).all()
    }
    seats = Seat.query.filter_by(room_id=st.room_id).order_by(Seat.row_label, Seat.number).all()
    return jsonify({
        "showtime": st.to_dict(),
        "rows": st.room.total_rows, "cols": st.room.total_cols,
        "seats": [{**s.to_dict(), "price": s.price_for(st), "booked": s.id in taken,
                   "held": s.id in held} for s in seats],
    })
