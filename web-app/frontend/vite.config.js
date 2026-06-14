import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// In dev, proxy API + WebSocket calls to the FastAPI backend on :8082 so the
// frontend can use same-origin relative URLs everywhere.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": { target: "http://localhost:8082", changeOrigin: true },
      "/ws": { target: "ws://localhost:8082", ws: true },
    },
  },
  build: { outDir: "dist" },
});
