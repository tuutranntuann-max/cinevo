// Vé điện tử sau khi thanh toán: có mã vé + QR.
import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import ErrorBox from "../../components/ErrorBox";
import Loading from "../../components/Loading";
import TicketCard from "../../components/TicketCard";
import { bookingService } from "../../services/bookingService";
import { commerceService } from "../../services/commerceService";
import PaymentMethodInstructions from "../../components/PaymentMethodInstructions";
import { useUserPreferences } from "../../context/UserPreferencesContext";

export default function BookingSuccessPage() {
  const { t } = useUserPreferences();
  const { code } = useParams();
  const [ticket, setTicket] = useState(null);
  const [error, setError] = useState("");
  const [settings, setSettings] = useState(null);

  useEffect(() => {
    bookingService.detail(code).then(setTicket).catch((e) => setError(e.message));
    commerceService.settings().then(setSettings).catch((e) => setError(e.message));
  }, [code]);

  if (error) return <ErrorBox message={error} />;
  if (!ticket) return <Loading />;
  if (ticket.status !== "PAID") return (
    <section className="narrow center">
      <h1 className="page-title">{ticket.status === "CANCELLED" ? t("Giao dịch đã kết thúc") : t("Đang chờ xác nhận thanh toán")}</h1>
      {ticket.status === "PENDING" && <PaymentMethodInstructions settings={settings} amount={ticket.total_amount} reference={ticket.code} />}
      <p className="hint">{t("Vé chỉ có hiệu lực sau khi nhân viên, quản lý hoặc Admin xác nhận giao dịch.")}</p>
      <Link className="btn btn-outline" to="/user/my-tickets">{t("Kiểm tra vé của tôi")}</Link>
    </section>
  );
  return (
    <section className="narrow center">
      <h1 className="page-title">{t("Đặt vé thành công")}</h1>
      <TicketCard ticket={ticket} />
      <div className="actions center-actions">
        <Link className="btn btn-outline" to="/user/my-tickets">{t("Vé của tôi")}</Link>
        <Link className="btn btn-red" to="/user">{t("Về trang chủ")}</Link>
      </div>
    </section>
  );
}
