<script setup lang="ts">
import { ref, onMounted } from "vue";
import { useRouter } from "vue-router";
import { useAuthStore } from "../stores/auth";

const router = useRouter();
const authStore = useAuthStore();
const form = ref({ username: "", password: "" });
const isLoading = ref(false);
const showPassword = ref(false);

// 动画相关
const mounted = ref(false);
onMounted(() => {
  setTimeout(() => {
    mounted.value = true;
  }, 100);
});

const handleSubmit = async () => {
  if (!form.value.username || !form.value.password) {
    return;
  }
  isLoading.value = true;
  try {
    await authStore.login(form.value);
    router.push("/");
  } catch (err) {
    // error already set in store
  } finally {
    isLoading.value = false;
  }
};

const handleKeydown = (e: KeyboardEvent) => {
  if (e.key === 'Enter') {
    handleSubmit();
  }
};
</script>

<template>
  <div class="login-page">
    <!-- 背景装饰 -->
    <div class="bg-decoration">
      <div class="gradient-orb orb-1"></div>
      <div class="gradient-orb orb-2"></div>
      <div class="gradient-orb orb-3"></div>
      <div class="grid-pattern"></div>
    </div>

    <!-- 登录卡片 -->
    <div class="login-container" :class="{ mounted }">
      <!-- 品牌区域 -->
      <div class="brand-section">
        <div class="logo-container">
          <div class="logo-icon">
            <svg viewBox="0 0 40 40" fill="none" xmlns="http://www.w3.org/2000/svg">
              <rect width="40" height="40" rx="10" fill="url(#logo-gradient)"/>
              <path d="M12 14h6v6h-6zM22 14h6v6h-6zM12 24h6v2h-6zM22 24h6v2h-6z" fill="white" opacity="0.9"/>
              <path d="M15 20l5 5 5-5" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
              <defs>
                <linearGradient id="logo-gradient" x1="0" y1="0" x2="40" y2="40">
                  <stop offset="0%" stop-color="#667eea"/>
                  <stop offset="100%" stop-color="#764ba2"/>
                </linearGradient>
              </defs>
            </svg>
          </div>
          <div class="brand-text">
            <h1 class="brand-name">QZ·TalentLens</h1>
            <p class="brand-slogan">人员初步画像智能工具</p>
          </div>
        </div>
      </div>

      <!-- 登录表单 -->
    <div class="login-card">
        <div class="card-header">
          <h2>欢迎回来</h2>
          <p>请登录您的管理员账户</p>
        </div>

        <form class="login-form" @submit.prevent="handleSubmit">
          <div class="form-group">
            <label for="username">
              <svg class="field-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/>
                <circle cx="12" cy="7" r="4"/>
              </svg>
              用户名
            </label>
            <div class="input-wrapper">
              <input 
                id="username"
                v-model="form.username" 
                type="text"
                placeholder="请输入用户名"
                autocomplete="username"
                @keydown="handleKeydown"
              />
            </div>
          </div>

          <div class="form-group">
            <label for="password">
              <svg class="field-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <rect x="3" y="11" width="18" height="11" rx="2" ry="2"/>
                <path d="M7 11V7a5 5 0 0 1 10 0v4"/>
              </svg>
              密码
            </label>
            <div class="input-wrapper">
              <input 
                id="password"
                v-model="form.password" 
                :type="showPassword ? 'text' : 'password'"
                placeholder="请输入密码"
                autocomplete="current-password"
                @keydown="handleKeydown"
              />
              <button 
                type="button" 
                class="toggle-password"
                @click="showPassword = !showPassword"
              >
                <svg v-if="!showPassword" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/>
                  <circle cx="12" cy="12" r="3"/>
                </svg>
                <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"/>
                  <line x1="1" y1="1" x2="23" y2="23"/>
                </svg>
              </button>
            </div>
          </div>

          <button 
            type="submit" 
            class="submit-btn"
            :disabled="isLoading || !form.username || !form.password"
          >
            <span v-if="isLoading" class="loading-spinner"></span>
            <span v-else>登 录</span>
          </button>

          <p v-if="authStore.error" class="error-message">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="12" cy="12" r="10"/>
              <line x1="12" y1="8" x2="12" y2="12"/>
              <line x1="12" y1="16" x2="12.01" y2="16"/>
            </svg>
            {{ authStore.error }}
          </p>
        </form>
      </div>

      <!-- 版权信息 -->
      <div class="copyright">
        <p>© 2025 QZ·TalentLens · 人员初步画像智能工具</p>
      </div>
    </div>
  </div>
</template>

<style scoped>
.login-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #0f0f23 0%, #1a1a2e 50%, #16213e 100%);
  position: relative;
  overflow: hidden;
  padding: 20px;
}

/* 背景装饰 */
.bg-decoration {
  position: absolute;
  inset: 0;
  pointer-events: none;
  overflow: hidden;
}

.gradient-orb {
  position: absolute;
  border-radius: 50%;
  filter: blur(80px);
  opacity: 0.4;
}

.orb-1 {
  width: 600px;
  height: 600px;
  background: radial-gradient(circle, rgba(102, 126, 234, 0.6) 0%, transparent 70%);
  top: -200px;
  left: -200px;
  animation: float 20s ease-in-out infinite;
}

.orb-2 {
  width: 500px;
  height: 500px;
  background: radial-gradient(circle, rgba(118, 75, 162, 0.5) 0%, transparent 70%);
  bottom: -150px;
  right: -150px;
  animation: float 25s ease-in-out infinite reverse;
}

.orb-3 {
  width: 300px;
  height: 300px;
  background: radial-gradient(circle, rgba(99, 102, 241, 0.4) 0%, transparent 70%);
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  animation: pulse 10s ease-in-out infinite;
}

.grid-pattern {
  position: absolute;
  inset: 0;
  background-image: 
    linear-gradient(rgba(255, 255, 255, 0.02) 1px, transparent 1px),
    linear-gradient(90deg, rgba(255, 255, 255, 0.02) 1px, transparent 1px);
  background-size: 50px 50px;
}

@keyframes float {
  0%, 100% { transform: translate(0, 0); }
  50% { transform: translate(30px, 30px); }
}

@keyframes pulse {
  0%, 100% { transform: translate(-50%, -50%) scale(1); opacity: 0.4; }
  50% { transform: translate(-50%, -50%) scale(1.2); opacity: 0.2; }
}

/* 登录容器 */
.login-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 32px;
  z-index: 1;
  opacity: 0;
  transform: translateY(20px);
  transition: all 0.6s cubic-bezier(0.16, 1, 0.3, 1);
}

.login-container.mounted {
  opacity: 1;
  transform: translateY(0);
}

/* 品牌区域 */
.brand-section {
  text-align: center;
}

.logo-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;
}

.logo-icon {
  width: 72px;
  height: 72px;
  animation: logoFloat 3s ease-in-out infinite;
}

.logo-icon svg {
  width: 100%;
  height: 100%;
  filter: drop-shadow(0 8px 24px rgba(102, 126, 234, 0.4));
}

@keyframes logoFloat {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-8px); }
}

.brand-text {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.brand-name {
  font-size: 32px;
  font-weight: 800;
  background: linear-gradient(135deg, #fff 0%, #a5b4fc 50%, #818cf8 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  letter-spacing: 2px;
  margin: 0;
}

.brand-slogan {
  font-size: 14px;
  color: rgba(255, 255, 255, 0.5);
  letter-spacing: 4px;
  margin: 0;
}

/* 登录卡片 */
.login-card {
  width: 100%;
  max-width: 420px;
  background: rgba(255, 255, 255, 0.03);
  backdrop-filter: blur(20px);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 24px;
  padding: 40px;
  box-shadow: 
    0 4px 24px rgba(0, 0, 0, 0.2),
    0 0 0 1px rgba(255, 255, 255, 0.05) inset;
}

.card-header {
  text-align: center;
  margin-bottom: 32px;
}

.card-header h2 {
  font-size: 24px;
  font-weight: 700;
  color: #fff;
  margin: 0 0 8px 0;
}

.card-header p {
  font-size: 14px;
  color: rgba(255, 255, 255, 0.5);
  margin: 0;
}

/* 表单样式 */
.login-form {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.form-group label {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  font-weight: 600;
  color: rgba(255, 255, 255, 0.8);
}

.field-icon {
  width: 16px;
  height: 16px;
  color: rgba(255, 255, 255, 0.5);
}

.input-wrapper {
  position: relative;
}

.input-wrapper input {
  width: 100%;
  padding: 14px 16px;
  font-size: 15px;
  color: #fff;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 12px;
  outline: none;
  transition: all 0.3s ease;
}

.input-wrapper input::placeholder {
  color: rgba(255, 255, 255, 0.3);
}

.input-wrapper input:focus {
  border-color: rgba(102, 126, 234, 0.6);
  background: rgba(255, 255, 255, 0.08);
  box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.15);
}

.toggle-password {
  position: absolute;
  right: 12px;
  top: 50%;
  transform: translateY(-50%);
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: transparent;
  border: none;
  cursor: pointer;
  color: rgba(255, 255, 255, 0.4);
  transition: color 0.2s;
}

.toggle-password:hover {
  color: rgba(255, 255, 255, 0.7);
}

.toggle-password svg {
  width: 18px;
  height: 18px;
}

/* 提交按钮 */
.submit-btn {
  width: 100%;
  padding: 16px;
  font-size: 16px;
  font-weight: 700;
  color: #fff;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border: none;
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.3s ease;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  margin-top: 8px;
  position: relative;
  overflow: hidden;
}

.submit-btn::before {
  content: '';
  position: absolute;
  inset: 0;
  background: linear-gradient(135deg, #764ba2 0%, #667eea 100%);
  opacity: 0;
  transition: opacity 0.3s;
}

.submit-btn:hover:not(:disabled)::before {
  opacity: 1;
}

.submit-btn:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 8px 24px rgba(102, 126, 234, 0.4);
}

.submit-btn:active:not(:disabled) {
  transform: translateY(0);
}

.submit-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.submit-btn span {
  position: relative;
  z-index: 1;
}

.loading-spinner {
  width: 20px;
  height: 20px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-top-color: #fff;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

/* 错误信息 */
.error-message {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 16px;
  background: rgba(239, 68, 68, 0.1);
  border: 1px solid rgba(239, 68, 68, 0.2);
  border-radius: 10px;
  color: #fca5a5;
  font-size: 14px;
  margin: 0;
}

.error-message svg {
  width: 18px;
  height: 18px;
  flex-shrink: 0;
}

/* 卡片底部 */
.card-footer {
  margin-top: 24px;
  padding-top: 24px;
  border-top: 1px solid rgba(255, 255, 255, 0.06);
  background: transparent;
}

.hint {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  font-size: 13px;
  color: rgba(255, 255, 255, 0.4);
  margin: 0;
}

.hint svg {
  width: 16px;
  height: 16px;
}

/* 版权信息 */
.copyright {
  text-align: center;
}

.copyright p {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.3);
  margin: 0;
}

/* 响应式 */
@media (max-width: 480px) {
  .login-card {
    padding: 32px 24px;
  }

  .brand-name {
    font-size: 26px;
  }

  .logo-icon {
    width: 60px;
    height: 60px;
  }
}
</style>
