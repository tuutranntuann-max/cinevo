import { useEffect, useState } from "react";
import DataTable from "../../components/DataTable";
import ErrorBox from "../../components/ErrorBox";
import Loading from "../../components/Loading";
import { api } from "../../services/api";

const INACTIVE_AFTER_DAYS = 30;

function userStatus(user) {
  if (user.status !== "ACTIVE") return { label: "OFF", className: "off" };

  const referenceTime = user.last_login_at || user.created_at;
  const lastActive = referenceTime ? new Date(referenceTime).getTime() : NaN;
  const inactiveFor = Date.now() - lastActive;
  if (Number.isFinite(inactiveFor) && inactiveFor >= INACTIVE_AFTER_DAYS * 24 * 60 * 60 * 1000) {
    return { label: "Ngưng hoạt động 30 ngày", className: "inactive" };
  }
  return { label: "ON", className: "on" };
}

export default function UserManagement() {
  const [users, setUsers] = useState(null);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [deletingId, setDeletingId] = useState(null);
  const [pendingDelete, setPendingDelete] = useState(null);

  async function loadUsers() {
    setError("");
    setUsers(null);
    try {
      setUsers(await api.get("/admin/users"));
    } catch (e) {
      setError(e.message);
    }
  }

  useEffect(() => {
    loadUsers();
  }, []);

  useEffect(() => {
    if (!pendingDelete) return undefined;
    function closeOnEscape(event) {
      if (event.key === "Escape" && deletingId === null) setPendingDelete(null);
    }
    window.addEventListener("keydown", closeOnEscape);
    return () => window.removeEventListener("keydown", closeOnEscape);
  }, [pendingDelete, deletingId]);

  async function deleteUser() {
    const user = pendingDelete;
    if (!user) return;
    setDeletingId(user.id);
    setError("");
    setMessage("");
    try {
      const result = await api.delete(`/admin/users/${user.id}`);
      setUsers((current) => current.filter((item) => item.id !== user.id));
      setMessage(result.message);
      setPendingDelete(null);
    } catch (e) {
      setError(e.message);
    } finally {
      setDeletingId(null);
    }
  }

  const columns = [
    { key: "id", label: "ID" },
    { key: "full_name", label: "Họ tên" },
    { key: "email", label: "Email" },
    { key: "phone", label: "SĐT" },
    { key: "role", label: "Role" },
    {
      key: "status",
      label: "Trạng thái",
      render: (user) => {
        const status = userStatus(user);
        return (
          <span className={`user-presence user-presence-${status.className}`} aria-label={status.label}>
            <span className="user-presence-dot" aria-hidden="true" />
            <span>{status.label}</span>
          </span>
        );
      },
    },
    {
      key: "actions",
      label: "Thao tác",
      render: (user) => user.role === "USER"
        || (user.email === "manager@cinevo.vn" && user.full_name === "Quản lý Demo")
        || (user.email === "admin@cinevo.vn" && user.full_name === "Admin Demo") ? (
        <button
          className="btn btn-danger btn-sm"
          type="button"
          disabled={deletingId !== null}
          onClick={() => setPendingDelete(user)}
        >
          {deletingId === user.id ? "Đang xóa..." : "Xóa tài khoản"}
        </button>
      ) : <span className="muted small">Không thể xóa</span>,
    },
  ];

  return (
    <section>
      <h1 className="page-title">Quản lý người dùng</h1>
      <p className="muted">Có thể xóa tài khoản USER và tài khoản demo. Tài khoản có lịch sử đặt vé được giữ lại để bảo toàn vé và giao dịch.</p>
      <ErrorBox message={error} />
      {message && <p className="appearance-success" role="status">{message}</p>}
      {!users && !error ? <Loading /> : users && <DataTable columns={columns} rows={users} />}
      {pendingDelete && (
        <div
          className="confirm-modal-overlay"
          onMouseDown={(event) => {
            if (event.target === event.currentTarget && deletingId === null) setPendingDelete(null);
          }}
        >
          <section className="confirm-modal" role="dialog" aria-modal="true" aria-labelledby="delete-user-title">
            <span className="confirm-modal-icon" aria-hidden="true">!</span>
            <h2 id="delete-user-title">Xóa tài khoản?</h2>
            <p>Bạn sắp xóa tài khoản này khỏi CINEVO:</p>
            <div className="confirm-modal-user">
              <strong>{pendingDelete.full_name}</strong>
              <span>{pendingDelete.email}</span>
              <span>{pendingDelete.role}</span>
            </div>
            <p className="confirm-modal-warning">Không thể hoàn tác. Tài khoản có lịch sử đặt vé sẽ được giữ lại để bảo toàn vé và giao dịch.</p>
            <div className="confirm-modal-actions">
              <button className="btn btn-ghost" type="button" disabled={deletingId !== null} onClick={() => setPendingDelete(null)}>
                Hủy
              </button>
              <button className="btn btn-danger" type="button" disabled={deletingId !== null} onClick={deleteUser}>
                {deletingId === pendingDelete.id ? "Đang xóa..." : "Xóa tài khoản"}
              </button>
            </div>
          </section>
        </div>
      )}
    </section>
  );
}
