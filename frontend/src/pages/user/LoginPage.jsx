import { Link, useLocation, useNavigate } from "react-router-dom";
import AuthPanel from "../../components/AuthPanel";
import { useBooking } from "../../context/BookingContext";
import { useUserPreferences } from "../../context/UserPreferencesContext";

// Sau khi đăng nhập: ADMIN -> /admin, MANAGER -> /manager, USER -> trang trước đó hoặc /user.
export const redirectByRole = (user, from) =>
  user.role === "ADMIN" ? "/admin" : ["MANAGER", "EMPLOYEE"].includes(user.role) ? "/manager" : from || "/user";

export default function LoginPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const { t } = useUserPreferences();
  const { booking } = useBooking();
  // Nếu đang có đơn đặt vé dở thì quay lại bước Xác nhận, không bắt chọn lại từ đầu.
  const from = location.state?.from || (booking.seats.length ? "/user/checkout" : undefined);
  return (
    <section className="narrow">
      {location.state?.from === "/user/profile" && (
        <p className="notice" role="status">{t("Đăng nhập để xem thông tin hồ sơ của bạn.")}</p>
      )}
      <AuthPanel initialView="login" onSuccess={(u) => navigate(redirectByRole(u, from), { replace: true })} />
      <p className="muted center small">{t("Bạn chưa cần đăng nhập để xem phim.")} <Link className="link" to="/user">{t("Về trang chủ")}</Link></p>
    </section>
  );
}
