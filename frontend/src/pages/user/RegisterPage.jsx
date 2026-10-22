import { useNavigate } from "react-router-dom";
import AuthPanel from "../../components/AuthPanel";
import { useBooking } from "../../context/BookingContext";

// Đăng ký luôn tạo tài khoản role USER (backend không nhận role từ client).
export default function RegisterPage() {
  const navigate = useNavigate();
  const { booking } = useBooking();
  return (
    <section className="narrow">
      <AuthPanel initialView="register" onSuccess={() => navigate(booking.seats.length ? "/user/checkout" : "/user", { replace: true })} />
    </section>
  );
}
