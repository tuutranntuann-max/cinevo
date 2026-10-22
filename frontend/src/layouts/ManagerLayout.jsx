import PanelLayout from "./PanelLayout";
import { useAuth } from "../context/AuthContext";

const LINKS = [
  ["", "Tổng quan"], ["/movies", "Phim"], ["/cinemas", "Rạp"], ["/rooms", "Phòng chiếu"],
  ["/seats", "Ghế"], ["/showtimes", "Suất chiếu"], ["/bookings", "Đặt vé"], ["/transactions", "Thanh toán"],
  ["/foods", "Đồ ăn"], ["/products", "Shop & hàng tồn kho"], ["/report", "Báo cáo"], ["/promotions", "Mã giảm giá"],
  ["/events", "Sự kiện"], ["/news", "Tin tức"], ["/support", "Chat hỗ trợ"],
];

export default function ManagerLayout() {
  const { user } = useAuth();
  const links = LINKS.filter(([path]) =>
    path !== "/seats" || ["MANAGER", "ADMIN"].includes(user?.role));
  return <PanelLayout title="Quản lý rạp" base="/manager" links={links} />;
}
