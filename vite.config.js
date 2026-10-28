import path from "node:path";
import { fileURLToPath } from "node:url";
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

const rootDirectory = path.dirname(fileURLToPath(import.meta.url));

export default defineConfig({
  base: "/static/dashboard-ui/",
  plugins: [react()],
  build: {
    outDir: path.resolve(rootDirectory, "static/dashboard-ui"),
    emptyOutDir: true,
    rollupOptions: {
      input: path.resolve(rootDirectory, "frontend/main.jsx"),
      output: {
        entryFileNames: "dashboard.js",
        assetFileNames: "dashboard[extname]",
        chunkFileNames: "chunks/[name]-[hash].js",
        manualChunks(id) {
          if (id.includes("/node_modules/recharts/")) return "recharts";
          if (id.includes("/node_modules/victory-vendor/")) return "chart-vendor";
        },
      },
    },
  },
});