import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { useAppearance } from "../context/AppearanceContext";
import { movieService } from "../services/movieService";
import { useUserPreferences } from "../context/UserPreferencesContext";

function FooterPartner({ partner }) {
  const [failedUrls, setFailedUrls] = useState([]);
  useEffect(() => setFailedUrls([]), [partner.logo_url]);
  const content = partner.logo_url && !failedUrls.includes(partner.logo_url)
    ? <img src={partner.logo_url} alt="" onError={() => setFailedUrls((current) => [...current, partner.logo_url])} />
    : <span>{partner.name}</span>;
  return partner.url
    ? <a className="footer-partner" href={partner.url} target="_blank" rel="noreferrer" aria-label={partner.name}>{content}</a>
    : <span className="footer-partner" aria-label={partner.name}>{content}</span>;
}

export default function Footer() {
  const { appearance } = useAppearance();
  const { t } = useUserPreferences();
  const [upcoming, setUpcoming] = useState([]);
  const [movieError, setMovieError] = useState("");

  useEffect(() => {
    if (!appearance.footer_show_upcoming) return undefined;
    let active = true;
    movieService.movies({ status: "coming_soon" })
      .then((movies) => {
        if (active) setUpcoming(movies.slice(0, 9));
      })
      .catch((error) => {
        if (active) setMovieError(error.message);
      });
    return () => { active = false; };
  }, [appearance.footer_show_upcoming]);

  const links = appearance.footer_links || [];
  const partners = appearance.footer_partners || [];

  return (
    <footer className="footer" id="site-footer">
      <div className="container footer-inner">
        {appearance.footer_show_upcoming && (
          <section className="footer-upcoming" aria-labelledby="footer-upcoming-title">
            <h2 id="footer-upcoming-title">{t("PHIM VIỆT SẮP CHIẾU")}</h2>
            {movieError
              ? <p className="footer-state" role="status">Không thể tải danh sách phim sắp chiếu: {movieError}</p>
              : upcoming.length
                ? <div className="footer-upcoming-list">
                    {upcoming.map((movie) => (
                      <Link to={`/user/movies/${movie.id}`} key={movie.id}>{movie.title}</Link>
                    ))}
                  </div>
                : <p className="footer-state">{t("Hiện chưa có phim sắp chiếu.")}</p>}
          </section>
        )}

        <div className="footer-lower">
          <section className="footer-company" aria-label={t("Thông tin công ty")}>
            <img className="footer-brand" src={appearance.logo_media_url || "/cinevo-logo.png"} alt="CINEVO" />
            <div>
              <h2>{appearance.footer_company_name || "CINEVO"}</h2>
              {appearance.footer_tax_code && <p><strong>{t("Số ĐKKD:")}</strong> {appearance.footer_tax_code}</p>}
              {appearance.footer_email && <p><strong>Email:</strong> <a href={`mailto:${appearance.footer_email}`}>{appearance.footer_email}</a></p>}
              {appearance.footer_license && <p>{appearance.footer_license}</p>}
              {appearance.footer_registered && <p>{t("Đăng ký lần đầu ngày")} {appearance.footer_registered}</p>}
              {appearance.footer_address && <p><strong>{t("Địa chỉ:")}</strong> {appearance.footer_address}</p>}
              <nav className="footer-links" aria-label={t("Liên kết thông tin")}>
                {links.map((item, index) => item.url?.startsWith("/") && !item.url.startsWith("//")
                  ? <Link to={item.url} key={`${item.label}-${index}`}>{item.label}</Link>
                  : item.url
                    ? <a href={item.url} key={`${item.label}-${index}`}>{item.label}</a>
                    : <span key={`${item.label}-${index}`}>{item.label}</span>)}
                {appearance.footer_version && <span>{appearance.footer_version}</span>}
              </nav>
            </div>
          </section>

          <section className="footer-partners-section" aria-labelledby="footer-partners-title">
            {appearance.footer_partners_enabled && <>
              <h2 id="footer-partners-title">{t("ĐỐI TÁC")}</h2>
              <div className="footer-partners-layout">
                <div className="footer-partners">
                  {partners.map((partner, index) => <FooterPartner key={`${partner.name}-${index}`} partner={partner} />)}
                </div>
                {appearance.footer_commerce_notice && (
                  <div className="footer-commerce-notice" aria-label={appearance.footer_commerce_notice}>
                    <span aria-hidden="true">✓</span>
                    <strong>{appearance.footer_commerce_notice}</strong>
                  </div>
                )}
              </div>
            </>}
          </section>
        </div>

      </div>
    </footer>
  );
}
