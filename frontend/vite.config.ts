import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

const securityHeaders = {
  "Permissions-Policy": "camera=(), microphone=(), geolocation=(), payment=()",
  "Referrer-Policy": "no-referrer",
  "X-Content-Type-Options": "nosniff",
  "X-Frame-Options": "DENY",
};

export default defineConfig({
  build: {
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (id.includes("node_modules/@xyflow")) {
            return "xyflow";
          }
          if (id.includes("node_modules/dagre")) {
            return "dagre";
          }
          return undefined;
        },
      },
    },
  },
  plugins: [react()],
  preview: {
    headers: securityHeaders,
  },
  server: {
    headers: securityHeaders,
  },
  test: {
    environment: "node",
    include: ["src/**/*.test.ts"],
  },
});
