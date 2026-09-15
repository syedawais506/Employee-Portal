import { fileURLToPath, URL } from "node:url";

import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": fileURLToPath(new URL("./src", import.meta.url)),
    },
  },
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: process.env.VITE_API_PROXY_TARGET ?? "http://localhost:8000",
        changeOrigin: true,
        ws: true,
      },
    },
  },
  build: {
    rollupOptions: {
      output: {
        // Vendor libraries change far less often than app code and are
        // shared across every route (unlike the per-page chunks from
        // routes/router.tsx's React.lazy split), so they get their own
        // cacheable chunk instead of being duplicated into/inflating every
        // route chunk.
        manualChunks: {
          "vendor-mui": ["@mui/material", "@mui/icons-material"],
          "vendor-charts": ["recharts"],
          "vendor-react": ["react", "react-dom", "react-router-dom"],
        },
      },
    },
  },
});
