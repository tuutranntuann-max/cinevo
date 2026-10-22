import StatsDashboard from "../../components/StatsDashboard";

export default function AdminDashboard() {
  return <StatsDashboard title="Tổng quan hệ thống" endpoint="/admin/dashboard" />;
}
