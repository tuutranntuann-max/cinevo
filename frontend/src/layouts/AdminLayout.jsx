import { useFeatures } from "../context/FeaturesContext";
import PanelLayout from "./PanelLayout";

const LINKS = [
  ["", "Tổng quan"], ["/users", "Người dùng"], ["/pending-registrations", "OTP đăng ký"], ["/gmail-assistant", "Trợ lý gửi OTP"], ["/managers", "Manager"], ["/movies", "Vé phim"],
  ["/watch-films", "Xem phim"],
  ["/cinemas", "Rạp toàn quốc"], ["/showtimes", "Suất chiếu"], ["/seats", "Sơ đồ ghế"],
  ["/transactions", "Giao dịch"], ["/foods", "Đồ ăn & combo"], ["/products", "Hàng tồn kho"],
  ["/promotions", "Mã giảm giá"], ["/events", "Sự kiện"], ["/news", "Tin tức"],
  ["/ai", "Quản lý AI", "ai"],
  ["/support", "Chat hỗ trợ"], ["/staff-applications", "Hồ sơ nhân viên"], ["/roles", "Phân quyền"],
  ["/settings", "Tùy chỉnh giao diện"], ["/logs", "Nhật ký"],
];

export default function AdminLayout() {
  const { features } = useFeatures();
  // Mục có cờ (phần tử thứ 3) chỉ hiện khi tính năng đó đang bật.
  const links = LINKS.filter(([, , flag]) => !flag || features[flag]);
  return <PanelLayout brand="CINEVOADM" title="CINEVOADM · Quản trị hệ thống" base="/admin" links={links} />;
}
