import { resolve } from "node:path";
import { defineConfig } from "vite";

// Builds straight into the integration so HACS users need no build step.
export default defineConfig({
  build: {
    outDir: resolve(__dirname, "../custom_components/paperlessoffline/frontend"),
    emptyOutDir: true,
    target: "es2021",
    minify: true,
    sourcemap: false,
    lib: {
      entry: {
        "paperlessoffline-panel": resolve(__dirname, "src/panel.ts"),
        "paperlessoffline-card": resolve(__dirname, "src/card.ts"),
      },
      formats: ["es"],
    },
    rollupOptions: {
      output: {
        entryFileNames: "[name].js",
        chunkFileNames: "chunk-[hash].js",
      },
    },
  },
});
