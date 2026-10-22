import { useEffect, useState } from "react";
import ErrorBox from "../../components/ErrorBox";
import PaymentMethodInstructions from "../../components/PaymentMethodInstructions";
import { useAuth } from "../../context/AuthContext";
import { commerceService } from "../../services/commerceService";
import { formatVND } from "../../utils/format";
import { useUserPreferences } from "../../context/UserPreferencesContext";

const tierClass = { SILVER: "membership-silver", GOLD: "membership-gold", DIAMOND: "membership-diamond" };

export default function MembershipPage() {
  const { user, requireLogin } = useAuth();
  const { t, language } = useUserPreferences();
  const [plans, setPlans] = useState([]);
  const [membership, setMembership] = useState(null);
  const [settings, setSettings] = useState(null);
  const [pending, setPending] = useState(null);
  const [error, setError] = useState("");
  const [busyTier, setBusyTier] = useState("");
  const paymentReady = Boolean(settings?.bank_bin && settings?.account_number);

  const load = async () => {
    try {
      const [planRows, bankSettings] = await Promise.all([
        commerceService.plans(),
        commerceService.settings(),
      ]);
      setPlans(planRows);
      setSettings(bankSettings);
      if (user) setMembership(await commerceService.membership());
    } catch (e) { setError(e.message); }
  };

  useEffect(() => { load(); }, [user]);
  useEffect(() => {
    if (!pending || !user) return undefined;
    const timer = window.setInterval(() => {
      commerceService.membership().then((value) => {
        setMembership(value);
        if (value.history.some((item) => item.payment_ref === pending.payment_ref && item.status === "ACTIVE")) {
          setPending(null);
        }
      }).catch((e) => setError(e.message));
    }, 5000);
    return () => window.clearInterval(timer);
  }, [pending?.payment_ref, user]);

  const createPurchase = (tier) => {
    setBusyTier(tier); setError("");
    commerceService.buyMembership(tier)
      .then(setPending)
      .catch((e) => setError(e.message))
      .finally(() => setBusyTier(""));
  };
  const buy = (tier) => {
    if (!user) return requireLogin(() => createPurchase(tier));
    createPurchase(tier);
  };

  return (
    <section>
      <header className="page-heading">
        <p className="eyebrow">CINEVO MEMBERSHIP</p>
        <h1 className="page-title">{t("Gói thành viên")}</h1>
        <p className="muted">{t("Gói có hiệu lực 30 ngày, mở quyền xem phim trực tuyến và ưu đãi cho đồ ăn, hàng hóa tại Shop. Ưu đãi không áp dụng cho vé phim.")}</p>
      </header>
      <ErrorBox message={error} />
      {membership?.active && (
        <div className="notice">
          {t("Hạng hiện tại:")} <b>{t(({ SILVER: "Bạc", GOLD: "Vàng", DIAMOND: "Kim cương" })[membership.active.tier] || membership.active.tier)}</b> · {t("Hết hạn")} {new Date(membership.active.expires_at).toLocaleDateString(language === "en" ? "en-US" : "vi-VN")}
        </div>
      )}
      <div className="membership-grid">
        {plans.map((plan) => (
          <article className={`card membership-card ${tierClass[plan.code]}`} key={plan.code}>
            <span className="eyebrow">{t("30 NGÀY")}</span>
            <h2>{t(plan.label)}</h2>
            <p className="membership-price">{plan.price ? formatVND(plan.price) : t("Chưa mở bán")}</p>
            <ul>
              <li>{plan.daily_movies == null ? t("Không giới hạn") : `${plan.daily_movies} ${t("phim / ngày")}`}</li>
              <li>{t("Xem phim trực tuyến khi gói còn hiệu lực")}</li>
              <li>{t("Giảm")} {plan.food_discount}% {t("đồ ăn")}</li>
              <li>{t("Giảm")} {plan.product_discount}% {t("hàng hóa")}</li>
            </ul>
            <button className="btn btn-red btn-block" disabled={!plan.price || !paymentReady || !!busyTier}
              onClick={() => buy(plan.code)}>
              {busyTier === plan.code ? t("Đang tạo giao dịch...") : t("Mua gói")}
            </button>
          </article>
        ))}
      </div>
      {pending && (
        <div className="commerce-checkout">
          <h2>{t("Đang chờ thanh toán thành viên")}</h2>
          <PaymentMethodInstructions settings={settings} amount={pending.amount} reference={pending.payment_ref} />
        </div>
      )}
      {!paymentReady && <p className="hint">{t("Giao dịch sẽ mở khi Admin cấu hình ngân hàng nhận tiền và số tài khoản trong phần quản lý thanh toán.")}</p>}
      {membership?.trust && (
        <p className="muted small">{t("Điểm uy tín đặt ghế:")} {membership.trust.score} · {t("Số lần hết hạn giữ ghế:")} {membership.trust.expired_holds}</p>
      )}
    </section>
  );
}
