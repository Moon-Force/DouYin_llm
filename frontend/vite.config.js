// Vite 开发服务器配置。
// 这里最重要的是代理配置：
// - 浏览器始终走同源路径 `/api` 和 `/ws`
// - Vite 再把这些请求转发到 8010 端口的 Python 后端
import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";

export default defineConfig({
  plugins: [vue()],
  server: {
    port: 5173,
    proxy: {
      // bootstrap、切房和 SSE 都通过这组 REST 路径访问后端。
      "/api": "http://127.0.0.1:8010",
      "/ws": {
        // 为后端 WebSocket 路径做透传。
        target: "ws://127.0.0.1:8010",
        ws: true,
      },
    },
  },
});
