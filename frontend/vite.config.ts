import { defineConfig } from "vitest/config";
import { loadEnv } from "vite";
import react from "@vitejs/plugin-react";
export default defineConfig(({ mode }) => {
  const apiTarget =
    loadEnv(mode, ".", "").API_PROXY_TARGET || "http://127.0.0.1:8000";
  return {
    plugins: [react()],
    server: {
      proxy: { "/api": { target: apiTarget, ws: true }, "/uploads": apiTarget },
    },
    test: {
      environment: "jsdom",
      setupFiles: "./src/test-setup.ts",
      include: ["src/**/*.test.ts*"],
    },
  };
});
