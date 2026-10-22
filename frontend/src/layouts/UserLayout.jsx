import { Outlet, useLocation, useNavigate } from "react-router-dom";
import Navbar from "../components/Navbar";
import Footer from "../components/Footer";
import ChatbotWidget from "../components/ChatbotWidget";
import BackHomeLink from "../components/BackHomeLink";
import WelcomeScreen from "../components/WelcomeScreen";
import { useUserPreferences } from "../context/UserPreferencesContext";
import { useAppearance } from "../context/AppearanceContext";
import { useState } from "react";

export default function UserLayout() {
  const { theme, t } = useUserPreferences();
  const location = useLocation();
  const navigate = useNavigate();
  const { appearance, appearanceLoaded } = useAppearance();
  const [entered, setEntered] = useState(() => sessionStorage.getItem("cinevo-welcome-entered") === "1");
  const isPreview = new URLSearchParams(location.search).get("welcomePreview") === "1";
  const showWelcome = appearanceLoaded && (isPreview || (appearance.welcome_enabled && !entered));
  const isHomePage = location.pathname === "/user";

  function enterSite() {
    if (isPreview) {
      setEntered(true);
      navigate("/user", { replace: true });
      return;
    }
    sessionStorage.setItem("cinevo-welcome-entered", "1");
    setEntered(true);
  }

  return (
    <div className="app-shell" data-theme={theme}>
      {!appearanceLoaded && <div className="welcome-loading" role="status">Đang tải Cinevo...</div>}
      {showWelcome && <WelcomeScreen appearance={appearance} onEnter={enterSite} />}
      {appearanceLoaded && !showWelcome && <>
      <Navbar />
      <main className={`${isHomePage ? "main main-home" : "container main"}`}>
        {!isHomePage && <div className="page-back-row"><BackHomeLink label={t("Về trang chủ")} /></div>}
        <Outlet />
      </main>
      <Footer />
      <ChatbotWidget />
      </>}
    </div>
  );
}
