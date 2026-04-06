// 前端启动入口。
// 主要职责：
// 1. 创建 Vue 应用实例。
// 2. 注册 Pinia，让整个页面共享同一份直播状态。
// 3. 在挂载前加载全局样式主题。
import { createApp } from "vue";
import { createPinia } from "pinia";

import App from "./App.vue";
import "./assets/main.css";

const app = createApp(App);
// Pinia 统一管理房间状态、SSE 连接状态、事件列表和提词建议。
app.use(createPinia());
// 挂载到 `frontend/index.html` 里声明的根节点。
app.mount("#app");
