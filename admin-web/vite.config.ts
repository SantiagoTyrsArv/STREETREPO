import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

const DEV_PORT = 5173; // el origen que la API permite por CORS en desarrollo

export default defineConfig({
  plugins: [react()],
  server: { port: DEV_PORT, strictPort: true },
  test: {
    environment: "jsdom",
    setupFiles: ["src/test/setup.ts"],
    include: ["src/**/*.test.{ts,tsx}"],
    restoreMocks: true,
    env: {
      VITE_API_BASE_URL: "http://api.test",
    },
  },
});
