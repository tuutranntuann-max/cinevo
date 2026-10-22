import { useEffect, useMemo, useState } from "react";
import Loading from "../../components/Loading";
import { api } from "../../services/api";
import { useUserPreferences } from "../../context/UserPreferencesContext";

const REGIONS = ["Miền Bắc", "Miền Trung", "Miền Nam"];

export default function CinemaListPage() {
  const { t } = useUserPreferences();
  const [cinemas, setCinemas] = useState(null);
  const [provinces, setProvinces] = useState([]);
  const [region, setRegion] = useState("");
  const [province, setProvince] = useState("");

  useEffect(() => {
    Promise.all([api.get("/cinemas"), api.get("/provinces")])
      .then(([cinemaRows, provinceRows]) => {
        setCinemas(cinemaRows);
        setProvinces(provinceRows);
      })
      .catch(() => {
        setCinemas([]);
        setProvinces([]);
      });
  }, []);

  const provinceOptions = useMemo(
    () => provinces.filter((item) => !region || item.region === region),
    [provinces, region],
  );
  const visibleCinemas = (cinemas || []).filter((cinema) =>
    (!region || cinema.region === region)
    && (!province || (cinema.province || cinema.city) === province));

  return (
    <section>
      <h1 className="page-title">{t("Hệ thống rạp toàn quốc")}</h1>
      <p className="muted">{t("Tìm rạp theo miền và tỉnh/thành trên cả nước.")}</p>
      <div className="cinema-region-filters">
        <div className="chips" role="group" aria-label={t("Lọc theo miền")}>
          <button type="button" className={`chip ${region === "" ? "active" : ""}`} onClick={() => {
            setRegion("");
            setProvince("");
          }}>{t("Toàn quốc")}</button>
          {REGIONS.map((item) => (
            <button key={item} type="button" className={`chip ${region === item ? "active" : ""}`} onClick={() => {
              setRegion(item);
              setProvince("");
            }}>{t(item)}</button>
          ))}
        </div>
        <label>{t("Tỉnh/thành")}
          <select value={province} onChange={(event) => setProvince(event.target.value)}>
            <option value="">{t("Tất cả tỉnh/thành")}</option>
            {provinceOptions.map((item) => <option key={item.name} value={item.name}>{item.name}</option>)}
          </select>
        </label>
      </div>
      {!cinemas ? <Loading /> : visibleCinemas.length ? (
        <div className="list">
          {visibleCinemas.map((c) => (
            <article key={c.id} className="card">
              {c.chain && <p className="small muted">{c.chain}</p>}
              <h3>{c.name}</h3>
              <p className="muted">{c.address}</p>
              <p className="small">{c.region} · {c.province || c.city}{c.phone ? ` · ${c.phone}` : ""}</p>
            </article>
          ))}
        </div>
      ) : <div className="state-box">{t("Chưa có rạp tại khu vực này.")}</div>}
    </section>
  );
}
