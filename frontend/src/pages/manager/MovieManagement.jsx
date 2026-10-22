import ResourcePage from "../../components/ResourcePage";

const columns = [{ key: "id", label: "ID" }, { key: "title", label: "Tên phim" }, { key: "genre", label: "Thể loại" }, { key: "duration_minutes", label: "Phút" }, { key: "status", label: "Trạng thái" }];

export default function MovieManagement() {
  return <ResourcePage title="Quản lý phim" endpoint="/manager/movies" columns={columns} />;
}
