import { api } from "./api";

export const bookingService = {
  validatePromotion: (code) => api.post("/promotions/validate", { code }),
  create: (payload) => api.post("/bookings", payload),
  mine: () => api.get("/bookings/my"),
  detail: (code) => api.get(`/bookings/${code}`),
};
