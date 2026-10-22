import { useCallback, useEffect, useState } from "react";
import ErrorBox from "../../components/ErrorBox";
import Loading from "../../components/Loading";
import { api } from "../../services/api";

const CALLBACK_MESSAGES = {
  connected: "Đã kết nối Gmail. Mã OTP đăng ký sẽ được gửi tự động.",
  denied: "Bạn đã hủy cấp quyền Gmail.",
  error: "Chưa kết nối được Gmail. Kiểm tra cấu hình OAuth rồi thử lại.",
};

function deliveryStatus(status) {
  if (status.connected) return "Đã kết nối Gmail OAuth";
  if (status.configured) return "OAuth đã cấu hình — cần bấm Kết nối Gmail";
  if (status.smtp_configured) return "Đang dùng SMTP — kiểm tra App Password";
  return "Chưa cấu hình dịch vụ gửi email";
}

export default function GmailAssistantPage() {
  const [status, setStatus] = useState(null);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  const [saveState, setSaveState] = useState("idle");
  const [form, setForm] = useState({
    oauth_client_id: "",
    oauth_client_secret: "",
    oauth_redirect_uri: "http://127.0.0.1:5000/api/admin/gmail-assistant/callback",
    oauth_frontend_url: window.location.origin,
    smtp_host: "smtp.gmail.com",
    smtp_port: "465",
    smtp_username: "",
    smtp_password: "",
    smtp_from_email: "",
  });

  const loadStatus = useCallback(async () => {
    setError("");
    try {
      setStatus(await api.get("/admin/gmail-assistant/status"));
    } catch (loadError) {
      setError(loadError.message);
    }
  }, []);

  useEffect(() => {
    const result = new URLSearchParams(window.location.search).get("gmail");
    if (result && CALLBACK_MESSAGES[result]) {
      setMessage(CALLBACK_MESSAGES[result]);
      window.history.replaceState(null, "", window.location.pathname);
    }
    loadStatus();
  }, [loadStatus]);

  async function connect() {
    setBusy(true);
    setError("");
    try {
      const result = await api.post("/admin/gmail-assistant/authorize", {});
      window.location.assign(result.authorization_url);
    } catch (connectError) {
      setError(connectError.message);
      setBusy(false);
    }
  }

  function updateField(event) {
    setForm((current) => ({ ...current, [event.target.name]: event.target.value }));
  }

  async function saveSettings(event) {
    event.preventDefault();
    setBusy(true);
    setSaveState("saving");
    setError("");
    setMessage("");
    const payload = {
      smtp_port: Number(form.smtp_port),
    };
    for (const key of [
      "oauth_client_id",
      "oauth_client_secret",
      "oauth_redirect_uri",
      "oauth_frontend_url",
      "smtp_host",
      "smtp_username",
      "smtp_password",
      "smtp_from_email",
    ]) {
      if (form[key].trim()) payload[key] = form[key].trim();
    }
    try {
      const result = await api.put("/admin/gmail-assistant/settings", payload);
      setMessage(result.message);
      setForm((current) => ({
        ...current,
        oauth_client_id: "",
        oauth_client_secret: "",
        smtp_username: "",
        smtp_password: "",
        smtp_from_email: "",
      }));
      await loadStatus();
      setSaveState("saved");
    } catch (saveError) {
      setError(saveError.message);
      setSaveState("error");
    } finally {
      setBusy(false);
    }
  }

  async function disconnect() {
    setBusy(true);
    setError("");
    setMessage("");
    try {
      const result = await api.post("/admin/gmail-assistant/disconnect", {});
      setMessage(result.message);
      await loadStatus();
    } catch (disconnectError) {
      setError(disconnectError.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <section>
      <h1 className="page-title">Trợ lý gửi OTP qua Gmail</h1>
      <p className="muted">
        Tự động gửi mã xác minh khi khách đăng ký hoặc yêu cầu gửi lại mã.
        Trợ lý không đọc hộp thư và không gửi email tùy ý.
      </p>
      {message && <p className="appearance-success" role="status">{message}</p>}
      <ErrorBox message={error} />
      {!status && !error && <Loading />}
      {status && (
        <div className="card narrow" style={{ padding: "1.5rem" }}>
          <h2>Kết nối tài khoản gửi</h2>
          <p>
            Trạng thái:{" "}
            <strong>{deliveryStatus(status)}</strong>
          </p>
          <p className="muted">
            Cấu hình OAuth: {status.configured ? "Đã đủ" : "Chưa đủ"} ·
            SMTP: {status.smtp_configured ? "Đã cấu hình" : "Chưa cấu hình"}
          </p>
          {status.sender_email && (
            <p className="muted">Tài khoản gửi: {status.sender_email}</p>
          )}
          <p className="muted">
            Chỉ cấp quyền gửi thư Gmail. Không nhập hoặc chia sẻ mật khẩu Google;
            Google sẽ hiện trang cấp quyền riêng. Token được mã hóa khi lưu trên backend.
          </p>
          {!status.configured && (
            <p className="hint">
              Nhập OAuth Client ID và Client Secret ở biểu mẫu bên dưới; đồng thời bật Gmail API
              và đăng ký đúng URL chuyển hướng OAuth trong Google Cloud.
            </p>
          )}
          <div className="form-actions">
            <button
              className="btn btn-red"
              type="button"
              disabled={busy || !status.configured}
              onClick={connect}
            >
              {busy ? "Đang xử lý..." : status.connected ? "Kết nối lại Gmail" : "Kết nối Gmail"}
            </button>
            {status.connected && (
              <button
                className="btn btn-danger"
                type="button"
                disabled={busy}
                onClick={disconnect}
              >
                Ngắt kết nối
              </button>
            )}
          </div>
        </div>
      )}
      <form className="card gmail-assistant-settings" onSubmit={saveSettings}>
        <h2>Cấu hình gửi email</h2>
        <p className="muted">
          Secret chỉ nhập một lần và được mã hóa khi lưu. Các ô secret luôn để trống sau khi lưu;
          để trống khi cập nhật thông tin khác sẽ giữ secret đã lưu.
        </p>
        <h3>Google OAuth (khuyến nghị)</h3>
        <label>
          OAuth Client ID
          <input
            autoComplete="off"
            name="oauth_client_id"
            onChange={updateField}
            placeholder={status?.oauth_client_id_configured ? "Đã có cấu hình — nhập mới nếu muốn thay đổi" : "Nhập Client ID"}
            value={form.oauth_client_id}
          />
        </label>
        <label>
          OAuth Client Secret
          <input
            autoComplete="new-password"
            name="oauth_client_secret"
            onChange={updateField}
            placeholder={status?.oauth_client_secret_configured ? "Đã lưu — nhập mới nếu muốn thay đổi" : "Nhập Client Secret"}
            type="password"
            value={form.oauth_client_secret}
          />
        </label>
        <label>
          OAuth Redirect URI
          <input
            autoComplete="off"
            name="oauth_redirect_uri"
            onChange={updateField}
            value={form.oauth_redirect_uri}
          />
        </label>
        <label>
          Địa chỉ trang quản trị
          <input
            autoComplete="off"
            name="oauth_frontend_url"
            onChange={updateField}
            value={form.oauth_frontend_url}
          />
        </label>
        <h3>SMTP Gmail (phương án thay thế)</h3>
        <label>
          SMTP host
          <input autoComplete="off" name="smtp_host" onChange={updateField} value={form.smtp_host} />
        </label>
        <label>
          SMTP port
          <input
            inputMode="numeric"
            name="smtp_port"
            onChange={updateField}
            type="number"
            value={form.smtp_port}
          />
        </label>
        <label>
          Tài khoản gửi Gmail
          <input
            autoComplete="off"
            name="smtp_username"
            onChange={updateField}
            placeholder={status?.smtp_configured ? "Đã cấu hình — nhập mới nếu muốn thay đổi" : "name@gmail.com"}
            type="email"
            value={form.smtp_username}
          />
        </label>
        <label>
          SMTP App Password
          <input
            autoComplete="new-password"
            name="smtp_password"
            onChange={updateField}
            placeholder={status?.smtp_configured ? "Đã lưu — nhập mới nếu muốn thay đổi" : "Chỉ dùng App Password, không dùng mật khẩu Gmail"}
            type="password"
            value={form.smtp_password}
          />
        </label>
        <label>
          Địa chỉ From
          <input
            autoComplete="off"
            name="smtp_from_email"
            onChange={updateField}
            placeholder="name@gmail.com"
            type="email"
            value={form.smtp_from_email}
          />
        </label>
        <div className="form-actions">
          <button className="btn btn-red" disabled={busy} type="submit">
            {busy ? "Đang lưu..." : "Lưu cấu hình"}
          </button>
        </div>
        {saveState !== "idle" && (
          <div
            aria-label={
              saveState === "saving"
                ? "Đang lưu cấu hình"
                : saveState === "saved"
                  ? "Đã lưu cấu hình"
                  : "Lưu cấu hình thất bại"
            }
            aria-valuemax="100"
            aria-valuemin="0"
            aria-valuenow={saveState === "saving" ? 65 : 100}
            className={`gmail-save-progress gmail-save-progress-${saveState}`}
            role="progressbar"
          >
            <span />
          </div>
        )}
      </form>
    </section>
  );
}
