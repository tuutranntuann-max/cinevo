import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import ErrorBox from "../../components/ErrorBox";
import { useAuth } from "../../context/AuthContext";
import { bookingService } from "../../services/bookingService";
import { commerceService } from "../../services/commerceService";
import { authService } from "../../services/authService";
import { formatVND } from "../../utils/format";
import { useUserPreferences } from "../../context/UserPreferencesContext";

export default function ProfilePage() {
  const { user, setUser } = useAuth();
  const { t } = useUserPreferences();
  const [form, setForm] = useState({ full_name: user.full_name, phone: user.phone || "" });
  const [msg, setMsg] = useState("");
  const [error, setError] = useState("");
  const [avatarFile, setAvatarFile] = useState(null);
  const [avatarPreview, setAvatarPreview] = useState("");
  const [avatarBusy, setAvatarBusy] = useState(false);
  const [history, setHistory] = useState({ bookings: [], memberships: [], shopOrders: [] });

  useEffect(() => {
    if (!avatarFile) {
      setAvatarPreview("");
      return undefined;
    }
    const preview = URL.createObjectURL(avatarFile);
    setAvatarPreview(preview);
    return () => URL.revokeObjectURL(preview);
  }, [avatarFile]);

  useEffect(() => {
    Promise.all([bookingService.mine(), commerceService.membership(), commerceService.shopOrders()])
      .then(([bookings, membership, shopOrders]) => setHistory({
        bookings,
        memberships: membership.history,
        shopOrders,
      }))
      .catch((e) => setError(e.message));
  }, []);

  const save = async (e) => {
    e.preventDefault(); setMsg(""); setError("");
    try { const d = await authService.updateMe(form); setUser(d.user); setMsg("Đã lưu thay đổi."); }
    catch (err) { setError(err.message); }
  };

  const uploadAvatar = async () => {
    if (!avatarFile) return;
    setAvatarBusy(true);
    setError("");
    setMsg("");
    try {
      const result = await authService.uploadAvatar(avatarFile);
      setUser(result.user);
      setAvatarFile(null);
      setMsg("Đã cập nhật ảnh đại diện.");
    } catch (uploadError) {
      setError(uploadError.message);
    } finally {
      setAvatarBusy(false);
    }
  };

  const removeAvatar = async () => {
    setAvatarBusy(true);
    setError("");
    setMsg("");
    try {
      const result = await authService.deleteAvatar();
      setUser(result.user);
      setAvatarFile(null);
      setMsg("Đã xóa ảnh đại diện.");
    } catch (removeError) {
      setError(removeError.message);
    } finally {
      setAvatarBusy(false);
    }
  };

  return (
    <section className="narrow">
      <h1 className="page-title">{t("Hồ sơ cá nhân")}</h1>
      <form className="auth-panel plain" onSubmit={save}>
        <ErrorBox message={error} />
        {msg && <div className="success">{msg}</div>}
        <div className="profile-avatar-editor">
          <div className="profile-avatar-preview" aria-label={t("Ảnh đại diện")}>
            {avatarPreview || user.avatar_url
              ? <img src={avatarPreview || user.avatar_url} alt={t("Ảnh đại diện của bạn")} />
              : <span>{user.full_name?.trim()?.charAt(0)?.toLocaleUpperCase("vi-VN") || "C"}</span>}
          </div>
          <div className="profile-avatar-controls">
            <strong>{t("Ảnh đại diện")}</strong>
            <p className="muted small">{t("Chọn ảnh JPG, PNG hoặc WEBP, tối đa 5 MB.")}</p>
            <label className="btn btn-ghost btn-sm profile-avatar-select">
              {t("Chọn ảnh")}
              <input type="file" accept="image/jpeg,image/png,image/webp,.jpg,.jpeg,.png,.webp"
                onChange={(event) => setAvatarFile(event.target.files?.[0] || null)} />
            </label>
            <div className="profile-avatar-actions">
              <button className="btn btn-red btn-sm" type="button" disabled={!avatarFile || avatarBusy}
                onClick={uploadAvatar}>
                {avatarBusy ? t("Đang tải ảnh...") : t("Cập nhật ảnh")}
              </button>
              {user.avatar_url && (
                <button className="btn btn-ghost btn-sm" type="button" disabled={avatarBusy}
                  onClick={removeAvatar}>{t("Xóa ảnh")}</button>
              )}
            </div>
            {avatarFile && <span className="muted small">{avatarFile.name}</span>}
          </div>
        </div>
        <p className="notice">{t("Mã khách hàng của bạn:")} <b>{user.customer_code || `CV${String(user.id).padStart(6, "0")}`}</b></p>
        <label>{t("Email")}<input value={user.email} disabled /></label>
        <label>{t("Họ và tên")}<input required value={form.full_name} onChange={(e) => setForm({ ...form, full_name: e.target.value })} /></label>
        <label>{t("Số điện thoại")}<input type="tel" value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} /></label>
        <p className="muted small">{t("Vai trò:")} {user.role} · {t("Trạng thái:")} {user.status}</p>
        <button className="btn btn-red">{t("Lưu thay đổi")}</button>
      </form>
      <section className="profile-history" id="history">
        <div className="actions"><h2>{t("Lịch sử giao dịch")}</h2><Link className="btn btn-outline btn-sm" to="/user/my-tickets">{t("Vé của tôi")}</Link></div>
        {!history.bookings.length && !history.memberships.length && !history.shopOrders.length
          ? <p className="state-box">{t("Chưa có giao dịch.")}</p>
          : <div className="list">
            {history.bookings.map((item) => <article className="card ticket-row" key={`ticket-${item.id}`}>
              <div><b>{item.movie.title}</b><p className="muted small">Mã {item.code} · {item.status === "PAID" ? "Đã thanh toán" : item.status === "PENDING" ? "Chờ xác nhận" : item.status}</p></div>
              <b>{formatVND(item.total_amount)}</b>
            </article>)}
            {history.memberships.map((item) => <article className="card ticket-row" key={`membership-${item.id}`}>
              <div><b>Gói {item.tier}</b><p className="muted small">Mã {item.payment_ref} · {item.status}</p></div>
              <b>{formatVND(item.amount)}</b>
            </article>)}
            {history.shopOrders.map((item) => <article className="card ticket-row" key={`shop-${item.id}`}>
              <div><b>Đơn Shop {item.code}</b><p className="muted small">Nhận tại {item.pickup_cinema} · {item.status}</p></div>
              <b>{formatVND(item.total_amount)}</b>
            </article>)}
          </div>}
      </section>
    </section>
  );
}
