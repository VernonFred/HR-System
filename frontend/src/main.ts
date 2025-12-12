import { createApp } from "vue";
import { createPinia } from "pinia";
import App from "./App.vue";
import router from "./router";
import { useAuthStore } from "./stores/auth";
import "./styles/legacy-variables.css";
import "./styles/index.css";
import "./styles/native-components.css"; // 原生组件美化样式

const app = createApp(App);
const pinia = createPinia();
app.use(pinia);
app.use(router);
app.mount("#app");

// 同步 token 更新（刷新/跨标签广播）
useAuthStore(pinia).startSync();
