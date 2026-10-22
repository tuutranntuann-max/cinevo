import ResourcePage from "../../components/ResourcePage";

const columns = [{ key: "id", label: "ID" }, { key: "cinema", label: "Rạp" }, { key: "name", label: "Phòng" }, { key: "room_type", label: "Loại" }, { key: "total_rows", label: "Số hàng" }, { key: "total_cols", label: "Số cột" }];

export default function RoomManagement() {
  return <ResourcePage title="Quản lý phòng chiếu" endpoint="/manager/rooms" columns={columns} />;
}
