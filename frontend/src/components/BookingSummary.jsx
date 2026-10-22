import { formatVND } from "../utils/format";
import { useUserPreferences } from "../context/UserPreferencesContext";

// Khối tóm tắt đơn đặt vé: dùng ở Xác nhận, Đồ ăn, Thanh toán.
export default function BookingSummary({ booking, totals, showFood = false }) {
  const { t, language } = useUserPreferences();
  const st = booking.showtime;
  return (
    <div className="ticket-card">
      <h3>{st.movie.title}</h3>
      <dl className="kv">
        <dt>{t("Rạp")}</dt><dd>{st.cinema.name}</dd>
        <dt>{t("Phòng")}</dt><dd>{st.room.name} ({st.room.room_type})</dd>
        <dt>{t("Ngày")}</dt><dd>{new Date(st.start_time).toLocaleDateString(language === "en" ? "en-US" : "vi-VN")}</dd>
        <dt>{t("Giờ")}</dt><dd>{new Date(st.start_time).toLocaleTimeString(language === "en" ? "en-US" : "vi-VN", { hour: "2-digit", minute: "2-digit" })}</dd>
        <dt>{t("Ghế")}</dt><dd>{booking.seats.map((s) => s.label).join(", ")}</dd>
      </dl>
      <div className="totals">
        <div><span>{t("Tiền vé")}</span><b>{formatVND(totals.seatAmount)}</b></div>
        {showFood && (
          <>
            {booking.foods.map((f) => (
              <div key={f.id} className="muted"><span>{f.name} × {f.quantity}</span><span>{formatVND(f.price * f.quantity)}</span></div>
            ))}
            <div><span>{t("Combo")}</span><b>{formatVND(totals.foodAmount)}</b></div>
          </>
        )}
        {booking.promotion && (
          <div className="promotion-total">
            <span>{t("Mã giảm giá")} ({booking.promotion.code})</span>
            <b>-{formatVND(totals.discountAmount)}</b>
          </div>
        )}
        <div className="grand"><span>{t("Tổng")}</span><b>{formatVND(totals.total)}</b></div>
      </div>
    </div>
  );
}
