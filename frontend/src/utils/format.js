// Các hàm định dạng dùng chung.
export const formatVND = (n) => `${Number(n || 0).toLocaleString("vi-VN")}đ`;

export const formatTime = (iso) =>
  new Date(iso).toLocaleTimeString("vi-VN", { hour: "2-digit", minute: "2-digit", hour12: false });

export const formatDate = (iso) => new Date(iso).toLocaleDateString("vi-VN");

/** YYYY-MM-DD theo giờ địa phương (khớp với giờ suất chiếu lưu ở backend). */
export const toISODate = (d) =>
  `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;

export const nextDays = (count = 5) =>
  Array.from({ length: count }, (_, i) => {
    const d = new Date();
    d.setDate(d.getDate() + i);
    return d;
  });

export const WEEKDAYS = ["CN", "T2", "T3", "T4", "T5", "T6", "T7"];
