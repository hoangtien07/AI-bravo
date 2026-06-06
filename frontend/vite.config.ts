import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Dev: proxy mọi lời gọi API sang FastAPI (uvicorn api:app, cổng 8000) → frontend luôn
// dùng đường dẫn TƯƠNG ĐỐI ("/ask"...) ở cả dev lẫn prod, không lo CORS / hardcode host.
const API = "http://127.0.0.1:8000";
const ROUTES = ["/ask", "/suggest", "/generate", "/tasks", "/scoreboard", "/feedback", "/healthz", "/health"];

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: Object.fromEntries(ROUTES.map((r) => [r, { target: API, changeOrigin: true }])),
  },
  build: { outDir: "dist" },
});
