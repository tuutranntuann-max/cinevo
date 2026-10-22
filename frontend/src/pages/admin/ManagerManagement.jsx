import ResourcePage from "../../components/ResourcePage";

const columns = [
  { key: "id", label: "ID" },
  { key: "full_name", label: "Họ tên" },
  { key: "email", label: "Email" },
  { key: "role", label: "Vai trò" },
  { key: "status", label: "Trạng thái" },
];

export default function ManagerManagement() {
  return <ResourcePage title="Quản lý nhân viên và Manager" endpoint="/admin/managers" columns={columns} />;
}
