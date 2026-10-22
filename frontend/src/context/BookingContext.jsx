// Giữ "đơn đặt vé đang làm dở": khu vực, suất chiếu, ghế, combo, phương thức thanh toán.
// Lưu vào localStorage nên đăng nhập/đăng ký xong (hoặc tải lại trang) vẫn còn nguyên.
import { createContext, useContext, useEffect, useMemo, useState } from "react";

const KEY = "cinevo_booking";
const CITY_KEY = "cinevo_city";
const EMPTY = { showtime: null, seats: [], foods: [], paymentMethod: "QR", promotion: null };

const BookingContext = createContext(null);
export const useBooking = () => useContext(BookingContext);

const load = () => {
  try { return { ...EMPTY, ...JSON.parse(localStorage.getItem(KEY) || "{}") }; }
  catch { return EMPTY; }
};

export function BookingProvider({ children }) {
  const [booking, setBooking] = useState(load);
  const [city, setCityState] = useState(localStorage.getItem(CITY_KEY) || "");

  useEffect(() => localStorage.setItem(KEY, JSON.stringify(booking)), [booking]);

  const setCity = (c) => { setCityState(c); localStorage.setItem(CITY_KEY, c); };

  // Chọn xong ghế: lưu suất chiếu + ghế, xóa combo cũ (nếu đổi suất).
  const saveSeatSelection = (showtime, seats) =>
    setBooking((b) => ({ ...EMPTY, paymentMethod: b.paymentMethod, showtime, seats }));
  const setFoods = (foods) => setBooking((b) => ({ ...b, foods }));
  const setPaymentMethod = (paymentMethod) => setBooking((b) => ({ ...b, paymentMethod }));
  const setPromotion = (promotion) => setBooking((b) => ({ ...b, promotion }));
  const resetBooking = () => setBooking(EMPTY);

  const totals = useMemo(() => {
    const seatAmount = booking.seats.reduce((s, x) => s + x.price, 0);
    const foodAmount = booking.foods.reduce((s, x) => s + x.price * x.quantity, 0);
    const subtotal = seatAmount + foodAmount;
    const discountPercent = Number(booking.promotion?.discount_percent);
    const discountAmount = booking.promotion && Number.isFinite(discountPercent)
      ? Math.floor(subtotal * Math.min(100, Math.max(0, discountPercent)) / 100)
      : 0;
    return { seatAmount, foodAmount, subtotal, discountAmount, total: subtotal - discountAmount };
  }, [booking]);

  const value = {
    booking, city, setCity, saveSeatSelection, setFoods, setPaymentMethod,
    setPromotion, resetBooking, totals,
  };
  return <BookingContext.Provider value={value}>{children}</BookingContext.Provider>;
}
