import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

export default defineConfig(({ isSsrBuild }) => ({
  plugins: [react()],
  build: {
    // La compilación del prerenderizado (dist-ssr/) solo necesita el JavaScript: sin copiar los
    // ~40 MB de public/media.
    copyPublicDir: !isSsrBuild,
  },
  test: {
    environment: "jsdom",
    setupFiles: ["src/test/setup.ts"],
    include: ["src/**/*.test.{ts,tsx}", "scripts/**/*.test.ts"],
    restoreMocks: true,
  },
}));
