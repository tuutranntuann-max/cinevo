// Khung dùng chung cho Manager/Admin: thanh bên + nội dung.
import { useEffect, useState } from "react";
import { Link, NavLink, Outlet, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import BrandLogo from "../components/BrandLogo";
import BackHomeLink from "../components/BackHomeLink";
import { api } from "../services/api";

export default function PanelLayout({ title, base, links, brand = "CINEVO" }) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [supportUnread, setSupportUnread] = useState(0);
  const [supportError, setSupportError] = useState("");
  const [pendingApplications, setPendingApplications] = useState(0);
  const [pendingResetRequests, setPendingResetRequests] = useState(0);

  useEffect(() => {
    let active = true;
    const refreshUnread = async () => {
      try {
        const inbox = await api.get("/support/staff/conversations?status=open");
        if (active) {
          setSupportUnread(inbox.unread_count);
          setSupportError("");
        }
      } catch (error) {
        if (active) setSupportError(error.message);
      }
    };
    refreshUnread();
    const timer = window.setInterval(refreshUnread, 5000);
    return () => {
      active = false;
      window.clearInterval(timer);
    };
  }, []);

  useEffect(() => {
    if (base !== "/admin") return undefined;
    let active = true;
    const refreshApplications = async () => {
      try {
        const [applications, resets] = await Promise.all([
          api.get("/staff-accounts/applications/count"),
          api.get("/staff-accounts/password-resets/count"),
        ]);
        if (active) {
          setPendingApplications(applications.pending_count);
          setPendingResetRequests(resets.pending_count);
        }
      } catch (error) {
        if (active) console.error("Không thể tải số hồ sơ nhân viên đang chờ duyệt.", error);
      }
    };
    refreshApplications();
    const timer = window.setInterval(refreshApplications, 10000);
    return () => {
      active = false;
      window.clearInterval(timer);
    };
  }, [base]);

  return (
    <div className="panel">
      <aside className="sidebar">
        <Link to="/user" className="logo brand-logo-link panel-brand" aria-label={brand}>
          <BrandLogo brand={brand} />
        </Link>
        <p className="muted small">{title}</p>
        <nav>
          {links.map(([path, label]) => (
            <NavLink key={path} to={`${base}${path}`} end={path === ""}
              title={path === "/support" && supportError ? `Thông báo chat chưa tải được: ${supportError}` : undefined}>
              {label}
              {path === "/support" && supportUnread > 0 && (
                <span className="panel-nav-badge" aria-label={`${supportUnread} tin nhắn chưa đọc`}>
                  {supportUnread > 99 ? "99+" : supportUnread}
                </span>
              )}
              {path === "/staff-applications" && pendingApplications + pendingResetRequests > 0 && (
                <span className="panel-nav-badge" aria-label={`${pendingApplications} hồ sơ và ${pendingResetRequests} yêu cầu đặt lại mật khẩu đang chờ`}>
                  {pendingApplications + pendingResetRequests > 99 ? "99+" : pendingApplications + pendingResetRequests}
                </span>
              )}
            </NavLink>
          ))}
        </nav>
        <div className="sidebar-foot">
          <p className="small">{user?.full_name}<br /><span className="muted">{user?.role}</span></p>
          <BackHomeLink className="btn-sm back-home-link-panel" />
          <button className="btn btn-ghost btn-sm" onClick={() => {
            logout();
            navigate(user?.role === "ADMIN" ? "/admin/login" : "/manager/login");
          }}>Đăng xuất</button>
        </div>
      </aside>
      <div className="panel-main"><Outlet /></div>
    </div>
  );
}
