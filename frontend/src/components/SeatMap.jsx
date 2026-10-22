import { useUserPreferences } from "../context/UserPreferencesContext";

export function groupSeatPairs(seats) {
  const rows = seats.reduce((acc, seat) => {
    (acc[seat.row] ||= []).push(seat);
    return acc;
  }, {});
  return Object.values(rows).flatMap((rowSeats) => {
    const ordered = [...rowSeats].sort((left, right) => left.number - right.number);
    const groups = [];
    for (let index = 0; index < ordered.length; index += 1) {
      const seat = ordered[index];
      const partner = ordered[index + 1];
      if (seat.type === "DOUBLE" && partner?.type === "DOUBLE" && partner.number === seat.number + 1) {
        groups.push({
          ...seat,
          id: seat.id,
          seat_ids: [seat.id, partner.id],
          label: `${seat.label}-${partner.label}`,
          number_label: `${seat.number}-${partner.number}`,
          price: seat.price + partner.price,
          booked: seat.booked || partner.booked,
          held: seat.held || partner.held,
          double: true,
        });
        index += 1;
      } else {
        groups.push({
          ...seat,
          seat_ids: [seat.id],
          number_label: String(seat.number),
          double: false,
        });
      }
    }
    return groups;
  });
}

// Sơ đồ ghế: ghế đôi là một lựa chọn chiếm hai ghế kề nhau.
export default function SeatMap({ seats, selectedIds, suggestedIds = [], onToggle }) {
  const { t } = useUserPreferences();
  const rows = groupSeatPairs(seats).reduce((acc, seat) => ((acc[seat.row] ||= []).push(seat), acc), {});
  return (
    <div className="seatmap">
      <div className="screen">{t("MÀN HÌNH")}</div>
      {Object.keys(rows).sort().map((row) => (
        <div className="seat-row" key={row}>
          <span className="row-label">{row}</span>
          {rows[row].map((s) => {
            const suggested = s.seat_ids.every((id) => suggestedIds.includes(id));
            if (s.double) {
              const pairSelected = s.seat_ids.every((id) => selectedIds.includes(id));
              const unavailable = s.booked || (s.held && !pairSelected);
              return (
                <span className="seat-double-pair" key={s.id} aria-label={`${t("Ghế đôi")} ${s.label}`}>
                  {s.seat_ids.map((seatId, index) => {
                    const selected = selectedIds.includes(seatId);
                    const cls = [
                      "seat", "double",
                      s.booked && "booked",
                      s.held && !selected && "held",
                      selected && "selected",
                      !selected && suggested && "suggested",
                    ].filter(Boolean).join(" ");
                    return (
                      <button key={seatId} className={cls} disabled={unavailable} onClick={() => onToggle(s)}
                        aria-pressed={pairSelected}
                        aria-label={`${t("Ghế đôi")} ${s.label}, ${t("vị trí")} ${index + 1}${s.booked ? `, ${t("đã đặt")}` : s.held ? `, ${t("đang được giữ")}` : ""}`}>
                        {s.number - (s.number % 2 === 0 ? 1 : 0) + index}
                      </button>
                    );
                  })}
                </span>
              );
            }
            const selected = s.seat_ids.every((id) => selectedIds.includes(id));
            const cls = ["seat", s.type === "VIP" && "vip", s.booked && "booked",
              s.held && !selected && "held", selected && "selected",
              !selected && suggested && "suggested"].filter(Boolean).join(" ");
            const seatUnavailable = s.booked || (s.held && !selected);
            return (
              <button key={s.id} className={cls} disabled={seatUnavailable} onClick={() => onToggle(s)}
                aria-pressed={selected} aria-label={`${t(s.double ? "Ghế đôi" : "Ghế")} ${s.label}${s.booked ? `, ${t("đã đặt")}` : s.held ? `, ${t("đang được giữ")}` : ""}`}>
                {s.number_label}
              </button>
            );
          })}
          <span className="row-label">{row}</span>
        </div>
      ))}
      <div className="legend">
        <span><i className="seat sm" />{t("Thường")}</span><span><i className="seat sm vip" />VIP</span>
        <span><i className="seat sm double" />{t("Ghế đôi")}</span>
        <span><i className="seat sm selected" />{t("Đang chọn")}</span><span><i className="seat sm suggested" />{t("AI gợi ý")}</span>
        <span><i className="seat sm held" />{t("Đang giữ")}</span><span><i className="seat sm booked" />{t("Đã đặt")}</span>
      </div>
    </div>
  );
}
