import ResourcePage from "../../components/ResourcePage";

const columns = [{ key: "id", label: "ID" }, { key: "user", label: "Người dùng" }, { key: "action", label: "Hành động" }, { key: "detail", label: "Chi tiết" }, { key: "created_at", label: "Thời gian", render: (r) => new Date(r.created_at).toLocaleString("vi-VN") }];

export default function ActivityLog() {
  return <ResourcePage title="Nhật ký hoạt động" endpoint="/admin/activity-logs" columns={columns} />;
}
