// Trợ lý Cinevo chạy bằng logic nội bộ của backend, không gọi dịch vụ AI bên ngoài.
import { api } from "./api";

export const aiService = {
  recommendMovies: (genre) => api.get(`/ai/recommend-movies${genre ? `?genre=${encodeURIComponent(genre)}` : ""}`),
  recommendSeats: (showtimeId, count) => api.get(`/ai/recommend-seats?showtime_id=${showtimeId}&count=${count}`),
  chat: (message) => api.post("/chatbot/chat", { message }),
};
