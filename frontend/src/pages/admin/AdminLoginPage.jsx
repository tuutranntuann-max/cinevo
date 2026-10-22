import { Link, useLocation, useNavigate } from "react-router-dom";
import AuthPanel from "../../components/AuthPanel";
import BackHomeLink from "../../components/BackHomeLink";
import BrandLogo from "../../components/BrandLogo";
import { useAuth } from "../../context/AuthContext";

export default function AdminLoginPage() {
  const { logout } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();
  const requestedPath = location.state?.from;
  const destination = requestedPath?.startsWith("/admin/") ? requestedPath : "/admin";

  async function onSuccess(user) {
    if (user.role !== "ADMIN") {
      logout();
      throw new Error("Tài khoản này không có quyền quản trị CINEVOADM.");
    }
    navigate(destination, { replace: true });
  }

  return (
    <main className="admin-login">
      <section className="admin-login-card">
        <Link to="/admin/login" className="logo brand-logo-link admin-login-brand" aria-label="CINEVOADM">
          <BrandLogo brand="CINEVOADM" />
        </Link>
        <p className="muted center">Đăng nhập dành riêng cho quản trị viên</p>
        <AuthPanel initialView="login" onSuccess={onSuccess} translateUi={false} />
        <BackHomeLink className="admin-login-home" />
      </section>
    </main>
  );
}
