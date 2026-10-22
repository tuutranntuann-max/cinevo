import { useCallback, useEffect, useMemo, useState } from "react";
import ErrorBox from "../../components/ErrorBox";
import { useAuth } from "../../context/AuthContext";
import { api } from "../../services/api";
import { commerceService } from "../../services/commerceService";
import { formatVND } from "../../utils/format";
import { PAYMENT_BANKS } from "../../data/paymentInstitutions";

const EMPTY_SETTINGS = {
  bank_name: "",
  bank_bin: "",
  account_number: "",
  account_name: "",
  qr_image_url: "",
  membership_prices: { SILVER: "", GOLD: "", DIAMOND: "" },
};

export default function TransactionManagement() {
  const { user } = useAuth();
  const [rows, setRows] = useState([]);
  const [history, setHistory] = useState([]);
  const [settings, setSettings] = useState(EMPTY_SETTINGS);
  const [selected, setSelected] = useState([]);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  const [settingsSaving, setSettingsSaving] = useState(false);
  const [settingsSaveError, setSettingsSaveError] = useState("");
  const [settingsSaveMessage, setSettingsSaveMessage] = useState("");
  const [lastUpdated, setLastUpdated] = useState(null);

  const load = useCallback(async ({ refreshSettings = false } = {}) => {
    try {
      const requests = [
        commerceService.pendingPayments(),
        commerceService.transactionHistory(),
      ];
      if (refreshSettings) requests.push(commerceService.adminSettings());
      const [pending, transactions, config] = await Promise.all(requests);
      setRows(pending);
      setHistory(transactions);
      setSelected((current) => {
        const pendingKeys = new Set(pending.map((row) => `${row.kind}:${row.id}`));
        return current.filter((key) => pendingKeys.has(key));
      });
      if (config) {
        setSettings({
          ...config,
          membership_prices: Object.fromEntries(
            Object.entries(config.membership_prices || {}).map(([key, value]) => [key, value ?? ""]),
          ),
        });
      }
      setLastUpdated(new Date());
      setError("");
    } catch (e) { setError(e.message); }
  }, []);

  useEffect(() => {
    load({ refreshSettings: true });
    const timer = window.setInterval(() => load(), 5000);
    return () => window.clearInterval(timer);
  }, [load]);

  const selectedItems = useMemo(() => rows.filter((row) => selected.includes(`${row.kind}:${row.id}`)), [rows, selected]);

  const review = async (approved) => {
    if (!selectedItems.length) return setError("Hãy chọn ít nhất một giao dịch.");
    setBusy(true); setError(""); setMessage("");
    try {
      await commerceService.reviewPayments(selectedItems.map(({ kind, id }) => ({ kind, id })), approved);
      setMessage(approved ? `Đã xác nhận ${selectedItems.length} giao dịch.` : `Đã từ chối ${selectedItems.length} giao dịch.`);
      await load();
    } catch (e) { setError(e.message); }
    finally { setBusy(false); }
  };

  const saveSettings = async (event) => {
    event.preventDefault();
    setSettingsSaving(true);
    setSettingsSaveError("");
    setSettingsSaveMessage("");
    setError("");
    setMessage("");
    try {
      const prices = Object.fromEntries(
        Object.entries(settings.membership_prices).map(([tier, value]) => [tier, value === "" ? null : Number(value)]),
      );
      const updated = await commerceService.updateAdminSettings({ ...settings, membership_prices: prices });
      setSettings({ ...updated, membership_prices: Object.fromEntries(
        Object.entries(updated.membership_prices).map(([key, value]) => [key, value ?? ""]),
      ) });
      setSettingsSaveMessage("Đã lưu cấu hình thanh toán và giá gói.");
      setMessage("Đã lưu cấu hình thanh toán và giá gói.");
    } catch (e) {
      setSettingsSaveError(e.message);
      setError(e.message);
    }
    finally { setSettingsSaving(false); }
  };

  const uploadQr = async (event) => {
    const file = event.target.files?.[0];
    if (!file) return;
    setBusy(true); setError(""); setMessage("");
    try {
      const form = new FormData();
      form.append("image", file);
      const result = await api.upload("/content/manage/media", form);
      change("qr_image_url", result.image_url);
      setMessage("Đã tải mã QR lên. Hãy lưu cấu hình để áp dụng.");
    } catch (e) { setError(e.message); }
    finally { setBusy(false); event.target.value = ""; }
  };

  const change = (field, value) => {
    setSettings((current) => ({ ...current, [field]: value }));
    setSettingsSaveError("");
    setSettingsSaveMessage("");
  };

  return (
    <section>
      <h1 className="page-title">Xác nhận thanh toán</h1>
      <ErrorBox message={error} />
      {message && <div className="success">{message}</div>}
      <div className="actions">
        <span className="muted small" role="status">
          Tự cập nhật mỗi 5 giây{lastUpdated ? ` · Cập nhật lúc ${lastUpdated.toLocaleTimeString("vi-VN")}` : ""}
        </span>
        <button className="btn btn-outline btn-sm" onClick={() => load({ refreshSettings: true })}>Làm mới</button>
        <button className="btn btn-red btn-sm" disabled={busy || !selected.length} onClick={() => review(true)}>Xác nhận đã chọn ({selected.length})</button>
        <button className="btn btn-ghost btn-sm" disabled={busy || !selected.length} onClick={() => review(false)}>Từ chối đã chọn</button>
      </div>
      <div className="table-wrap">
        <table className="data-table">
          <thead><tr>
            <th><input type="checkbox" aria-label="Chọn tất cả" checked={rows.length > 0 && selected.length === rows.length}
              onChange={(event) => setSelected(event.target.checked ? rows.map((row) => `${row.kind}:${row.id}`) : [])} /></th>
            <th>Loại</th><th>Khách hàng</th><th>Số tiền</th><th>Mã chuyển khoản</th><th>Ngày tạo</th>
          </tr></thead>
          <tbody>{rows.map((row) => {
            const key = `${row.kind}:${row.id}`;
            return <tr key={key}>
              <td><input type="checkbox" checked={selected.includes(key)}
                onChange={(event) => setSelected((current) => event.target.checked ? [...current, key] : current.filter((value) => value !== key))} /></td>
              <td>{row.kind === "BOOKING" ? "Vé phim" : row.kind === "MEMBERSHIP" ? "Thành viên" : "Shop"}</td>
              <td>{row.customer_name}<br /><small>{row.customer_email}</small></td>
              <td>{formatVND(row.amount)}</td>
              <td><code>{row.transaction_ref}</code></td>
              <td>{row.created_at ? new Date(row.created_at).toLocaleString("vi-VN") : "—"}</td>
            </tr>;
          })}{!rows.length && <tr><td colSpan="6" className="muted">Không có giao dịch chờ xác nhận.</td></tr>}</tbody>
        </table>
      </div>
      <h2 className="section-title">Lịch sử giao dịch gần đây</h2>
      <div className="table-wrap">
        <table className="data-table">
          <thead><tr><th>Loại</th><th>Khách hàng</th><th>Số tiền</th><th>Mã giao dịch</th><th>Trạng thái</th><th>Ngày tạo</th></tr></thead>
          <tbody>{history.map((row) => <tr key={`${row.kind}:${row.id}`}>
            <td>{row.kind === "BOOKING" ? "Vé phim" : row.kind === "MEMBERSHIP" ? "Thành viên" : "Shop"}</td>
            <td>{row.customer_name}<br /><small>{row.customer_email}</small></td>
            <td>{formatVND(row.amount)}</td><td><code>{row.transaction_ref}</code></td><td>{row.status}</td>
            <td>{row.created_at ? new Date(row.created_at).toLocaleString("vi-VN") : "—"}</td>
          </tr>)}{!history.length && <tr><td colSpan="6" className="muted">Chưa có giao dịch.</td></tr>}</tbody>
        </table>
      </div>

      {user?.role === "ADMIN" && (
        <form className="auth-panel plain commerce-settings" onSubmit={saveSettings}>
          <h2>Cấu hình tài khoản nhận tiền</h2>
          <p className="muted small">Chọn ngân hàng nhận tiền để tự tạo QR VietQR theo số tiền và mã giao dịch. Ảnh QR riêng là tùy chọn.</p>
          <label>Ngân hàng nhận tiền
            <select value={settings.bank_bin} onChange={(event) => {
              const bank = PAYMENT_BANKS.find((item) => item.bin === event.target.value);
              setSettings((current) => ({ ...current, bank_bin: event.target.value, bank_name: bank?.name || "" }));
              setSettingsSaveError("");
              setSettingsSaveMessage("");
            }}>
              <option value="">Chọn ngân hàng</option>
              {PAYMENT_BANKS.map((bank) => <option value={bank.bin} key={`${bank.bin}-${bank.name}`}>{bank.name}</option>)}
            </select>
          </label>
          <label>Tên ngân hàng<input value={settings.bank_name} onChange={(e) => change("bank_name", e.target.value)} /></label>
          <label>Số tài khoản<input value={settings.account_number} onChange={(e) => change("account_number", e.target.value)} /></label>
          <label>Tên chủ tài khoản<input value={settings.account_name} onChange={(e) => change("account_name", e.target.value)} /></label>
          <label>URL ảnh QR riêng (không bắt buộc)
            <input type="text" inputMode="url" placeholder="Để trống nếu không dùng URL riêng"
              value={settings.qr_image_url} onChange={(e) => change("qr_image_url", e.target.value)} />
          </label>
          <p className="muted small">Nếu không tải ảnh riêng, hệ thống tự tạo VietQR có sẵn số tiền và nội dung chuyển khoản cho từng giao dịch.</p>
          <label>Tải ảnh mã QR (JPG, PNG, WEBP)
            <input type="file" accept="image/jpeg,image/png,image/webp" onChange={uploadQr} disabled={busy} />
          </label>
          {settings.qr_image_url && <img className="bank-transfer-qr" src={settings.qr_image_url} alt="Mã QR ngân hàng đã cấu hình" />}
          <h3>Giá gói thành viên (VND / 30 ngày)</h3>
          {[["SILVER", "Bạc"], ["GOLD", "Vàng"], ["DIAMOND", "Kim cương"]].map(([tier, label]) => (
            <label key={tier}>{label}<input type="number" min="1" step="1" value={settings.membership_prices[tier]}
              onChange={(e) => {
                setSettingsSaveError("");
                setSettingsSaveMessage("");
                setSettings((current) => ({
                  ...current,
                  membership_prices: { ...current.membership_prices, [tier]: e.target.value },
                }));
              }} /></label>
          ))}
          {settingsSaving && (
            <div className="settings-save-progress" role="progressbar" aria-label="Đang lưu cấu hình" aria-valuetext="Đang lưu">
              <span />
            </div>
          )}
          {settingsSaveError && <div className="alert" role="alert">{settingsSaveError}</div>}
          {settingsSaveMessage && <div className="success" role="status">{settingsSaveMessage}</div>}
          <button className="btn btn-red" disabled={settingsSaving}>
            {settingsSaving ? "Đang lưu cấu hình..." : "Lưu cấu hình"}
          </button>
        </form>
      )}
    </section>
  );
}
