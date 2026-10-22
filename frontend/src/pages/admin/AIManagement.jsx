import ResourcePage from "../../components/ResourcePage";

const columns = [{ key: "key", label: "Cấu hình" }, { key: "value", label: "Giá trị" }];

export default function AIManagement() {
  return <ResourcePage title="Quản lý AI" endpoint="/admin/ai-settings" columns={columns} />;
}
