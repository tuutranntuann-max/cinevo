import AdminCatalogPage from "../../components/AdminCatalogPage";

export default function ProductManagement() {
  return <AdminCatalogPage title="Quản lý hàng tồn kho" endpoint="/admin/products" kind="product" />;
}
