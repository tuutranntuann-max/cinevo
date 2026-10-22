import ResourcePage from "../../components/ResourcePage";

const columns = [{ key: "id", label: "ID" }, { key: "name", label: "Tên rạp" }, { key: "city", label: "Khu vực" }, { key: "address", label: "Địa chỉ" }];

export default function CinemaManagement() {
  return <ResourcePage title="Quản lý rạp" endpoint="/manager/cinemas" columns={columns} />;
}
