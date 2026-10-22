// Chọn ghế (có AI gợi ý). Khi bấm Tiếp tục: nếu CHƯA đăng nhập mới hiện popup đăng nhập/đăng ký.
// Sau khi đăng nhập xong, đơn đặt vé được giữ nguyên và đi thẳng tới trang Xác nhận.
import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import ErrorBox from "../../components/ErrorBox";
import Loading from "../../components/Loading";
import SeatMap from "../../components/SeatMap";
import StepProgress from "../../components/StepProgress";
import { groupSeatPairs } from "../../components/SeatMap";
import { useAuth } from "../../context/AuthContext";
import { useBooking } from "../../context/BookingContext";
import { useFeatures } from "../../context/FeaturesContext";
import { aiService } from "../../services/aiService";
import { movieService } from "../../services/movieService";
import { commerceService } from "../../services/commerceService";
import { formatDate, formatTime, formatVND } from "../../utils/format";
import { useUserPreferences } from "../../context/UserPreferencesContext";

const MAX_SEATS = 8;

export default function SeatSelectionPage() {
  const { t } = useUserPreferences();
  const { showtimeId } = useParams();
  const navigate = useNavigate();
  const { requireLogin, user } = useAuth();
  const { features } = useFeatures();
  const { booking, saveSeatSelection } = useBooking();
  const [data, setData] = useState(null);
  const [selected, setSelected] = useState([]);       // mảng seat object
  const [suggested, setSuggested] = useState([]);
  const [aiMsg, setAiMsg] = useState("");
  const [error, setError] = useState("");
  const [holdExpiresAt, setHoldExpiresAt] = useState(null);
  const [holdBusy, setHoldBusy] = useState(false);
  const [remainingSeconds, setRemainingSeconds] = useState(0);
  const [trust, setTrust] = useState(null);

  useEffect(() => {
    Promise.all([
      movieService.seatMap(showtimeId),
      user ? commerceService.mySeatHolds(showtimeId) : Promise.resolve([]),
      user ? commerceService.trust() : Promise.resolve(null),
    ]).then(([d, holds, trustState]) => {
      const heldIds = new Set(holds.map((hold) => hold.seat_id));
      d.seats = d.seats.map((seat) => ({ ...seat, held: seat.held && !heldIds.has(seat.id) }));
      setData(d);
      const ownSeats = groupSeatPairs(d.seats).filter((seat) =>
        seat.seat_ids.every((id) => heldIds.has(id)) && !seat.booked);
      setSelected(ownSeats.length ? ownSeats : booking.showtime?.id === d.showtime.id
        ? groupSeatPairs(d.seats).filter((seat) =>
          seat.seat_ids.every((id) => booking.seats.some((chosen) => chosen.id === id))
          && seat.seat_ids.every((id) => d.seats.some((item) => item.id === id && !item.booked && !item.held)))
        : []);
      if (holds.length) setHoldExpiresAt(holds.reduce((earliest, hold) =>
        !earliest || hold.expires_at < earliest ? hold.expires_at : earliest, null));
      setTrust(trustState);
    }).catch((e) => setError(e.message));
  }, [showtimeId, user?.id]);

  useEffect(() => {
    if (!holdExpiresAt) return undefined;
    const updateTimer = () => {
      const seconds = Math.max(0, Math.ceil((new Date(holdExpiresAt).getTime() - Date.now()) / 1000));
      setRemainingSeconds(seconds);
      if (seconds === 0) {
        setSelected([]);
        setHoldExpiresAt(null);
        setError(t("Đã hết thời gian giữ ghế. Vui lòng chọn lại ghế."));
        Promise.all([movieService.seatMap(showtimeId), commerceService.trust()])
          .then(([seatMap, trustState]) => { setData(seatMap); setTrust(trustState); })
          .catch((e) => setError(e.message));
      }
    };
    updateTimer();
    const timer = window.setInterval(updateTimer, 1000);
    return () => window.clearInterval(timer);
  }, [holdExpiresAt, showtimeId, t]);

  const toggle = async (seat) => {
    if (holdBusy) return;
    setError("");
    const next = selected.some((item) => item.id === seat.id)
      ? selected.filter((item) => item.id !== seat.id)
      : [...selected, seat];
    const nextSeatIds = next.flatMap((item) => item.seat_ids);
    if (nextSeatIds.length > MAX_SEATS) return setError(`${t("Chọn tối đa")} ${MAX_SEATS} ${t("ghế")}.`);
    if (!user) {
      setSelected(next);
      return;
    }
    setHoldBusy(true);
    try {
      const result = await commerceService.saveSeatHolds(Number(showtimeId), nextSeatIds);
      setSelected(next);
      setHoldExpiresAt(result.expires_at);
      setTrust(result.trust);
      const previouslySelectedIds = new Set(selected.flatMap((item) => item.seat_ids));
      setData((current) => ({
        ...current,
        seats: current.seats.map((item) => ({
          ...item,
          held: nextSeatIds.includes(item.id)
            || (item.held && !previouslySelectedIds.has(item.id)),
        })),
      }));
      if (result.trust?.blocked_until && new Date(result.trust.blocked_until) > new Date()) {
        setError(t("Tài khoản đang tạm khóa đặt ghế do vi phạm nhiều lần."));
      }
    } catch (e) {
      setError(e.message);
      if (e.code === "SEAT_TAKEN") {
        const refreshed = await movieService.seatMap(showtimeId);
        setData(refreshed);
      }
    } finally {
      setHoldBusy(false);
    }
  };

  const askAi = async (count) => {
    setAiMsg(t("Đang tìm ghế đẹp..."));
    try {
      const r = await aiService.recommendSeats(showtimeId, count);
      setAiMsg(r.message);
      setSuggested(r.seat_ids);
      if (r.seat_ids.length) {
        const choices = groupSeatPairs(data.seats).filter((s) => s.seat_ids.every((id) => r.seat_ids.includes(id)));
        const choiceIds = choices.flatMap((seat) => seat.seat_ids);
        const held = await commerceService.saveSeatHolds(Number(showtimeId), choiceIds);
        setSelected(choices);
        setHoldExpiresAt(held.expires_at);
      }
    } catch (e) { setAiMsg(e.message); }
  };

  const proceed = async () => {
    if (!selected.length) return setError(t("Vui lòng chọn ít nhất 1 ghế."));
    const selectedSeatIds = new Set(selected.flatMap((seat) => seat.seat_ids));
    const seats = data.seats.filter((seat) => selectedSeatIds.has(seat.id))
      .map((seat) => ({ id: seat.id, label: seat.label, type: seat.type, price: seat.price }));
    requireLogin(async () => {
      setHoldBusy(true);
      setError("");
      try {
        const result = await commerceService.saveSeatHolds(Number(showtimeId), [...selectedSeatIds]);
        saveSeatSelection(data.showtime, seats);
        setHoldExpiresAt(result.expires_at);
        setTrust(result.trust);
        navigate("/user/checkout");
      } catch (e) {
        setError(e.message);
      } finally {
        setHoldBusy(false);
      }
    });
  };

  if (error && !data) return <ErrorBox message={error} />;
  if (!data) return <Loading />;
  const st = data.showtime;
  const total = selected.reduce((s, x) => s + x.price, 0);

  return (
    <section className="seat-selection-page">
      <StepProgress current={0} />
      <h1 className="page-title">{st.movie.title}</h1>
      <p className="muted">{st.cinema.name} · {st.room.name} · {formatDate(st.start_time)} · {formatTime(st.start_time)}</p>

      {features.ai && (
        <div className="ai-box">
          <b>{t("Gợi ý ghế bằng AI")}</b>
          <button className="btn btn-outline btn-sm" onClick={() => askAi(1)}>1 {t("người")}</button>
          <button className="btn btn-outline btn-sm" onClick={() => askAi(2)}>2 {t("người")}</button>
          {aiMsg && <span className="muted small">{aiMsg}</span>}
        </div>
      )}

      <SeatMap seats={data.seats} selectedIds={selected.flatMap((seat) => seat.seat_ids)} suggestedIds={suggested} onToggle={toggle} />
      {holdExpiresAt && <p className="notice reservation-countdown" role="timer" aria-live="polite">
        {t("Thời gian giữ ghế còn")} <strong>{Math.floor(remainingSeconds / 60)}:{String(remainingSeconds % 60).padStart(2, "0")}</strong>. {t("Hoàn tất thanh toán trước khi hết giờ.")}
      </p>}
      {trust?.penalties > 0 && <p className="notice">{t("Bạn đã bị trừ")} {trust.penalties} {t("điểm uy tín do để ghế hết hạn. Hãy hoàn tất đặt vé đúng giờ để tránh bị khóa đặt ghế.")}</p>}
      {holdBusy && <p className="muted small">{t("Đang cập nhật ghế...")}</p>}
      <ErrorBox message={error} />

      <div className="sticky-bar seat-selection-actions">
        <div>
          <b>{selected.length ? selected.map((s) => s.label).join(", ") : t("Chưa chọn ghế")}</b>
          <div className="muted small">{t("Tạm tính:")} {formatVND(total)}</div>
        </div>
        <button className="btn btn-red" disabled={holdBusy} onClick={proceed}>{holdBusy ? t("Đang giữ ghế...") : t("Tiếp tục")}</button>
      </div>
    </section>
  );
}
