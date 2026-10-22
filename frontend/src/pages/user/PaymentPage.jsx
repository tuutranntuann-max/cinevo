// Tạo giao dịch QR, giữ ghế trong 10 phút và chờ nhân viên xác nhận chuyển khoản.
import { useEffect, useState } from "react";
import { Navigate, useNavigate } from "react-router-dom";
import BookingSummary from "../../components/BookingSummary";
import ErrorBox from "../../components/ErrorBox";
import StepProgress from "../../components/StepProgress";
import { useBooking } from "../../context/BookingContext";
import { bookingService } from "../../services/bookingService";
import { commerceService } from "../../services/commerceService";
import { formatVND } from "../../utils/format";
import PaymentMethodInstructions from "../../components/PaymentMethodInstructions";
import { useUserPreferences } from "../../context/UserPreferencesContext";

export default function PaymentPage() {
  const { t } = useUserPreferences();
  const { booking, totals, resetBooking } = useBooking();
  const navigate = useNavigate();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [seatTaken, setSeatTaken] = useState(false);
  const [order, setOrder] = useState(null);
  const [settings, setSettings] = useState(null);
  const [holdDeadline, setHoldDeadline] = useState(null);
  const [remainingSeconds, setRemainingSeconds] = useState(null);
  const [holdStatusLoaded, setHoldStatusLoaded] = useState(false);
  const [paymentMethod, setPaymentMethod] = useState("VIETQR");
  const showtimeId = booking.showtime?.id;

  useEffect(() => {
    commerceService.settings().then(setSettings).catch((e) => setError(e.message));
  }, []);

  useEffect(() => {
    if (!showtimeId) {
      setHoldStatusLoaded(true);
      return undefined;
    }
    let active = true;
    setHoldStatusLoaded(false);
    commerceService.mySeatHolds(showtimeId)
      .then((holds) => {
        if (!active) return;
        const earliest = holds.reduce((deadline, hold) => {
          const time = new Date(hold.expires_at).getTime();
          return Number.isFinite(time) && (!deadline || time < deadline) ? time : deadline;
        }, null);
        setHoldDeadline(earliest);
      })
      .catch((e) => { if (active) setError(e.message); })
      .finally(() => { if (active) setHoldStatusLoaded(true); });
    return () => { active = false; };
  }, [showtimeId]);

  useEffect(() => {
    const bookingDeadline = order?.hold_expires_at
      ? new Date(order.hold_expires_at).getTime()
      : null;
    if (Number.isFinite(bookingDeadline)) {
      setHoldDeadline(bookingDeadline);
    } else if (order) {
      setHoldDeadline(null);
    }
  }, [order?.hold_expires_at]);

  useEffect(() => {
    if (!holdDeadline) {
      setRemainingSeconds(null);
      return undefined;
    }
    const updateTimer = () => setRemainingSeconds(
      Math.max(0, Math.ceil((holdDeadline - Date.now()) / 1000)),
    );
    updateTimer();
    const timer = window.setInterval(updateTimer, 1000);
    return () => window.clearInterval(timer);
  }, [holdDeadline]);

  useEffect(() => {
    if (!order) return undefined;
    const check = async () => {
      try {
        const current = await bookingService.detail(order.code);
        setOrder(current);
        if (current.status === "PAID") {
          resetBooking();
          navigate(`/user/booking-success/${current.code}`, { replace: true });
        } else if (current.status === "CANCELLED") {
          setError("Đơn đã hết hạn hoặc bị từ chối. Vui lòng chọn ghế mới để đặt lại.");
        }
      } catch (e) { setError(e.message); }
    };
    const timer = window.setInterval(check, 4000);
    return () => window.clearInterval(timer);
  }, [order?.code, navigate, resetBooking]);

  if (!booking.showtime || !booking.seats.length) return <Navigate to="/user/movies" replace />;
  const paymentReady = Boolean(settings?.bank_bin && settings?.account_number);

  const pay = async () => {
    setBusy(true); setError("");
    try {
      const created = await bookingService.create({
        showtime_id: booking.showtime.id,
        seat_ids: booking.seats.map((s) => s.id),
        foods: booking.foods.map((f) => ({ food_id: f.id, quantity: f.quantity })),
        payment_method: "QR",
        promo_code: booking.promotion?.code || "",
      });
      setOrder(created);
    } catch (e) {
      setError(e.message);
      setSeatTaken(["SEAT_TAKEN", "HOLD_EXPIRED"].includes(e.code));
    } finally { setBusy(false); }
  };

  return (
    <section className="narrow">
      <StepProgress current={3} />
      <h1 className="page-title">{t("Thanh toán")}</h1>
      <BookingSummary booking={booking} totals={totals} showFood />
      <h3>{t("Chọn cách thanh toán")}</h3>
      {!paymentReady && <div className="alert">{t("Admin cần cấu hình ngân hàng và số tài khoản nhận tiền trước khi nhận thanh toán.")}</div>}
      <ErrorBox message={error} />
      {(seatTaken || remainingSeconds === 0) && <button className="btn btn-outline" onClick={() => navigate(`/user/seats/${booking.showtime.id}`)}>{t("Chọn lại ghế")}</button>}
      {order ? (
        <>
          <PaymentMethodInstructions settings={settings} amount={order.total_amount} reference={order.code} initialMethod={paymentMethod} />
        <div className={`notice reservation-countdown ${remainingSeconds === 0 ? "expired" : ""}`} role="timer" aria-live="polite">
          {remainingSeconds === 0
            ? t("Đã hết thời gian giữ ghế. Đang cập nhật trạng thái giao dịch...")
            : <>{t("Đang chờ nhân viên xác nhận. Thời gian giữ ghế còn")} <strong>{Math.floor((remainingSeconds ?? 0) / 60)}:{String((remainingSeconds ?? 0) % 60).padStart(2, "0")}</strong>.</>}
        </div>
        <p className="muted small">{t("Mã giao dịch:")} {order.code} · {t("Trạng thái:")} {order.payment?.status || "PENDING"}</p>
        {order.status === "CANCELLED" && <button className="btn btn-outline" onClick={() => navigate(`/user/seats/${booking.showtime.id}`)}>{t("Chọn lại ghế")}</button>}
        </>
      ) : (
        <>
        <div className="payment-method-options" role="group" aria-label={t("Phương thức thanh toán")}>
          <button type="button" className={`btn ${paymentMethod === "VIETQR" ? "btn-red" : "btn-outline"}`}
            aria-pressed={paymentMethod === "VIETQR"} onClick={() => setPaymentMethod("VIETQR")}>
            {t("Quét mã VietQR")}
          </button>
          <button type="button" className={`btn ${paymentMethod === "BANK" ? "btn-red" : "btn-outline"}`}
            aria-pressed={paymentMethod === "BANK"} onClick={() => setPaymentMethod("BANK")}>
            {t("Mở ngân hàng / ví")}
          </button>
        </div>
        {paymentMethod === "BANK" && <p className="hint">{t("Sau khi tạo mã giao dịch, bạn có thể chọn website ngân hàng hoặc ví để mở.")}</p>}
        {holdDeadline && remainingSeconds !== null && (
          <div className={`notice reservation-countdown ${remainingSeconds === 0 ? "expired" : ""}`} role="timer" aria-live="polite">
            {remainingSeconds === 0 ? t("Đã hết thời gian giữ ghế. Vui lòng chọn lại ghế.") : <>{t("Thời gian giữ ghế còn")} <strong>{Math.floor(remainingSeconds / 60)}:{String(remainingSeconds % 60).padStart(2, "0")}</strong>.</>}
          </div>
        )}
        <button className="btn btn-red btn-block" disabled={busy || !paymentReady || !holdStatusLoaded || remainingSeconds === 0} onClick={pay}>
          {busy ? t("Đang tạo giao dịch...") : !holdStatusLoaded ? t("Đang kiểm tra ghế...") : remainingSeconds === 0 ? t("Thời gian giữ ghế đã hết") : `${t("Tạo giao dịch")} ${formatVND(totals.total)}`}
        </button>
        </>
      )}
    </section>
  );
}
