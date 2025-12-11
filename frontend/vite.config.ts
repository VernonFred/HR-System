import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";
import path from "path";

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  build: {
    chunkSizeWarningLimit: 800,
    rollupOptions: {
      output: {
        manualChunks: {
          echarts: [
            "echarts/core",
            "echarts/charts",
            "echarts/components",
            "echarts/renderers",
          ],
        },
      },
    },
  },
  server: {
    host: "0.0.0.0",
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:9000',
        changeOrigin: true,
      },
      '/auth': {
        target: 'http://localhost:9000',
        changeOrigin: true,
      },
      '/questionnaires': {
        target: 'http://localhost:9000',
        changeOrigin: true,
      },
      '/submissions': {
        target: 'http://localhost:9000',
        changeOrigin: true,
      },
      '/analytics': {
        target: 'http://localhost:9000',
        changeOrigin: true,
      },
      '/health': {
        target: 'http://localhost:9000',
        changeOrigin: true,
      },
    },
  },
  preview: {
    host: "0.0.0.0",
    port: 4173,
  },
});
