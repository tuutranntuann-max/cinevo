// Chọn combo đồ ăn (tùy chọn). Có nút Bỏ qua.
import { useEffect, useState } from "react";
import { Navigate, useNavigate } from "react-router-dom";
import Loading from "../../components/Loading";
import ErrorBox from "../../components/ErrorBox";
import StepProgress from "../../components/StepProgress";
import { useBooking } from "../../context/BookingContext";
import { commerceService } from "../../services/commerceService";
import { movieService } from "../../services/movieService";
import { formatVND } from "../../utils/format";
import { useUserPreferences } from "../../context/UserPreferencesContext";

export default function FoodPage() {
  const { t } = useUserPreferences();
  const { booking, setFoods, totals } = useBooking();
  const navigate = useNavigate();
  const [foods, setFoodList] = useState(null);
  const [membership, setMembership] = useState(null);
  const [error, setError] = useState("");
  const [qty, setQty] = useState(() => Object.fromEntries(booking.foods.map((f) => [f.id, f.quantity])));

  useEffect(() => {
    Promise.all([movieService.foods(), commerceService.membership()])
      .then(([items, currentMembership]) => {
        setFoodList(items);
        setMembership(currentMembership.active);
      })
      .catch((e) => { setError(e.message); setFoodList([]); });
  }, []);
  if (!booking.showtime || !booking.seats.length) return <Navigate to="/user/movies" replace />;

  const change = (id, delta) => setQty((q) => ({ ...q, [id]: Math.max(0, Math.min(10, (q[id] || 0) + delta)) }));
  const discountRate = { SILVER: 10, GOLD: 20, DIAMOND: 45 }[membership?.tier] || 0;
  const priceFor = (food) => Math.floor(food.price * (100 - discountRate) / 100);
  const foodTotal = (foods || []).reduce((s, f) => s + priceFor(f) * (qty[f.id] || 0), 0);

  const next = (skip) => {
    setFoods(skip ? [] : foods.filter((f) => qty[f.id] > 0).map((f) => ({ id: f.id, name: f.name, price: priceFor(f), quantity: qty[f.id] })));
    navigate("/user/payment");
  };

  return (
    <section className="narrow">
      <StepProgress current={2} />
      <h1 className="page-title">{t("Chọn combo đồ ăn")}</h1>
      <ErrorBox message={error} />
      {discountRate > 0 && <p className="notice">{t("Hạng")} {membership.tier}: {discountRate}% {t("được giảm giá cho đồ ăn.")}</p>}
      {!foods ? <Loading /> : (
        <div className="list">
          {foods.map((f) => (
            <article key={f.id} className="card food">
              <div><h3>{f.name}</h3><p className="muted small">{f.description}</p><b>{formatVND(priceFor(f))}</b>
                {discountRate > 0 && <small className="muted"> <s>{formatVND(f.price)}</s></small>}</div>
              <div className="qty">
                <button className="btn btn-ghost btn-sm" onClick={() => change(f.id, -1)} aria-label={`${t("Giảm số lượng")} ${f.name}`}>−</button>
                <span>{qty[f.id] || 0}</span>
                <button className="btn btn-outline btn-sm" onClick={() => change(f.id, 1)} aria-label={`+ ${t("Thêm")}`}>+ {t("Thêm")}</button>
              </div>
            </article>
          ))}
        </div>
      )}
      <div className="sticky-bar">
        <div><b>{t("Vé:")} {formatVND(totals.seatAmount)}</b><div className="muted small">{t("Combo")}: {formatVND(foodTotal)}</div></div>
        <div className="actions">
          <button className="btn btn-ghost" onClick={() => next(true)}>{t("Bỏ qua")}</button>
          <button className="btn btn-red" disabled={!foodTotal} onClick={() => next(false)}>{t("Tiếp tục")}</button>
        </div>
      </div>
    </section>
  );
}
