import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// 개발 서버에서 API·스크린샷 요청을 FastAPI(기본 127.0.0.1:8000)로 넘긴다.
const API_TARGET = process.env.VITE_API_TARGET ?? "http://127.0.0.1:8000";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": API_TARGET,
      "/screenshots": API_TARGET,
    },
  },
});
