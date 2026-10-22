import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Proxy /api -> Flask (localhost:5000) để frontend gọi API không bị lỗi CORS khi dev.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: { "/api": { target: "http://localhost:5000", changeOrigin: true } },
  },
});
