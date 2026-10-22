import { useEffect, useState } from "react";
import AdminCatalogPage from "../../components/AdminCatalogPage";
import ErrorBox from "../../components/ErrorBox";
import { commerceService } from "../../services/commerceService";
import { formatVND } from "../../utils/format";

export default function ShopManagement() {
  const [orders, setOrders] = useState([]);
  const [error, setError] = useState("");

  const load = () => commerceService.staffShopOrders().then(setOrders).catch((e) => setError(e.message));
  useEffect(() => { load(); }, []);

  const update = async (order, status) => {
    setError("");
    try {
      await commerceService.updateShopOrder(order.id, status);
      await load();
    } catch (e) { setError(e.message); }
  };

  return (
    <>
      <AdminCatalogPage title="Quản lý Shop & hàng tồn kho" endpoint="/manager/products" kind="product" />
      <section>
        <h2 className="section-title">Đơn hàng Shop và nhận tại rạp</h2>
        <ErrorBox message={error} />
        <div className="table-wrap">
          <table className="data-table">
            <thead><tr><th>Mã đơn</th><th>Khách hàng</th><th>Sản phẩm</th><th>Rạp nhận</th><th>Thanh toán</th><th>Thao tác</th></tr></thead>
            <tbody>{orders.map((order) => (
              <tr key={order.id}>
                <td><code>{order.code}</code><br /><small>{order.status}</small></td>
                <td>{order.customer_name}<br /><small>{order.customer_email}</small></td>
                <td>{order.items.map((item) => `${item.name} ×${item.quantity}`).join(", ")}<br /><b>{formatVND(order.total_amount)}</b></td>
                <td>{order.pickup_cinema}</td>
                <td>{order.status === "READY_FOR_PICKUP" || order.status === "COLLECTED" ? "Đã xác nhận" : "Chờ xác nhận"}</td>
                <td>
                  {order.status === "READY_FOR_PICKUP" && <button className="btn btn-red btn-sm" onClick={() => update(order, "COLLECTED")}>Đã giao hàng</button>}
                  {order.status === "PENDING" && <span className="muted small">Xác nhận thanh toán tại mục Giao dịch</span>}
                </td>
              </tr>
            ))}{!orders.length && <tr><td colSpan="6" className="muted">Chưa có đơn hàng Shop.</td></tr>}</tbody>
          </table>
        </div>
      </section>
    </>
  );
}
