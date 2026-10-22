import { useCallback, useEffect, useState } from "react";
import DataTable from "../../components/DataTable";
import ErrorBox from "../../components/ErrorBox";
import Loading from "../../components/Loading";
import { api } from "../../services/api";

const STATUS_LABELS = {
  SENT: "Đã gửi, còn hiệu lực",
  EXPIRED: "Mã đã hết hạn",
  NOT_SENT: "Chưa có mã",
};

function formatDate(value) {
  if (!value) return "—";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? "—" : date.toLocaleString("vi-VN");
}

export default function PendingRegistrationsPage() {
  const [registrations, setRegistrations] = useState(null);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [busyId, setBusyId] = useState(null);

  const loadRegistrations = useCallback(async () => {
    setError("");
    try {
      setRegistrations(await api.get("/admin/pending-registrations"));
    } catch (loadError) {
      setError(loadError.message);
    }
  }, []);

  useEffect(() => {
    loadRegistrations();
  }, [loadRegistrations]);

  async function resendOtp(registration) {
    setBusyId(registration.id);
    setError("");
    setMessage("");
    try {
      const result = await api.post(
        `/admin/pending-registrations/${registration.id}/resend-otp`,
        {},
      );
      setMessage(result.message);
      await loadRegistrations();
    } catch (resendError) {
      setError(resendError.message);
    } finally {
      setBusyId(null);
    }
  }

  const columns = [
    { key: "full_name", label: "Họ tên" },
    { key: "email", label: "Email khách hàng" },
    {
      key: "created_at",
      label: "Ngày đăng ký",
      render: (registration) => formatDate(registration.created_at),
    },
    {
      key: "otp_sent_at",
      label: "Lần gửi gần nhất",
      render: (registration) => formatDate(registration.otp_sent_at),
    },
    {
      key: "otp_status",
      label: "Trạng thái",
      render: (registration) => {
        if (registration.delivery_mode === "DEVELOPMENT" && registration.otp_status === "SENT") {
          return "Mã thử nghiệm — không gửi email thật";
        }
        return STATUS_LABELS[registration.otp_status] || registration.otp_status;
      },
    },
    {
      key: "actions",
      label: "Thao tác",
      render: (registration) => (
        <button
          className="btn btn-ghost btn-sm"
          type="button"
          disabled={busyId !== null}
          onClick={() => resendOtp(registration)}
        >
          {busyId === registration.id ? "Đang gửi..." : "Gửi lại OTP"}
        </button>
      ),
    },
  ];

  return (
    <section>
      <h1 className="page-title">OTP đăng ký khách hàng</h1>
      <p className="muted">
        Theo dõi email, thời điểm và trạng thái gửi. Mã xác minh không hiển thị trong trang quản trị.
      </p>
      {!registrations && !error && <Loading />}
      <ErrorBox message={error} />
      {message && <p className="appearance-success" role="status">{message}</p>}
      {registrations && (
        registrations.length
          ? <DataTable columns={columns} rows={registrations} />
          : <div className="state-box">Không có đăng ký nào đang chờ xác minh.</div>
      )}
    </section>
  );
}
