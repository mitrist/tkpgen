import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  base: "/max-app/",
  build: {
    outDir: "../../proposals/static/max-app",
    emptyOutDir: true,
    manifest: false,
    rollupOptions: {
      output: {
        entryFileNames: "app.js",
        assetFileNames: "app.[ext]",
        chunkFileNames: "chunk-[name].js",
      },
    },
  },
});
