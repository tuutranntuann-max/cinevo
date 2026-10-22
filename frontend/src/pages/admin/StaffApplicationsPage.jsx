import { useCallback, useEffect, useState } from "react";
import ErrorBox from "../../components/ErrorBox";
import Loading from "../../components/Loading";
import { api } from "../../services/api";

const ROLE_LABELS = { EMPLOYEE: "Nhân viên", MANAGER: "Quản lý" };
const STATUS_LABELS = {
  PENDING: "Chờ duyệt",
  INVITED: "Đã cấp mã mời",
  ACTIVE: "Đã kích hoạt",
  REJECTED: "Đã từ chối",
};

export default function StaffApplicationsPage() {
  const [applications, setApplications] = useState([]);
  const [resetRequests, setResetRequests] = useState([]);
  const [roles, setRoles] = useState({});
  const [inviteCodes, setInviteCodes] = useState({});
  const [resetCodes, setResetCodes] = useState({});
  const [loading, setLoading] = useState(true);
  const [busyId, setBusyId] = useState(null);
  const [error, setError] = useState("");

  const loadApplications = useCallback(async () => {
    try {
      const [result, resets] = await Promise.all([
        api.get("/staff-accounts/applications"),
        api.get("/staff-accounts/password-resets"),
      ]);
      setApplications(result.applications);
      setResetRequests(resets.requests);
      setError("");
    } catch (loadError) {
      setError(loadError.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadApplications();
  }, [loadApplications]);

  async function approve(application) {
    setBusyId(application.id);
    setError("");
    try {
      const result = await api.post(`/staff-accounts/applications/${application.id}/approve`, {
        role: roles[application.id] || application.requested_role,
      });
      setInviteCodes((current) => ({ ...current, [application.id]: result.invite_code }));
      await loadApplications();
    } catch (approveError) {
      setError(approveError.message);
    } finally {
      setBusyId(null);
    }
  }

  async function reject(application) {
    setBusyId(application.id);
    setError("");
    try {
      await api.post(`/staff-accounts/applications/${application.id}/reject`, {});
      await loadApplications();
    } catch (rejectError) {
      setError(rejectError.message);
    } finally {
      setBusyId(null);
    }
  }

  async function reissueInvite(application) {
    setBusyId(application.id);
    setError("");
    try {
      const result = await api.post(`/staff-accounts/applications/${application.id}/invite`, {});
      setInviteCodes((current) => ({ ...current, [application.id]: result.invite_code }));
      await loadApplications();
    } catch (inviteError) {
      setError(inviteError.message);
    } finally {
      setBusyId(null);
    }
  }

  async function issueResetCode(resetRequest) {
    setBusyId(`reset-${resetRequest.id}`);
    setError("");
    try {
      const result = await api.post(`/staff-accounts/password-resets/${resetRequest.id}/issue`, {});
      setResetCodes((current) => ({ ...current, [resetRequest.id]: result.reset_code }));
      await loadApplications();
    } catch (issueError) {
      setError(issueError.message);
    } finally {
      setBusyId(null);
    }
  }

  if (loading) return <Loading />;

  return (
    <section className="staff-applications-page">
      <div>
        <h1 className="page-title">Hồ sơ nhân viên và quản lý</h1>
        <p className="muted">Chỉ hồ sơ được Admin duyệt mới nhận được mã mời kích hoạt một lần.</p>
        <p className="staff-application-privacy">
          Hồ sơ gồm dữ liệu cá nhân nhạy cảm; chỉ xem khi cần xét duyệt và không chia sẻ mã mời công khai.
        </p>
      </div>
      <ErrorBox message={error} />
      <section className="staff-reset-admin">
        <div>
          <h2>Yêu cầu quên mật khẩu</h2>
          <p className="muted small">Cấp mã một lần và gửi riêng cho nhân viên/quản lý qua kênh đã xác minh.</p>
        </div>
        {!resetRequests.length ? (
          <div className="state-box">Không có yêu cầu đặt lại mật khẩu đang chờ hoặc đã cấp mã.</div>
        ) : resetRequests.map((resetRequest) => (
          <article className="staff-reset-admin-card" key={resetRequest.id}>
            <div>
              <strong>{resetRequest.full_name}</strong>
              <p>{resetRequest.email} · {ROLE_LABELS[resetRequest.role] || resetRequest.role}</p>
              <span className={`staff-application-status ${resetRequest.status.toLowerCase()}`}>
                {resetRequest.status === "PENDING" ? "Chờ cấp mã" : "Đã cấp mã"}
              </span>
            </div>
            <button className="btn btn-ghost btn-sm" type="button"
              disabled={busyId === `reset-${resetRequest.id}`}
              onClick={() => issueResetCode(resetRequest)}>
              {busyId === `reset-${resetRequest.id}` ? "Đang cấp mã..." : resetRequest.status === "PENDING" ? "Cấp mã đặt lại" : "Cấp lại mã"}
            </button>
            {resetCodes[resetRequest.id] && (
              <div className="staff-invitation-code" role="status">
                <strong>Mã đặt lại (chỉ hiển thị lần này)</strong>
                <code>{resetCodes[resetRequest.id]}</code>
                <p>{resetRequest.email} · Mã dùng một lần, hết hạn sau 30 phút. Gửi riêng mã cho đúng người.</p>
              </div>
            )}
          </article>
        ))}
      </section>
      {!applications.length ? (
        <div className="state-box">Chưa có hồ sơ đăng ký.</div>
      ) : applications.map((application) => (
        <article className="staff-application-card" key={application.id}>
          <header className="staff-application-card-header">
            <div>
              <h2>{application.full_name}</h2>
              <p>{application.email} · {application.phone}</p>
            </div>
            <span className={`staff-application-status ${application.status.toLowerCase()}`}>
              {STATUS_LABELS[application.status] || application.status}
            </span>
          </header>
          <dl className="staff-application-details">
            <div><dt>CCCD</dt><dd>{application.citizen_id}</dd></div>
            <div><dt>Địa chỉ</dt><dd>{application.address}</dd></div>
            <div><dt>Giới tính</dt><dd>{application.gender}</dd></div>
            <div><dt>Nghề nghiệp / tình trạng</dt><dd>{application.occupation}</dd></div>
            <div><dt>Vị trí yêu cầu</dt><dd>{ROLE_LABELS[application.requested_role] || application.requested_role}</dd></div>
            {application.approved_role && (
              <div><dt>Vị trí được duyệt</dt><dd>{ROLE_LABELS[application.approved_role] || application.approved_role}</dd></div>
            )}
          </dl>
          {application.status === "PENDING" && (
            <div className="staff-application-review">
              <label>Phân quyền
                <select value={roles[application.id] || application.requested_role}
                  onChange={(event) => setRoles((current) => ({ ...current, [application.id]: event.target.value }))}>
                  <option value="EMPLOYEE">Nhân viên</option>
                  <option value="MANAGER">Quản lý</option>
                </select>
              </label>
              <button className="btn btn-red btn-sm" type="button" disabled={busyId === application.id}
                onClick={() => approve(application)}>
                {busyId === application.id ? "Đang duyệt..." : "Duyệt và cấp mã mời"}
              </button>
              <button className="btn btn-ghost btn-sm" type="button" disabled={busyId === application.id}
                onClick={() => reject(application)}>
                Từ chối hồ sơ
              </button>
            </div>
          )}
          {inviteCodes[application.id] && (
            <div className="staff-invitation-code" role="status">
              <strong>Mã mời (chỉ hiển thị lần này)</strong>
              <code>{inviteCodes[application.id]}</code>
              <p>Gửi mã riêng cho người đăng ký. Mã hết hạn sau 7 ngày và chỉ sử dụng được một lần.</p>
            </div>
          )}
          {application.status === "INVITED" && !inviteCodes[application.id] && (
            <div className="staff-invitation-reissue">
              <p className="muted small">Mã trước chỉ hiển thị khi tạo. Nếu người nhận làm mất hoặc mã hết hạn, cấp mã mới.</p>
              <button className="btn btn-ghost btn-sm" type="button" disabled={busyId === application.id}
                onClick={() => reissueInvite(application)}>
                Cấp lại mã mời
              </button>
            </div>
          )}
        </article>
      ))}
    </section>
  );
}
