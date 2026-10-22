import ResourcePage from "../../components/ResourcePage";
import { formatVND } from "../../utils/format";

const columns = [{ key: "movie", label: "Phim" }, { key: "bookings", label: "Số đơn" }, { key: "revenue", label: "Doanh thu", render: (r) => formatVND(r.revenue) }];

export default function ReportPage() {
  return <ResourcePage title="Báo cáo doanh thu theo phim" endpoint="/manager/report" columns={columns} />;
}
