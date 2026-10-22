// Định tuyến chính. Khách khám phá phim tự do; các bước sau khi chọn ghế yêu cầu đăng nhập.
// /user/*  -> khách hàng | /manager/* -> quản lý rạp | /admin/* -> quản trị viên
import { Navigate, Route, Routes } from "react-router-dom";
import AuthModal from "./components/AuthModal";
import FeatureGate from "./components/FeatureGate";
import ProtectedRoute from "./components/ProtectedRoute";
import SupportChatWidget from "./components/SupportChatWidget";
import AdminLayout from "./layouts/AdminLayout";
import ManagerLayout from "./layouts/ManagerLayout";
import UserLayout from "./layouts/UserLayout";

import HomePage from "./pages/user/HomePage";
import MovieListPage from "./pages/user/MovieListPage";
import NewsPage from "./pages/user/NewsPage";
import PromotionsPage from "./pages/user/PromotionsPage";
import EventsPage from "./pages/user/EventsPage";
import MovieDetailPage from "./pages/user/MovieDetailPage";
import MovieWatchPage from "./pages/user/MovieWatchPage";
import CinemaListPage from "./pages/user/CinemaListPage";
import ShowtimePage from "./pages/user/ShowtimePage";
import SeatSelectionPage from "./pages/user/SeatSelectionPage";
import FoodPage from "./pages/user/FoodPage";
import CheckoutPage from "./pages/user/CheckoutPage";
import PaymentPage from "./pages/user/PaymentPage";
import BookingSuccessPage from "./pages/user/BookingSuccessPage";
import MyTicketsPage from "./pages/user/MyTicketsPage";
import ProfilePage from "./pages/user/ProfilePage";
import MembershipPage from "./pages/user/MembershipPage";
import ShopPage from "./pages/user/ShopPage";
import LoginPage from "./pages/user/LoginPage";
import RegisterPage from "./pages/user/RegisterPage";
import SettingsPage from "./pages/user/SettingsPage";

import ManagerDashboard from "./pages/manager/ManagerDashboard";
import MovieManagement from "./pages/manager/MovieManagement";
import CinemaManagement from "./pages/manager/CinemaManagement";
import RoomManagement from "./pages/manager/RoomManagement";
import SeatManagement from "./pages/manager/SeatManagement";
import ShowtimeManagement from "./pages/manager/ShowtimeManagement";
import BookingManagement from "./pages/manager/BookingManagement";
import FoodManagement from "./pages/manager/FoodManagement";
import ReportPage from "./pages/manager/ReportPage";

import AdminDashboard from "./pages/admin/AdminDashboard";
import UserManagement from "./pages/admin/UserManagement";
import PendingRegistrationsPage from "./pages/admin/PendingRegistrationsPage";
import GmailAssistantPage from "./pages/admin/GmailAssistantPage";
import ManagerManagement from "./pages/admin/ManagerManagement";
import AdminMovieManagement from "./pages/admin/AdminMovieManagement";
import AdminWatchFilmManagement from "./pages/admin/AdminWatchFilmManagement";
import TransactionManagement from "./pages/admin/TransactionManagement";
import PromotionManagement from "./pages/admin/PromotionManagement";
import NewsManagement from "./pages/admin/NewsManagement";
import EventManagement from "./pages/admin/EventManagement";
import AIManagement from "./pages/admin/AIManagement";
import RoleManagement from "./pages/admin/RoleManagement";
import SystemSettings from "./pages/admin/SystemSettings";
import ActivityLog from "./pages/admin/ActivityLog";
import SupportInboxPage from "./pages/support/SupportInboxPage";
import StaffApplicationPage from "./pages/staff/StaffApplicationPage";
import StaffLoginPage from "./pages/staff/StaffLoginPage";
import StaffApplicationsPage from "./pages/admin/StaffApplicationsPage";
import FoodCatalogManagement from "./pages/admin/FoodCatalogManagement";
import ProductManagement from "./pages/admin/ProductManagement";
import ManagerProductManagement from "./pages/manager/ShopManagement";
import AdminShowtimeManagement from "./pages/admin/AdminShowtimeManagement";
import CinemaCatalogManagement from "./pages/admin/CinemaCatalogManagement";
import AdminLoginPage from "./pages/admin/AdminLoginPage";
import ClickEffects from "./components/ClickEffects";
import ScrollControls from "./components/ScrollControls";
import { AppearanceBackdrop } from "./context/AppearanceContext";

export default function App() {
  return (
    <>
      <AppearanceBackdrop />
      <Routes>
        <Route path="/" element={<Navigate to="/user" replace />} />

        {/* ===== KHÁCH HÀNG ===== */}
        <Route path="/user" element={<UserLayout />}>
          {/* Công khai: khám phá phim, rạp, suất chiếu, chọn ghế */}
          <Route index element={<HomePage />} />
          <Route path="movies" element={<MovieListPage />} />
          <Route path="movies/:id" element={<MovieDetailPage />} />
          <Route path="promotions" element={<PromotionsPage />} />
          <Route path="news" element={<NewsPage />} />
          <Route path="events" element={<EventsPage />} />
          <Route path="membership" element={<MembershipPage />} />
          <Route path="settings" element={<SettingsPage />} />
          <Route path="shop" element={<ShopPage />} />
          <Route path="watch" element={<MovieWatchPage />} />
          <Route path="watch/:id" element={<MovieWatchPage />} />
          <Route path="cinemas" element={<CinemaListPage />} />
          <Route path="showtimes/:movieId" element={<ShowtimePage />} />
          <Route path="seats/:showtimeId" element={<SeatSelectionPage />} />
          <Route path="login" element={<LoginPage />} />
          <Route path="register" element={<RegisterPage />} />
          {/* Cần đăng nhập: từ bước xác nhận đặt vé trở đi */}
          <Route element={<ProtectedRoute />}>
            <Route path="checkout" element={<CheckoutPage />} />
            <Route path="food" element={<FoodPage />} />
            <Route path="payment" element={<PaymentPage />} />
            <Route path="booking-success/:code" element={<BookingSuccessPage />} />
            <Route path="my-tickets" element={<MyTicketsPage />} />
            <Route path="profile" element={<ProfilePage />} />
          </Route>
        </Route>

        {/* ===== QUẢN LÝ RẠP (MANAGER, ADMIN) ===== */}
        <Route path="/manager" element={<ProtectedRoute roles={["EMPLOYEE", "MANAGER", "ADMIN"]} loginPath="/manager/login"><ManagerLayout /></ProtectedRoute>}>
          <Route index element={<ManagerDashboard />} />
          <Route path="movies" element={<MovieManagement />} />
          <Route path="cinemas" element={<CinemaManagement />} />
          <Route path="promotions" element={<PromotionManagement />} />
          <Route path="events" element={<EventManagement />} />
          <Route path="news" element={<NewsManagement />} />
          <Route path="rooms" element={<RoomManagement />} />
          <Route path="seats" element={<SeatManagement />} />
          <Route path="showtimes" element={<ShowtimeManagement />} />
          <Route path="bookings" element={<BookingManagement />} />
          <Route path="transactions" element={<TransactionManagement />} />
          <Route path="foods" element={<FoodManagement />} />
          <Route path="products" element={<ManagerProductManagement />} />
          <Route path="report" element={<ReportPage />} />
          <Route path="support" element={<SupportInboxPage />} />
        </Route>

        {/* ===== QUẢN TRỊ (chỉ ADMIN) ===== */}
        <Route path="/admin/login" element={<AdminLoginPage />} />
        <Route path="/manager/login" element={<StaffLoginPage />} />
        <Route path="/staff/register" element={<StaffApplicationPage />} />
        <Route path="/admin" element={<ProtectedRoute roles={["ADMIN"]} loginPath="/admin/login"><AdminLayout /></ProtectedRoute>}>
          <Route index element={<AdminDashboard />} />
          <Route path="users" element={<UserManagement />} />
          <Route path="pending-registrations" element={<PendingRegistrationsPage />} />
          <Route path="gmail-assistant" element={<GmailAssistantPage />} />
          <Route path="managers" element={<ManagerManagement />} />
          <Route path="movies" element={<AdminMovieManagement />} />
          <Route path="watch-films" element={<AdminWatchFilmManagement />} />
          <Route path="cinemas" element={<CinemaCatalogManagement />} />
          <Route path="showtimes" element={<AdminShowtimeManagement />} />
          <Route path="seats" element={<SeatManagement />} />
          <Route path="transactions" element={<TransactionManagement />} />
          <Route path="promotions" element={<PromotionManagement />} />
          <Route path="events" element={<EventManagement />} />
          <Route path="news" element={<NewsManagement />} />
          <Route path="foods" element={<FoodCatalogManagement />} />
          <Route path="products" element={<ProductManagement />} />
          <Route path="ai" element={<FeatureGate feature="ai" fallback="/admin"><AIManagement /></FeatureGate>} />
          <Route path="roles" element={<RoleManagement />} />
          <Route path="staff-applications" element={<StaffApplicationsPage />} />
          <Route path="settings" element={<SystemSettings />} />
          <Route path="support" element={<SupportInboxPage />} />
          <Route path="logs" element={<ActivityLog />} />
        </Route>

        <Route path="*" element={<Navigate to="/user" replace />} />
      </Routes>
      <AuthModal />
      <SupportChatWidget />
      <ClickEffects />
      <ScrollControls />
    </>
  );
}
