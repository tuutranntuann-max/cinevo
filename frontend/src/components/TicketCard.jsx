// Vé điện tử dạng "ticket stub": phần thông tin + đường đục lỗ + QR.
import { QRCodeSVG } from "qrcode.react";
import { useUserPreferences } from "../context/UserPreferencesContext";

export default function TicketCard({ ticket }) {
  const { t, language } = useUserPreferences();
  return (
    <div className="stub">
      <div className="stub-main">
        <div className="stub-brand">CINEVO</div>
        <h3>{ticket.movie.title}</h3>
        {ticket.movie.director && <p>{t("Đạo diễn:")} {ticket.movie.director}</p>}
        {ticket.movie.cast_members && <p>{t("Diễn viên:")} {ticket.movie.cast_members}</p>}
        <p>{new Date(ticket.start_time).toLocaleDateString(language === "en" ? "en-US" : "vi-VN")} - {new Date(ticket.start_time).toLocaleTimeString(language === "en" ? "en-US" : "vi-VN", { hour: "2-digit", minute: "2-digit" })}</p>
        <p>{ticket.cinema}</p>
        <p>{ticket.room} · {t("Ghế")} {ticket.seats.join(", ")}</p>
        {ticket.foods.length > 0 && <p className="muted small">{ticket.foods.map((f) => `${f.name} ×${f.quantity}`).join(", ")}</p>}
      </div>
      <div className="stub-qr">
        <div className="qr-box"><QRCodeSVG value={ticket.qr_payload} size={132} /></div>
        <p>{t("Mã vé")}</p><b>{ticket.code}</b>
      </div>
    </div>
  );
}
