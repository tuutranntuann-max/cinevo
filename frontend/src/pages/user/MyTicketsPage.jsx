// Vé của tôi: nhóm "Sắp tới" (có nút Xem QR) và "Đã xem".
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import ErrorBox from "../../components/ErrorBox";
import Loading from "../../components/Loading";
import TicketCard from "../../components/TicketCard";
import { bookingService } from "../../services/bookingService";
import { useUserPreferences } from "../../context/UserPreferencesContext";

export default function MyTicketsPage() {
  const { t: translate, language } = useUserPreferences();
  const [tickets, setTickets] = useState(null);
  const [error, setError] = useState("");
  const [open, setOpen] = useState(null);

  useEffect(() => { bookingService.mine().then(setTickets).catch((e) => setError(e.message)); }, []);
  if (error) return <ErrorBox message={error} />;
  if (!tickets) return <Loading />;

  const upcoming = tickets.filter((t) => t.is_upcoming);
  const past = tickets.filter((t) => !t.is_upcoming && t.status === "PAID");
  const pending = tickets.filter((t) => t.status === "PENDING");

  const Row = ({ t, canQr }) => (
    <article className="card ticket-row">
      <div>
        <h3>{t.movie.title}</h3>
        <p className="muted small">{new Date(t.start_time).toLocaleDateString(language === "en" ? "en-US" : "vi-VN")} - {new Date(t.start_time).toLocaleTimeString(language === "en" ? "en-US" : "vi-VN", { hour: "2-digit", minute: "2-digit" })} · {t.cinema}</p>
        <p className="small">{translate("Ghế")} {t.seats.join(", ")} · {translate("Mã vé")} {t.code}</p>
      </div>
      {canQr && <button className="btn btn-outline btn-sm" onClick={() => setOpen(t)}>{translate("Xem QR")}</button>}
    </article>
  );

  return (
    <section>
      <h1 className="page-title">{translate("Vé của tôi")}</h1>
      {pending.length > 0 && (
        <>
          <h2 className="section-title">{translate("Chờ xác nhận thanh toán")}</h2>
          {pending.map((ticket) => <Row key={ticket.code} t={ticket} canQr={false} />)}
        </>
      )}
      <h2 className="section-title">{translate("Sắp tới")}</h2>
      {upcoming.filter((t) => t.status === "PAID").length ? upcoming.filter((t) => t.status === "PAID").map((t) => <Row key={t.code} t={t} canQr />) : (
        <div className="state-box">{translate("Bạn chưa có vé sắp tới.")} <Link className="link" to="/user/movies">{translate("Đặt vé ngay")}</Link></div>
      )}
      <h2 className="section-title">{translate("Đã xem")}</h2>
      {past.length ? past.map((t) => <Row key={t.code} t={t} />) : <div className="state-box">{translate("Chưa có vé đã xem.")}</div>}

      {open && (
        <div className="modal-backdrop" onClick={() => setOpen(null)}>
          <div className="modal" role="dialog" aria-modal="true" onClick={(e) => e.stopPropagation()}>
            <button className="modal-close" onClick={() => setOpen(null)} aria-label={translate("Đóng")}>×</button>
            <TicketCard ticket={open} />
          </div>
        </div>
      )}
    </section>
  );
}
