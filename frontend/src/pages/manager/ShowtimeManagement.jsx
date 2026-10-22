import ResourcePage from "../../components/ResourcePage";
import { formatVND } from "../../utils/format";

const columns = [{ key: "id", label: "ID" }, { key: "movie", label: "Phim" }, { key: "cinema", label: "Rạp" }, { key: "room", label: "Phòng" }, { key: "start_time", label: "Giờ chiếu", render: (r) => new Date(r.start_time).toLocaleString("vi-VN") }, { key: "base_price", label: "Giá", render: (r) => formatVND(r.base_price) }];

export default function ShowtimeManagement() {
  return <ResourcePage title="Quản lý suất chiếu" endpoint="/manager/showtimes" columns={columns} />;
}
