import { api } from "./api";

export const authService = {
  register: (payload) => api.post("/auth/register", payload),
  verifyOtp: (email, code) => api.post("/auth/verify-otp", { email, code }),
  resendOtp: (email) => api.post("/auth/resend-otp", { email }),
  login: (email, password) => api.post("/auth/login", { email, password }),
  me: () => api.get("/auth/me"),
  updateMe: (payload) => api.put("/auth/me", payload),
  uploadAvatar: (file) => {
    const formData = new FormData();
    formData.append("image", file);
    return api.upload("/auth/me/avatar", formData);
  },
  deleteAvatar: () => api.delete("/auth/me/avatar"),
};
