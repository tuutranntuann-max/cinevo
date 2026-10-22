import { useEffect, useRef, useState } from "react";
import { Link, NavLink, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import BrandLogo from "./BrandLogo";
import { useUserPreferences } from "../context/UserPreferencesContext";
import { commerceService } from "../services/commerceService";

export default function Navbar() {
  const { user, logout } = useAuth();
  const { t } = useUserPreferences();
  const navigate = useNavigate();
  const location = useLocation();
  const [query, setQuery] = useState("");
  const [accountMenuOpen, setAccountMenuOpen] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);
  const [membershipTier, setMembershipTier] = useState("");
  const accountMenuRef = useRef(null);

  useEffect(() => {
    setQuery(new URLSearchParams(location.search).get("q") || "");
    setAccountMenuOpen(false);
    setMenuOpen(false);
  }, [location.pathname, location.search]);

  useEffect(() => {
    let cancelled = false;
    setMembershipTier("");
    if (!user || user.role !== "USER") return undefined;
    commerceService.membership()
      .then((membership) => {
        if (!cancelled) setMembershipTier(membership.active?.tier || "");
      })
      .catch((error) => {
        console.error("Không thể tải hạng thành viên cho ảnh đại diện.", error);
      });
    return () => { cancelled = true; };
  }, [user]);

  useEffect(() => {
    if (!accountMenuOpen) return undefined;
    const closeOnOutsideClick = (event) => {
      if (!accountMenuRef.current?.contains(event.target)) setAccountMenuOpen(false);
    };
    const closeOnEscape = (event) => {
      if (event.key === "Escape") setAccountMenuOpen(false);
    };
    document.addEventListener("pointerdown", closeOnOutsideClick);
    document.addEventListener("keydown", closeOnEscape);
    return () => {
      document.removeEventListener("pointerdown", closeOnOutsideClick);
      document.removeEventListener("keydown", closeOnEscape);
    };
  }, [accountMenuOpen]);

  const signOut = () => {
    setAccountMenuOpen(false);
    logout();
    navigate("/user");
  };

  return (
    <header className={`navbar${menuOpen ? " is-menu-open" : ""}`}>
      <div className="container navbar-inner">
        <Link to="/user" className="logo brand-logo-link" aria-label={`CINEVO - ${t("Về trang chủ")}`}>
          <BrandLogo />
        </Link>
        <div className="nav-right">
          {user ? (
            <>
              {["MANAGER", "EMPLOYEE"].includes(user.role) && (
                <Link className="btn btn-ghost btn-sm nav-manager-link" to="/manager">
                  <svg viewBox="0 0 24 24" aria-hidden="true">
                    <path d="M4 20V8l8-4 8 4v12M8 20v-5h8v5M4 9h16" />
                  </svg>
                  {t("Quản lý rạp")}
                </Link>
              )}
              <div className="account-menu" ref={accountMenuRef}>
                <button
                  className={`btn btn-ghost account-menu-trigger${accountMenuOpen ? " is-open" : ""}`}
                  type="button"
                  aria-label={`Tài khoản ${user.full_name}`}
                  aria-expanded={accountMenuOpen}
                  aria-controls="navbar-account-menu"
                  title={`${user.full_name} · ${user.email}`}
                  onClick={() => setAccountMenuOpen((open) => !open)}
                >
                  <span className={`account-avatar${membershipTier ? ` membership-${membershipTier.toLowerCase()}` : ""}`} aria-hidden="true">
                    {user.avatar_url
                      ? <img src={user.avatar_url} alt="" />
                      : user.full_name?.trim()?.charAt(0)?.toLocaleUpperCase("vi-VN") || "C"}
                  </span>
                  <svg className="account-menu-chevron" viewBox="0 0 24 24" aria-hidden="true">
                    <path d="m7 10 5 5 5-5" />
                  </svg>
                </button>
                {accountMenuOpen && (
                  <div className="account-menu-popover" id="navbar-account-menu">
                    <div className="account-menu-identity">
                      <span className={`account-avatar account-avatar-large${membershipTier ? ` membership-${membershipTier.toLowerCase()}` : ""}`} aria-hidden="true">
                        {user.avatar_url
                          ? <img src={user.avatar_url} alt="" />
                          : user.full_name?.trim()?.charAt(0)?.toLocaleUpperCase("vi-VN") || "C"}
                      </span>
                      <span className="account-menu-identity-copy">
                        <strong>{user.full_name}</strong>
                        <small>{user.email}</small>
                      </span>
                    </div>
                    <nav className="account-menu-links" aria-label="Menu tài khoản">
                      <Link to="/user/profile" onClick={() => setAccountMenuOpen(false)}>
                        <span className="account-menu-icon" aria-hidden="true">♙</span>
                        {t("Hồ sơ cá nhân")}
                      </Link>
                      <Link to="/user/profile#history" onClick={() => setAccountMenuOpen(false)}>
                        <span className="account-menu-icon" aria-hidden="true">↺</span>
                        {t("Lịch sử giao dịch")}
                      </Link>
                      <Link to="/user/my-tickets" onClick={() => setAccountMenuOpen(false)}>
                        <span className="account-menu-icon" aria-hidden="true">▤</span>
                        {t("Vé của tôi")}
                      </Link>
                      <Link to="/user/membership" onClick={() => setAccountMenuOpen(false)}>
                        <span className="account-menu-icon" aria-hidden="true">✦</span>
                        {t("Gói thành viên")}
                      </Link>
                      <Link to="/user/shop" onClick={() => setAccountMenuOpen(false)}>
                        <span className="account-menu-icon" aria-hidden="true">▢</span>
                        {t("Cửa hàng Cinevo")}
                      </Link>
                      <Link to="/user/settings" onClick={() => setAccountMenuOpen(false)}>
                        <span className="account-menu-icon" aria-hidden="true">⚙</span>
                        {t("Cài đặt")}
                      </Link>
                    </nav>
                    <button className="account-menu-logout" type="button" onClick={signOut}>
                      <span className="account-menu-icon" aria-hidden="true">↪</span>
                      {t("Đăng xuất")}
                    </button>
                  </div>
                )}
              </div>
            </>
          ) : (
            <>
              <Link className="btn btn-ghost btn-sm" to="/user/login">{t("Đăng nhập")}</Link>
              <Link className="btn btn-red btn-sm" to="/user/register">{t("Đăng ký")}</Link>
            </>
          )}
          <Link className="btn btn-ghost btn-sm settings-quick-link" to="/user/settings"
            aria-label={t("Cài đặt")} title={t("Cài đặt")}>⚙</Link>
          <button
            className="btn btn-ghost navbar-menu-toggle"
            type="button"
            aria-label={menuOpen ? t("Đóng menu") : t("Mở menu")}
            aria-expanded={menuOpen}
            aria-controls="navbar-mobile-menu"
            onClick={() => setMenuOpen((open) => !open)}
          >
            <svg viewBox="0 0 24 24" aria-hidden="true">
              {menuOpen
                ? <path d="m6 6 12 12M18 6 6 18" />
                : <path d="M4 7h16M4 12h16M4 17h16" />}
            </svg>
          </button>
        </div>
        <div className="navbar-menu" id="navbar-mobile-menu">
          <form className="nav-search" onSubmit={(event) => {
            event.preventDefault();
            const search = query.trim();
            navigate(search ? `/user/movies?q=${encodeURIComponent(search)}` : "/user/movies");
          }}>
            <input name="q" type="search" placeholder={t("Tìm phim...")} aria-label={t("Tìm phim")}
              value={query} onChange={(event) => setQuery(event.target.value)} />
            <button className="btn btn-ghost btn-sm nav-icon-button" type="submit" aria-label={t("Tìm phim")} title={t("Tìm phim")}>
              <svg viewBox="0 0 24 24" aria-hidden="true">
                <circle cx="10.8" cy="10.8" r="6.8" />
                <path d="m16 16 4.2 4.2" />
              </svg>
            </button>
          </form>
          <nav className="nav-links" aria-label="Điều hướng chính">
            <NavLink className="nav-link" to="/user/movies">
              <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 5h16v14H4zM4 9h16M8 5v4m8-4v4m-8 4v6m8-6v6" /></svg>
              {t("Vé phim")}
            </NavLink>
            <NavLink className="nav-link" to="/user/watch">
              <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M5 4.5v15l14-7.5z" /></svg>
              {t("Xem phim")}
            </NavLink>
            <NavLink className="nav-link" to="/user/cinemas">
              <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 20V8l8-4 8 4v12M8 20v-5h8v5M4 9h16M8 9v2m4-2v2m4-2v2" /></svg>
              {t("Rạp")}
            </NavLink>
            <NavLink className="nav-link" to="/user/shop">
              <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 8h16l1 12H3L4 8Zm3 0a5 5 0 0 1 10 0M8 12v.01M16 12v.01" /></svg>
              {t("Shop")}
            </NavLink>
            <NavLink className="nav-link" to="/user/membership">
              <svg viewBox="0 0 24 24" aria-hidden="true"><path d="m12 3 2.4 5 5.5.8-4 3.9.9 5.5-4.8-2.6-4.8 2.6.9-5.5-4-3.9 5.5-.8L12 3Z" /></svg>
              {t("Thành viên")}
            </NavLink>
            <NavLink className="nav-link" to="/user/promotions">
              <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M20 12 12 20 3 11V4h7zM7 8h.01" /><path d="m9 15 6-6" /></svg>
              {t("Mã giảm giá")}
            </NavLink>
            <NavLink className="nav-link" to="/user/events">
              <svg viewBox="0 0 24 24" aria-hidden="true"><rect x="4" y="6" width="16" height="14" rx="2" /><path d="M8 4v4m8-4v4M4 10h16m-12 4h2m3 0h2" /></svg>
              {t("Sự kiện")}
            </NavLink>
            <NavLink className="nav-link" to="/user/news">
              <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M5 4h14v16H5zM8 8h8M8 12h8m-8 4h5" /></svg>
              {t("Tin tức")}
            </NavLink>
            <NavLink className="nav-link" to="/staff/register">
              <svg viewBox="0 0 24 24" aria-hidden="true"><rect x="3" y="7" width="18" height="13" rx="2" /><path d="M8 7V5h8v2m-4 0v4m-3 0h6" /></svg>
              {t("Tuyển dụng")}
            </NavLink>
            {user && (
              <NavLink className="nav-link" to="/user/my-tickets">
                <svg viewBox="0 0 24 24" aria-hidden="true">
                  <path d="M4 6h16a1 1 0 0 1 1 1v3a2 2 0 0 0 0 4v3a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1v-3a2 2 0 0 0 0-4V7a1 1 0 0 1 1-1Z" />
                  <path d="M13 6v2m0 3v2m0 3v2" />
                </svg>
                {t("Vé của tôi")}
              </NavLink>
            )}
          </nav>
        </div>
      </div>
    </header>
  );
}
