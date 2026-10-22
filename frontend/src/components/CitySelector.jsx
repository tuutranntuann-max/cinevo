import { useEffect, useState } from "react";
import { movieService } from "../services/movieService";
import { useBooking } from "../context/BookingContext";
import { useUserPreferences } from "../context/UserPreferencesContext";

// Chọn khu vực (Hà Nội, TP.HCM...). Danh sách lấy từ các rạp trong database.
export default function CitySelector({ variant = "select" }) {
  const { city, setCity } = useBooking();
  const { t } = useUserPreferences();
  const [cities, setCities] = useState([]);

  useEffect(() => { movieService.cities().then(setCities).catch(() => {}); }, []);

  if (variant === "chips") {
    return (
      <div className="chips" role="group" aria-label={t("Chọn khu vực")}>
        {cities.map((c) => (
          <button key={c} className={`chip ${c === city ? "active" : ""}`} onClick={() => setCity(c)}>{c}</button>
        ))}
      </div>
    );
  }
  return (
    <select className="city-select" value={city} onChange={(e) => setCity(e.target.value)} aria-label={t("Khu vực")}>
      <option value="">{t("Tất cả khu vực")}</option>
      {cities.map((c) => <option key={c} value={c}>{c}</option>)}
    </select>
  );
}
