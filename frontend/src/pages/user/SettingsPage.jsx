import { useUserPreferences } from "../../context/UserPreferencesContext";

export default function SettingsPage() {
  const { theme, language, setTheme, setLanguage, t } = useUserPreferences();

  return (
    <section className="user-settings-page">
      <p className="eyebrow">CINEVO</p>
      <h1 className="page-title">{t("Cài đặt")}</h1>
      <p className="muted">{t("Cài đặt giao diện và ngôn ngữ")}</p>

      <section className="card user-settings-card" aria-labelledby="settings-theme-title">
        <div>
          <h2 id="settings-theme-title">{t("Giao diện")}</h2>
          <p className="muted small">{t("Chọn chế độ sáng hoặc tối cho khu vực khách hàng.")}</p>
        </div>
        <div className="settings-choice-row" role="group" aria-label={t("Giao diện")}>
          <button type="button" className={`settings-choice${theme === "light" ? " selected" : ""}`}
            aria-pressed={theme === "light"} onClick={() => setTheme("light")}>
            <span className="settings-theme-swatch settings-theme-swatch-light" aria-hidden="true">Aa</span>
            {t("Chế độ sáng")}
          </button>
          <button type="button" className={`settings-choice${theme === "dark" ? " selected" : ""}`}
            aria-pressed={theme === "dark"} onClick={() => setTheme("dark")}>
            <span className="settings-theme-swatch settings-theme-swatch-dark" aria-hidden="true">Aa</span>
            {t("Chế độ tối")}
          </button>
        </div>
      </section>

      <section className="card user-settings-card" aria-labelledby="settings-language-title">
        <div>
          <h2 id="settings-language-title">{t("Ngôn ngữ")}</h2>
          <p className="muted small">{t("Chọn ngôn ngữ hiển thị trên website.")}</p>
        </div>
        <div className="settings-choice-row" role="group" aria-label={t("Ngôn ngữ")}>
          <button type="button" className={`settings-choice${language === "vi" ? " selected" : ""}`}
            aria-pressed={language === "vi"} onClick={() => setLanguage("vi")}>
            🇻🇳 {t("Tiếng Việt")}
          </button>
          <button type="button" className={`settings-choice${language === "en" ? " selected" : ""}`}
            aria-pressed={language === "en"} onClick={() => setLanguage("en")}>
            🇬🇧 {t("Tiếng Anh")}
          </button>
        </div>
      </section>
      <p className="hint">{t("Tùy chọn được lưu tự động trên thiết bị này.")}</p>
    </section>
  );
}
