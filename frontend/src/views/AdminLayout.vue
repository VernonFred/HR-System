<script setup lang="ts">
import { computed, ref, onMounted } from "vue";
import { useRoute } from "vue-router";
import Sidebar, { type PageKey } from "../components/Sidebar.vue";
import { useAuthStore } from "../stores/auth";

const route = useRoute();
const authStore = useAuthStore();

// 根据当前路由计算活动页面
const activePage = computed<PageKey>(() => {
  const name = route.name as string;
  // 支持新的页面类型
  const validPages: PageKey[] = [
    "candidates", 
    "jobprofiles", 
    "assessments", 
    "questionnaire-center",
    "users",
    "settings"
  ];
  if (validPages.includes(name as PageKey)) {
    return name as PageKey;
  }
  return "candidates";
});

// ⭐ Token 过期提醒
const showTokenWarning = ref(false);
const tokenWarningMessage = ref("");
const tokenDaysRemaining = ref<number | null>(null);

const checkTokenExpiry = async () => {
  // 已禁用：使用长期 Token 后不再需要过期提醒
  // 如需重新启用，取消下方注释
  /*
  try {
    const response = await fetch('/api/ai/router-status', {
      headers: {
        'Authorization': `Bearer ${authStore.token}`,
      },
    });
    if (response.ok) {
      const data = await response.json();
      const status = data.api_key_status;
      
      // 如果剩余天数少于 7 天，显示提醒
      if (status?.days_remaining !== null && status.days_remaining < 7) {
        tokenDaysRemaining.value = status.days_remaining;
        tokenWarningMessage.value = status.warning || `Token 将在 ${status.days_remaining} 天后过期`;
        showTokenWarning.value = true;
      }
    }
  } catch (error) {
    console.error('检查Token状态失败:', error);
  }
  */
};

const dismissTokenWarning = () => {
  showTokenWarning.value = false;
  // 保存到 localStorage，24小时内不再提醒
  localStorage.setItem('tokenWarningDismissed', Date.now().toString());
};

const goToSettings = () => {
  showTokenWarning.value = false;
  window.location.href = '/settings';
};

onMounted(() => {
  // 检查是否已经关闭过提醒（24小时内不再提醒）
  const dismissed = localStorage.getItem('tokenWarningDismissed');
  if (dismissed) {
    const dismissedTime = parseInt(dismissed);
    const hoursPassed = (Date.now() - dismissedTime) / (1000 * 60 * 60);
    if (hoursPassed < 24) {
      return; // 24小时内不再检查
    }
  }
  
  // 延迟 2 秒后检查，避免影响页面加载
  setTimeout(checkTokenExpiry, 2000);
});
</script>

<template>
  <div class="app-container">
    <div class="wip-shell">
      <Sidebar :active="activePage" />

      <main class="main">
        <router-view />
      </main>
    </div>
    
    <!-- Token 过期提醒弹窗 -->
    <Teleport to="body">
      <Transition name="modal">
        <div v-if="showTokenWarning" class="token-warning-overlay" @click.self="dismissTokenWarning">
          <div class="token-warning-modal">
            <div class="warning-icon">
              <i class="ri-error-warning-fill"></i>
            </div>
            <h3>API Token 即将过期</h3>
            <p class="warning-message">{{ tokenWarningMessage }}</p>
            <p v-if="tokenDaysRemaining !== null" class="days-remaining">
              剩余 <strong>{{ tokenDaysRemaining }}</strong> 天
            </p>
            <p class="warning-hint">请及时更新 Token，以免影响 AI 画像功能的正常使用。</p>
            <div class="warning-actions">
              <button class="btn-dismiss" @click="dismissTokenWarning">稍后提醒</button>
              <button class="btn-goto-settings" @click="goToSettings">
                <i class="ri-settings-4-line"></i>
                前往设置
              </button>
            </div>
          </div>
        </div>
      </Transition>
    </Teleport>
  </div>
</template>

<style scoped>
.app-container {
  min-height: 100vh;
  background: var(--bg-base);
  color: var(--text-primary);
  display: flex;
  flex-direction: column;
  padding: var(--space-3);
  gap: var(--space-3);
}

.wip-shell {
  display: grid;
  grid-template-columns: 240px 1fr;
  gap: var(--space-4);
  height: calc(100vh - 80px);
}

.sidebar {
  background: var(--bg-subtle);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-lg);
  padding: var(--space-4);
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

.sidebar-header {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  font-weight: 700;
  letter-spacing: 0.2px;
}

.logo-dot {
  width: 12px;
  height: 12px;
  border-radius: var(--radius-full);
  background: var(--gradient-primary);
  box-shadow: 0 0 0 6px rgba(99, 102, 241, 0.12);
}

.logo-title {
  font-size: var(--text-lg);
}

.nav-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.nav-item {
  width: 100%;
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: 10px 12px;
  border-radius: var(--radius-md);
  border: 1px solid transparent;
  background: transparent;
  color: var(--text-secondary);
  cursor: pointer;
  transition: background var(--transition-base), color var(--transition-base), border var(--transition-base);
}

.nav-item i {
  font-size: 18px;
}

.nav-item.active {
  background: rgba(99, 102, 241, 0.08);
  border-color: var(--border-default);
  color: var(--text-primary);
}

.sidebar-footer {
  margin-top: auto;
}

.user-card {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: 10px;
  background: var(--bg-muted);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
}

.user-avatar {
  width: 36px;
  height: 36px;
  border-radius: var(--radius-full);
  background: var(--gradient-primary);
  display: grid;
  place-items: center;
  font-weight: 700;
}

.user-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.user-name {
  font-weight: 600;
}

.user-role {
  color: var(--text-tertiary);
  font-size: var(--text-sm);
}

.main {
  background: var(--bg-subtle);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-lg);
  padding: var(--space-5);
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
  overflow: auto;
}

.main-header {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.page-title {
  font-size: var(--text-2xl);
  font-weight: 700;
}

.page-subtitle {
  color: var(--text-tertiary);
  font-size: var(--text-sm);
}

.content-placeholder {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

.placeholder-card {
  display: flex;
  gap: var(--space-3);
  align-items: center;
  padding: var(--space-4);
  background: var(--bg-muted);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-lg);
}

.placeholder-dot {
  width: 12px;
  height: 12px;
  border-radius: var(--radius-full);
  background: var(--accent-primary);
  box-shadow: 0 0 0 10px rgba(99, 102, 241, 0.08);
}

.placeholder-title {
  font-weight: 600;
  font-size: var(--text-lg);
}

.placeholder-desc {
  color: var(--text-tertiary);
  font-size: var(--text-sm);
}

.placeholder-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: var(--space-3);
}

.placeholder-box {
  padding: var(--space-4);
  background: var(--bg-muted);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
}

.placeholder-label {
  font-weight: 600;
  margin-bottom: var(--space-2);
}

.placeholder-text {
  color: var(--text-tertiary);
  font-size: var(--text-sm);
}

@media (max-width: 960px) {
  .wip-shell {
    grid-template-columns: 1fr;
    height: auto;
  }
  .sidebar {
    flex-direction: row;
    align-items: center;
    justify-content: space-between;
  }
  .nav-list {
    flex-direction: row;
    flex-wrap: wrap;
  }
}

/* Token 过期提醒弹窗样式 */
.token-warning-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 10000;
  backdrop-filter: blur(4px);
}

.token-warning-modal {
  background: white;
  border-radius: 20px;
  padding: 2rem;
  max-width: 420px;
  width: 90%;
  text-align: center;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.2);
}

.warning-icon {
  width: 72px;
  height: 72px;
  border-radius: 50%;
  background: linear-gradient(135deg, #fef3c7 0%, #fde68a 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto 1.5rem;
  font-size: 2.5rem;
  color: #d97706;
}

.token-warning-modal h3 {
  font-size: 1.375rem;
  font-weight: 700;
  color: #1f2937;
  margin: 0 0 0.75rem;
}

.warning-message {
  font-size: 0.9375rem;
  color: #6b7280;
  margin: 0 0 0.5rem;
}

.days-remaining {
  font-size: 1.125rem;
  color: #d97706;
  margin: 0 0 1rem;
}

.days-remaining strong {
  font-size: 1.5rem;
  font-weight: 700;
}

.warning-hint {
  font-size: 0.8125rem;
  color: #9ca3af;
  margin: 0 0 1.5rem;
  padding: 0.75rem 1rem;
  background: #f9fafb;
  border-radius: 8px;
}

.warning-actions {
  display: flex;
  gap: 0.75rem;
  justify-content: center;
}

.btn-dismiss {
  padding: 0.75rem 1.5rem;
  background: #f3f4f6;
  color: #6b7280;
  border: none;
  border-radius: 10px;
  font-size: 0.9375rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-dismiss:hover {
  background: #e5e7eb;
}

.btn-goto-settings {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.75rem 1.5rem;
  background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);
  color: white;
  border: none;
  border-radius: 10px;
  font-size: 0.9375rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-goto-settings:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(245, 158, 11, 0.3);
}

/* 弹窗动画 */
.modal-enter-active,
.modal-leave-active {
  transition: all 0.3s ease;
}

.modal-enter-from,
.modal-leave-to {
  opacity: 0;
}

.modal-enter-from .token-warning-modal,
.modal-leave-to .token-warning-modal {
  transform: scale(0.9) translateY(20px);
}
</style>
