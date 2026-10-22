import ResourcePage from "../../components/ResourcePage";

const columns = [{ key: "id", label: "ID" }, { key: "name", label: "Role" }, { key: "description", label: "Mô tả" }];

export default function RoleManagement() {
  return <ResourcePage title="Quản lý phân quyền" endpoint="/admin/roles" columns={columns} />;
}
