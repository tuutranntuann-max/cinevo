import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import BackHomeLink from "../../components/BackHomeLink";
import ErrorBox from "../../components/ErrorBox";
import { useAuth } from "../../context/AuthContext";
import { api } from "../../services/api";

const INITIAL_PROFILE = {
  full_name: "",
  email: "",
  phone: "",
  citizen_id: "",
  address: "",
  gender: "",
  occupation: "",
  requested_role: "EMPLOYEE",
  accept_privacy: false,
};

export default function StaffApplicationPage() {
  const navigate = useNavigate();
  const { startSession } = useAuth();
  const [mode, setMode] = useState("apply");
  const [profile, setProfile] = useState(INITIAL_PROFILE);
  const [activation, setActivation] = useState({
    email: "",
    invite_code: "",
    password: "",
    confirm_password: "",
  });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [submitted, setSubmitted] = useState(false);

  async function submitApplication(event) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      await api.post("/staff-accounts/applications", profile);
      setSubmitted(true);
    } catch (submitError) {
      setError(submitError.message);
    } finally {
      setBusy(false);
    }
  }

  async function activateAccount(event) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      const result = await api.post("/staff-accounts/complete", activation);
      startSession(result);
      navigate("/manager", { replace: true });
    } catch (activateError) {
      setError(activateError.message);
    } finally {
      setBusy(false);
    }
  }

  function updateProfile(event) {
    const value = event.target.type === "checkbox" ? event.target.checked : event.target.value;
    setProfile((current) => ({ ...current, [event.target.name]: value }));
  }

  return (
    <main className="staff-auth-page">
      <BackHomeLink className="staff-auth-home" />
      <section className="staff-application">
        <h1 className="page-title">Cơ hội nghề nghiệp tại CINEVO</h1>
        <p className="muted">Ứng tuyển vị trí nhân viên hoặc quản lý. Hồ sơ sẽ được Admin xét duyệt trước khi cấp mã kích hoạt tài khoản.</p>
        <div className="staff-application-tabs" role="group" aria-label="Chọn thao tác">
          <button type="button" className={`btn btn-sm ${mode === "apply" ? "btn-red" : "btn-ghost"}`}
            onClick={() => { setMode("apply"); setError(""); }}>
            Gửi hồ sơ
          </button>
          <button type="button" className={`btn btn-sm ${mode === "activate" ? "btn-red" : "btn-ghost"}`}
            onClick={() => { setMode("activate"); setError(""); }}>
            Tôi đã có mã mời
          </button>
        </div>
        <ErrorBox message={error} />
        {mode === "apply" && (submitted ? (
          <div className="success staff-application-success" role="status">
            <strong>Đã nhận hồ sơ của bạn.</strong>
            <p>Vui lòng chờ Admin duyệt. Khi nhận được mã mời, quay lại đây để kích hoạt tài khoản.</p>
            <button className="btn btn-ghost btn-sm" type="button" onClick={() => setMode("activate")}>
              Nhập mã mời
            </button>
          </div>
        ) : (
          <form className="staff-application-form" onSubmit={submitApplication}>
            <label>Họ và tên
              <input name="full_name" autoComplete="name" required minLength={2} maxLength={120}
                value={profile.full_name} onChange={updateProfile} />
            </label>
            <label>Email
              <input name="email" type="email" autoComplete="email" required maxLength={160}
                value={profile.email} onChange={updateProfile} />
            </label>
            <label>Số điện thoại
              <input name="phone" type="tel" autoComplete="tel" required placeholder="09xxxxxxxx"
                value={profile.phone} onChange={updateProfile} />
            </label>
            <label>Số CCCD (12 chữ số)
              <input name="citizen_id" inputMode="numeric" autoComplete="off" pattern="[0-9]{12}"
                minLength={12} maxLength={12} required value={profile.citizen_id} onChange={updateProfile} />
            </label>
            <label className="staff-application-wide">Địa chỉ
              <input name="address" autoComplete="street-address" required minLength={5} maxLength={300}
                value={profile.address} onChange={updateProfile} />
            </label>
            <label>Giới tính
              <select name="gender" required value={profile.gender} onChange={updateProfile}>
                <option value="">Chọn giới tính</option>
                <option value="Nam">Nam</option>
                <option value="Nữ">Nữ</option>
                <option value="Khác">Khác</option>
              </select>
            </label>
            <label>Nghề nghiệp / tình trạng
              <input name="occupation" required minLength={2} maxLength={100}
                placeholder="Học sinh, sinh viên, công nhân..."
                value={profile.occupation} onChange={updateProfile} />
            </label>
            <label>Vị trí đăng ký
              <select name="requested_role" value={profile.requested_role} onChange={updateProfile}>
                <option value="EMPLOYEE">Nhân viên</option>
                <option value="MANAGER">Quản lý</option>
              </select>
            </label>
            <p className="staff-application-privacy staff-application-wide">
              Thông tin hồ sơ chỉ hiển thị trong khu vực Admin để xét duyệt tài khoản.
            </p>
            <label className="staff-application-consent staff-application-wide">
              <input name="accept_privacy" type="checkbox" required checked={profile.accept_privacy}
                onChange={updateProfile} />
              Tôi đồng ý cung cấp thông tin cá nhân để Admin xét duyệt hồ sơ nhân viên/quản lý.
            </label>
            <button className="btn btn-red staff-application-wide" type="submit"
              disabled={busy || !profile.accept_privacy}>
              {busy ? "Đang gửi hồ sơ..." : "Gửi hồ sơ xét duyệt"}
            </button>
          </form>
        ))}
        {mode === "activate" && (
          <form className="staff-application-form staff-activation-form" onSubmit={activateAccount}>
            <label>Email hồ sơ
              <input type="email" autoComplete="email" required value={activation.email}
                onChange={(event) => setActivation({ ...activation, email: event.target.value })} />
            </label>
            <label>Mã mời dùng một lần
              <input required minLength={32} maxLength={32} autoComplete="one-time-code"
                value={activation.invite_code}
                onChange={(event) => setActivation({ ...activation, invite_code: event.target.value.toUpperCase() })} />
            </label>
            <label>Mật khẩu (tối thiểu 8 ký tự)
              <input type="password" autoComplete="new-password" required minLength={8} maxLength={128}
                value={activation.password}
                onChange={(event) => setActivation({ ...activation, password: event.target.value })} />
            </label>
            <label>Nhập lại mật khẩu
              <input type="password" autoComplete="new-password" required minLength={8} maxLength={128}
                value={activation.confirm_password}
                onChange={(event) => setActivation({ ...activation, confirm_password: event.target.value })} />
            </label>
            <button className="btn btn-red staff-application-wide" type="submit" disabled={busy}>
              {busy ? "Đang kích hoạt..." : "Kích hoạt tài khoản"}
            </button>
          </form>
        )}
        <p className="muted center small">
          Đã có tài khoản? <Link className="link" to="/manager/login">Đăng nhập nhân viên</Link>
        </p>
      </section>
    </main>
  );
}
