import ResourcePage from "../../components/ResourcePage";
import { formatVND } from "../../utils/format";

const columns = [{ key: "code", label: "Mã vé" }, { key: "customer", label: "Khách" }, { key: "movie", label: "Phim" }, { key: "seats", label: "Ghế" }, { key: "total_amount", label: "Tổng tiền", render: (r) => formatVND(r.total_amount) }, { key: "status", label: "Trạng thái" }];

export default function BookingManagement() {
  return <ResourcePage title="Quản lý đặt vé" endpoint="/manager/bookings" columns={columns} />;
}
