import { useEffect, useState } from "react";
import ErrorBox from "../../components/ErrorBox";
import PaymentMethodInstructions from "../../components/PaymentMethodInstructions";
import { useAuth } from "../../context/AuthContext";
import { commerceService } from "../../services/commerceService";
import { movieService } from "../../services/movieService";
import { formatVND } from "../../utils/format";
import { useUserPreferences } from "../../context/UserPreferencesContext";

export default function ShopPage() {
  const { t } = useUserPreferences();
  const { user, requireLogin } = useAuth();
  const [products, setProducts] = useState([]);
  const [cinemas, setCinemas] = useState([]);
  const [settings, setSettings] = useState(null);
  const [membership, setMembership] = useState(null);
  const [quantities, setQuantities] = useState({});
  const [pickup, setPickup] = useState("");
  const [order, setOrder] = useState(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const load = async () => {
    try {
      const [items, bankSettings, membershipInfo] = await Promise.all([
        commerceService.products(),
        commerceService.settings(),
        user ? commerceService.membership() : Promise.resolve(null),
      ]);
      setProducts(items);
      setSettings(bankSettings);
      setMembership(membershipInfo?.active || null);
      setCinemas(await movieService.cinemas());
    } catch (e) { setError(e.message); }
  };
  useEffect(() => { load(); }, [user?.id]);
  useEffect(() => {
    if (!order) return undefined;
    const timer = window.setInterval(() => {
      commerceService.shopOrders().then((orders) => {
        const latest = orders.find((item) => item.code === order.code);
        if (latest) setOrder(latest);
      }).catch((e) => setError(e.message));
    }, 5000);
    return () => window.clearInterval(timer);
  }, [order?.code]);

  const cart = products
    .filter((product) => quantities[product.id] > 0)
    .map((product) => ({ product_id: product.id, quantity: quantities[product.id] }));
  const discountRate = { SILVER: 15, GOLD: 30, DIAMOND: 45 }[membership?.tier] || 0;
  const subtotal = products.reduce((sum, product) => sum + product.price * (quantities[product.id] || 0), 0);
  const total = subtotal - Math.floor(subtotal * discountRate / 100);
  const paymentReady = Boolean(settings?.bank_bin && settings?.account_number);

  const createOrder = () => {
    if (!cart.length) return setError(t("Hãy chọn ít nhất một sản phẩm."));
    if (!pickup) return setError(t("Chọn rạp bạn sẽ đến nhận hàng."));
    setBusy(true); setError("");
    commerceService.createShopOrder(cart, Number(pickup))
      .then(setOrder)
      .catch((e) => setError(e.message))
      .finally(() => setBusy(false));
  };
  const checkout = () => {
    if (!user) return requireLogin(() => createOrder());
    createOrder();
  };

  return (
    <section>
      <header className="page-heading">
        <p className="eyebrow">CINEVO SHOP</p>
        <h1 className="page-title">{t("Kính 3D & vật tư điện ảnh")}</h1>
        <p className="muted">{t("Đặt hàng trực tuyến, thanh toán chuyển khoản và nhận hàng tại rạp.")}</p>
      </header>
      <ErrorBox message={error} />
      {products.length ? (
        <div className="shop-grid">
          {products.map((product) => (
            <article className="card shop-product" key={product.id}>
              <span className="eyebrow">{product.category}</span>
              <h2>{product.name}</h2>
              <p className="muted">{product.description}</p>
              <p><b>{formatVND(product.price)}</b> <small>· {t("Còn")} {product.stock_quantity}</small></p>
              <label>{t("Số lượng")}
                <input type="number" min="0" max={product.stock_quantity} value={quantities[product.id] || 0}
                  onChange={(e) => setQuantities((current) => ({
                    ...current, [product.id]: Math.max(0, Math.min(product.stock_quantity, Number(e.target.value) || 0)),
                  }))} />
              </label>
            </article>
          ))}
        </div>
      ) : <div className="state-box">{t("Shop chưa có sản phẩm đang bán. Sản phẩm sẽ xuất hiện sau khi quản lý cập nhật kho hàng.")}</div>}
      {!order && products.length > 0 && (
        <div className="shop-checkout card">
          <h2>{t("Giỏ hàng")}</h2>
          {discountRate > 0 && <p className="notice">{t("Hạng")} {membership.tier}: {discountRate}% {t("được giảm giá cho hàng hóa.")}</p>}
          <label>{t("Rạp nhận hàng")}
            <select value={pickup} onChange={(e) => setPickup(e.target.value)} required>
              <option value="">{t("Chọn rạp nhận hàng")}</option>
              {cinemas.map((cinema) => <option key={cinema.id} value={cinema.id}>{cinema.name} · {cinema.city}</option>)}
            </select>
          </label>
          <p>{t("Tạm tính:")} <b>{formatVND(total)}</b>{discountRate > 0 && <small className="muted"> · {t("Trước ưu đãi:")} {formatVND(subtotal)}</small>}</p>
          {!paymentReady && <p className="hint">{t("Admin cần cấu hình ngân hàng nhận tiền và số tài khoản trước khi mở thanh toán Shop.")}</p>}
          <button className="btn btn-red" disabled={busy || !cart.length || !paymentReady} onClick={checkout}>
            {busy ? t("Đang tạo đơn...") : t("Tạo đơn và nhận mã chuyển khoản")}
          </button>
        </div>
      )}
      {order && (
        <div className="commerce-checkout">
          <h2>{t("Đơn hàng")} {order.code}</h2>
          {order.status === "READY_FOR_PICKUP" && <div className="success">{t("Đã xác nhận thanh toán. Đơn hàng sẵn sàng để nhận tại rạp.")}</div>}
          <p>{t("Nhận tại:")} {order.pickup_cinema} · {t("Tạm tính")} {formatVND(order.subtotal)} · {t("Ưu đãi")} {formatVND(order.discount_amount)}</p>
          {order.status === "PENDING" && <PaymentMethodInstructions settings={settings} amount={order.total_amount} reference={order.code} />}
        </div>
      )}
    </section>
  );
}
