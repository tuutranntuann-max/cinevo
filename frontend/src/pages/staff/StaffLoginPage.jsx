import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import AuthPanel from "../../components/AuthPanel";
import BackHomeLink from "../../components/BackHomeLink";
import ErrorBox from "../../components/ErrorBox";
import { api } from "../../services/api";
import { redirectByRole } from "../user/LoginPage";

export default function StaffLoginPage() {
  const navigate = useNavigate();
  const [mode, setMode] = useState("login");
  const [email, setEmail] = useState("");
  const [resetCode, setResetCode] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [notice, setNotice] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function requestReset(event) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      const result = await api.post("/staff-accounts/password-resets", { email });
      setNotice(result.message);
      setMode("requested");
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setBusy(false);
    }
  }

  async function completeReset(event) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      const result = await api.post("/staff-accounts/password-resets/complete", {
        email,
        reset_code: resetCode,
        password,
        confirm_password: confirmPassword,
      });
      setNotice(result.message);
      setResetCode("");
      setPassword("");
      setConfirmPassword("");
      setMode("complete");
    } catch (resetError) {
      setError(resetError.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="staff-auth-page">
      <section className="narrow">
        <h1 className="page-title">Cổng nhân viên CINEVO</h1>
        {mode === "login" && (
          <>
            <AuthPanel initialView="login" showRegister={false} translateUi={false}
              onSuccess={(user) => navigate(redirectByRole(user), { replace: true })} />
            <p className="center small">
              <button className="link" type="button" onClick={() => { setMode("request"); setError(""); setNotice(""); }}>
                Quên mật khẩu?
              </button>
            </p>
          </>
        )}
        {mode === "request" && (
          <form className="staff-reset-form" onSubmit={requestReset}>
            <h2>Yêu cầu mã đặt lại mật khẩu</h2>
            <p className="muted">Nhập email tài khoản nhân viên/quản lý. Admin sẽ kiểm tra yêu cầu và gửi mã dùng một lần cho bạn.</p>
            <ErrorBox message={error} />
            <label>Email tài khoản
              <input type="email" autoComplete="email" required value={email}
                onChange={(event) => setEmail(event.target.value)} />
            </label>
            <button className="btn btn-red btn-block" type="submit" disabled={busy}>
              {busy ? "Đang gửi yêu cầu..." : "Gửi yêu cầu cho Admin"}
            </button>
            <button className="btn btn-ghost btn-sm" type="button" onClick={() => { setMode("login"); setError(""); }}>
              Quay lại đăng nhập
            </button>
          </form>
        )}
        {mode === "requested" && (
          <div className="staff-reset-form" role="status">
            <h2>Đã gửi yêu cầu</h2>
            <p className="success">{notice}</p>
            <p className="muted">Admin sẽ cấp mã một lần. Khi nhận được mã, chọn nút bên dưới để đặt mật khẩu mới.</p>
            <button className="btn btn-red btn-block" type="button" onClick={() => { setMode("reset"); setError(""); }}>
              Tôi đã nhận mã từ Admin
            </button>
            <button className="btn btn-ghost btn-sm" type="button" onClick={() => { setMode("login"); setError(""); }}>
              Quay lại đăng nhập
            </button>
          </div>
        )}
        {mode === "reset" && (
          <form className="staff-reset-form" onSubmit={completeReset}>
            <h2>Đặt mật khẩu mới</h2>
            <p className="muted">Mã do Admin gửi chỉ dùng một lần và hết hạn sau 30 phút.</p>
            <ErrorBox message={error} />
            <label>Email tài khoản
              <input type="email" autoComplete="email" required value={email}
                onChange={(event) => setEmail(event.target.value)} />
            </label>
            <label>Mã đặt lại 8 số
              <input inputMode="numeric" autoComplete="one-time-code" pattern="[0-9]{8}" minLength={8}
                maxLength={8} required value={resetCode}
                onChange={(event) => setResetCode(event.target.value.replace(/\D/g, "").slice(0, 8))} />
            </label>
            <label>Mật khẩu mới (tối thiểu 8 ký tự)
              <input type="password" autoComplete="new-password" minLength={8} maxLength={128} required
                value={password} onChange={(event) => setPassword(event.target.value)} />
            </label>
            <label>Nhập lại mật khẩu
              <input type="password" autoComplete="new-password" minLength={8} maxLength={128} required
                value={confirmPassword} onChange={(event) => setConfirmPassword(event.target.value)} />
            </label>
            <button className="btn btn-red btn-block" type="submit" disabled={busy}>
              {busy ? "Đang đổi mật khẩu..." : "Đổi mật khẩu"}
            </button>
          </form>
        )}
        {mode === "complete" && (
          <div className="staff-reset-form" role="status">
            <h2>Đổi mật khẩu thành công</h2>
            <p className="success">{notice}</p>
            <button className="btn btn-red btn-block" type="button" onClick={() => { setMode("login"); setError(""); }}>
              Đăng nhập bằng mật khẩu mới
            </button>
          </div>
        )}
        <p className="muted center">
          Chưa có tài khoản? <Link className="link" to="/staff/register">Gửi hồ sơ nhân viên/quản lý</Link>
        </p>
        <BackHomeLink className="staff-auth-home" />
      </section>
    </main>
  );
}
