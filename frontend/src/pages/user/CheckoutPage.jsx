// XÁC NHẬN ĐẶT VÉ: hiển thị lại đúng đơn khách vừa chọn (đã được giữ nguyên sau khi đăng nhập/đăng ký).
import { useState } from "react";
import { Link, Navigate, useNavigate } from "react-router-dom";
import BookingSummary from "../../components/BookingSummary";
import ErrorBox from "../../components/ErrorBox";
import StepProgress from "../../components/StepProgress";
import { useBooking } from "../../context/BookingContext";
import { useUserPreferences } from "../../context/UserPreferencesContext";
import { bookingService } from "../../services/bookingService";

export default function CheckoutPage() {
  const { t } = useUserPreferences();
  const { booking, totals, setPromotion } = useBooking();
  const navigate = useNavigate();
  const [code, setCode] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  if (!booking.showtime || !booking.seats.length) return <Navigate to="/user/movies" replace />;

  const applyPromotion = async (event) => {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      const promotion = await bookingService.validatePromotion(code.trim());
      setPromotion(promotion);
      setCode(promotion.code);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <section className="narrow">
      <StepProgress current={1} />
      <h1 className="page-title">{t("Xác nhận đặt vé")}</h1>
      <BookingSummary booking={booking} totals={totals} />
      <form className="promotion-form" onSubmit={applyPromotion}>
        <label htmlFor="promotion-code">{t("Mã giảm giá")}</label>
        <div className="promotion-form-controls">
          <input
            id="promotion-code"
            value={code}
            onChange={(event) => setCode(event.target.value)}
            placeholder={t("Nhập mã giảm giá")}
            maxLength={30}
            disabled={busy}
          />
          {booking.promotion ? (
            <button type="button" className="btn btn-ghost" onClick={() => {
              setPromotion(null);
              setCode("");
              setError("");
            }}>{t("Gỡ mã")}</button>
          ) : (
            <button className="btn btn-outline" disabled={busy || !code.trim()}>
              {busy ? t("Đang kiểm tra...") : t("Áp dụng")}
            </button>
          )}
        </div>
        {booking.promotion && <p className="success">{t("Đã áp dụng mã giảm giá")}: {booking.promotion.discount_percent}%</p>}
        <ErrorBox message={error} />
      </form>
      <div className="actions">
        <Link className="btn btn-ghost" to={`/user/seats/${booking.showtime.id}`}>{t("Đổi ghế")}</Link>
        <button className="btn btn-red" onClick={() => navigate("/user/food")}>{t("Tiếp tục")}</button>
      </div>
    </section>
  );
}
