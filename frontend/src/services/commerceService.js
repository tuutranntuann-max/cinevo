import { api } from "./api";

export const commerceService = {
  settings: () => api.get("/commerce/settings"),
  plans: () => api.get("/commerce/membership/plans"),
  membership: () => api.get("/commerce/membership/mine"),
  buyMembership: (tier) => api.post("/commerce/membership/purchases", { tier }),
  products: () => api.get("/commerce/shop/products"),
  createShopOrder: (items, pickup_cinema_id) => api.post("/commerce/shop/orders", { items, pickup_cinema_id }),
  shopOrders: () => api.get("/commerce/shop/orders/mine"),
  staffShopOrders: () => api.get("/commerce/admin/shop/orders"),
  updateShopOrder: (id, status) => api.patch(`/commerce/admin/shop/orders/${id}`, { status }),
  saveSeatHolds: (showtime_id, seat_ids) => api.post("/commerce/seat-holds", { showtime_id, seat_ids }),
  releaseSeatHolds: (showtime_id) => api.delete(`/commerce/seat-holds/${showtime_id}`),
  mySeatHolds: (showtime_id) => api.get(`/commerce/seat-holds/my/${showtime_id}`),
  pendingPayments: () => api.get("/commerce/admin/pending"),
  transactionHistory: () => api.get("/commerce/admin/history"),
  adminSettings: () => api.get("/commerce/admin/settings"),
  updateAdminSettings: (values) => api.patch("/commerce/admin/settings", values),
  reviewPayments: (items, approved = true) => api.post("/commerce/admin/approve", { items, approved }),
  trust: () => api.get("/commerce/trust"),
};
