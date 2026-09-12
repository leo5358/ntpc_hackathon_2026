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
          // Intercept browser extension injected source maps (e.g. installHook.js.map)
          if (req.url && req.url.includes(".map") && !req.url.startsWith("/@fs/")) {
            res.statusCode = 404;
            res.end();
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
