import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// The dashboard proxies /api to the FastAPI backend on :8000 during dev.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": "http://127.0.0.1:8000",
    },
  },
});
