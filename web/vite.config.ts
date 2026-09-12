import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [
    react(),
    {
      name: "ignore-devtools-sourcemap",
      configureServer(server) {
        server.middlewares.use((req, res, next) => {
          // Gracefully serve valid empty source map for extension injected scripts
          if (req.url && req.url.includes(".map") && !req.url.startsWith("/@fs/")) {
            res.statusCode = 200;
            res.setHeader("Content-Type", "application/json");
            res.end(JSON.stringify({ version: 3, file: "", sources: [], mappings: "" }));
            return;
          }
          next();
        });
      },
    },
  ],
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
});
