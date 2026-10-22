from ..models import Seat


def validate_double_seat_selection(seats, selected_ids):
    selected_ids = set(selected_ids)
    for seat in seats:
        if seat.seat_type != "DOUBLE":
            continue
        partner_number = seat.number + 1 if seat.number % 2 else seat.number - 1
        partner = Seat.query.filter_by(
            room_id=seat.room_id,
            row_label=seat.row_label,
            number=partner_number,
        ).first()
        if (
            partner is None
            or partner.seat_type != "DOUBLE"
            or partner.id not in selected_ids
        ):
            return False
    return True
