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
@import './styles/login-page.css';
</style>
