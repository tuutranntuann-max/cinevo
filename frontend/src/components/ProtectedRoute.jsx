// Chặn route theo đăng nhập + role. Backend vẫn kiểm tra lại quyền ở mọi API.
import { Navigate, Outlet, useLocation } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import Loading from "./Loading";

export default function ProtectedRoute({ roles, children, loginPath = "/user/login" }) {
  const { user, loading } = useAuth();
  const location = useLocation();

  if (loading) return <Loading />;
  if (!user) return <Navigate to={loginPath} state={{ from: location.pathname }} replace />;
  if (roles && !roles.includes(user.role)) return <Navigate to="/user" replace />;
  return children || <Outlet />;
}
