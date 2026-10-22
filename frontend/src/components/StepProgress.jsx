import { useUserPreferences } from "../context/UserPreferencesContext";

export default function StepProgress({ current }) {
  const { t } = useUserPreferences();
  const steps = ["Chọn ghế", "Xác nhận", "Đồ ăn", "Thanh toán"];
  return (
    <ol className="steps" aria-label={t("Tiến trình đặt vé")}>
      {steps.map((s, i) => (
        <li key={s} className={i === current ? "current" : i < current ? "done" : ""}>{t(s)}</li>
      ))}
    </ol>
  );
}
