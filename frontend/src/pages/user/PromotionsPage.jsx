import { useEffect, useState } from "react";
import ErrorBox from "../../components/ErrorBox";
import Loading from "../../components/Loading";
import { movieService } from "../../services/movieService";
import { useUserPreferences } from "../../context/UserPreferencesContext";

export default function PromotionsPage() {
  const { t } = useUserPreferences();
  const [promotions, setPromotions] = useState(null);
  const [error, setError] = useState("");
  const [copiedCode, setCopiedCode] = useState("");

  useEffect(() => {
    let active = true;
    movieService.promotions()
      .then((result) => { if (active) setPromotions(result); })
      .catch((loadError) => { if (active) setError(loadError.message); });
    return () => { active = false; };
  }, []);

  async function copyCode(code) {
    try {
      await navigator.clipboard.writeText(code);
      setCopiedCode(code);
      window.setTimeout(() => setCopiedCode((current) => current === code ? "" : current), 1800);
      setError("");
    } catch {
      setError("Không thể sao chép mã trên trình duyệt này. Vui lòng chọn và sao chép mã thủ công.");
    }
  }

  return (
    <section className="container-page promotions-page">
      <header className="promotions-heading">
        <span className="eyebrow">ƯU ĐÃI CINEVO</span>
        <h1 className="page-title">{t("Mã giảm giá")}</h1>
        <p className="muted">{t("Các mã ưu đãi đang được Cinevo áp dụng. Nhấn để sao chép mã.")}</p>
      </header>
      <ErrorBox message={error} />
      {!promotions ? <Loading /> : promotions.length ? (
        <div className="promotion-grid">
          {promotions.map((promotion) => (
            <article className="promotion-card" key={promotion.id}>
              <div className="promotion-discount">
                <strong>{promotion.discount_percent}%</strong>
                <span>{t("ƯU ĐÃI")}</span>
              </div>
              {promotion.image_url && (
                <img className="promotion-image" src={promotion.image_url} alt={`Poster ưu đãi ${promotion.code}`} />
              )}
              <div className="promotion-details">
                <p className="promotion-label">{t("MÃ ƯU ĐÃI")}</p>
                <h2>{promotion.code}</h2>
                <p className="muted">{promotion.description || t("Ưu đãi Cinevo dành cho bạn.")}</p>
                <button className="btn btn-red btn-sm" type="button" onClick={() => copyCode(promotion.code)}>
                  {copiedCode === promotion.code ? t("Đã sao chép") : t("Sao chép mã")}
                </button>
              </div>
            </article>
          ))}
        </div>
      ) : (
        <div className="state-box">{t("Hiện chưa có mã ưu đãi nào đang hoạt động. Hãy quay lại sau nhé.")}</div>
      )}
    </section>
  );
}
