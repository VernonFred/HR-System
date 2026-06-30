<script setup lang="ts">
import { ref, onMounted, computed } from "vue";
import { useAuthStore } from "../stores/auth";
import { apiRequest, apiRequestWithBody } from "../api/client";

const authStore = useAuthStore();

// 账户管理
const currentPassword = ref("");
const newPassword = ref("");
const confirmPassword = ref("");
const showCurrentPassword = ref(false);
const showNewPassword = ref(false);

// 保存状态
const saving = ref(false);
const passwordChangeSuccess = ref(false);
const passwordChangeError = ref("");

// DeepSeek API Key 管理
const tokenStatus = ref<{
  available: boolean;
  expires?: string | null;
  days_remaining?: number | null;
  warning?: string | null;
} | null>(null);
const aiModelInfo = ref<{
  model_id: string;
  api_base: string;
  fallback_available: boolean;
  routing_strategy: string;
}>({
  model_id: "deepseek-v4-pro",
  api_base: "https://api.deepseek.com",
  fallback_available: false,
  routing_strategy: "DeepSeek only",
});
const tokenLoading = ref(false);
const newToken = ref("");
const showTokenInput = ref(false);
const tokenSaving = ref(false);
const tokenUpdateSuccess = ref(false);
const tokenUpdateError = ref("");

// API Key 状态样式
const tokenStatusClass = computed(() => {
  if (!tokenStatus.value) return '';
  if (!tokenStatus.value.available) return 'error';
  if (typeof tokenStatus.value.days_remaining === 'number' && tokenStatus.value.days_remaining < 7) return 'warning';
  return 'success';
});

// 加载 API Key 状态 - 使用统一的 API 客户端
const loadTokenStatus = async () => {
  tokenLoading.value = true;
  try {
    const data = await apiRequest<any>({
      path: '/api/ai/router-status',
      auth: true,
    });
    tokenStatus.value = data.api_key_status || null;
    const model = Array.isArray(data.models) && data.models.length > 0 ? data.models[0] : null;
    aiModelInfo.value = {
      model_id: model?.model_id || "deepseek-v4-pro",
      api_base: model?.api_base || "https://api.deepseek.com",
      fallback_available: Boolean(data.fallback_available),
      routing_strategy: data.routing_strategy || "DeepSeek only",
    };
  } catch (error) {
    console.error('加载 DeepSeek API Key 状态失败:', error);
  } finally {
    tokenLoading.value = false;
  }
};

// 更新 DeepSeek API Key
const updateToken = async () => {
  if (!newToken.value.trim()) {
    tokenUpdateError.value = "请输入 DeepSeek API Key";
    return;
  }

  tokenUpdateError.value = "";
  tokenSaving.value = true;

  try {
    await apiRequestWithBody({
      path: '/api/settings/update-token',
      method: 'POST',
      body: {
        token: newToken.value.trim(),
      },
      auth: true,
    });

    tokenUpdateSuccess.value = true;
    showTokenInput.value = false;
    newToken.value = "";

      // 刷新 API Key 状态
      await loadTokenStatus();

    setTimeout(() => {
      tokenUpdateSuccess.value = false;
    }, 3000);
  } catch (error) {
    tokenUpdateError.value = "网络错误，请稍后重试";
  } finally {
    tokenSaving.value = false;
  }
};

// 获取当前用户信息
const userInfo = ref({
  username: authStore.username || "Admin",
  role: authStore.userRole === 'admin' ? "系统管理员" : "普通用户",
  lastLogin: new Date().toLocaleString('zh-CN'),
});

// 修改用户名
const isEditingUsername = ref(false);
const newUsername = ref("");
const usernameSaving = ref(false);
const usernameUpdateSuccess = ref(false);
const usernameUpdateError = ref("");

const startEditUsername = () => {
  newUsername.value = userInfo.value.username;
  isEditingUsername.value = true;
  usernameUpdateError.value = "";
};

const cancelEditUsername = () => {
  isEditingUsername.value = false;
  newUsername.value = "";
  usernameUpdateError.value = "";
};

// V45: 使用统一的 API 客户端（支持自动刷新 Token）
const saveUsername = async () => {
  if (!newUsername.value.trim()) {
    usernameUpdateError.value = "用户名不能为空";
    return;
  }
  if (newUsername.value.trim() === userInfo.value.username) {
    isEditingUsername.value = false;
    return;
  }

  usernameUpdateError.value = "";
  usernameSaving.value = true;

  try {
    const data = await apiRequestWithBody<{ username: string }>({
      path: '/api/auth/update-username',
      method: 'POST',
      body: {
        new_username: newUsername.value.trim(),
      },
      auth: true,
    });

      userInfo.value.username = data.username;
      // 更新 store 中的用户信息（会自动持久化到 localStorage）
      authStore.setUsername(data.username);
      isEditingUsername.value = false;
      usernameUpdateSuccess.value = true;
      setTimeout(() => {
        usernameUpdateSuccess.value = false;
      }, 3000);
  } catch (error: any) {
    if (error.message?.includes("未登录") || error.message?.includes("过期")) {
      usernameUpdateError.value = "登录已过期，请重新登录";
    } else {
      usernameUpdateError.value = error.message || "用户名修改失败";
    }
  } finally {
    usernameSaving.value = false;
  }
};

onMounted(() => {
  // V45: 检查登录状态
  if (!authStore.isLoggedIn) {
    window.location.href = "/login";
    return;
  }

  // 从 store 获取用户信息
  userInfo.value.username = authStore.username;
  userInfo.value.role = authStore.userRole === 'admin' ? '系统管理员' : '普通用户';
  loadTokenStatus();
});

// V45: 使用统一的 API 客户端（支持自动刷新 Token）
const changePassword = async () => {
  if (!currentPassword.value) {
    passwordChangeError.value = "请输入当前密码";
    return;
  }
  if (!newPassword.value) {
    passwordChangeError.value = "请输入新密码";
    return;
  }
  if (newPassword.value.length < 6) {
    passwordChangeError.value = "新密码长度至少6位";
    return;
  }
  if (!confirmPassword.value) {
    passwordChangeError.value = "请确认新密码";
    return;
  }
  if (newPassword.value !== confirmPassword.value) {
    passwordChangeError.value = "两次输入的密码不一致";
    return;
  }

  passwordChangeError.value = "";
  saving.value = true;

  try {
    await apiRequestWithBody({
      path: '/auth/change-password',
      method: 'POST',
      body: {
        current_password: currentPassword.value,
        new_password: newPassword.value,
      },
      auth: true,
    });

      passwordChangeSuccess.value = true;
    currentPassword.value = "";
    newPassword.value = "";
    confirmPassword.value = "";
      setTimeout(() => {
        passwordChangeSuccess.value = false;
      }, 3000);
  } catch (error: any) {
    if (error.message?.includes("未登录") || error.message?.includes("过期")) {
      passwordChangeError.value = "登录已过期，请重新登录";
    } else {
      passwordChangeError.value = error.message || "密码修改失败，请检查当前密码是否正确";
    }
  } finally {
    saving.value = false;
  }
};

const handleLogout = () => {
  showLogoutConfirm.value = true;
};

// 退出登录确认弹窗
const showLogoutConfirm = ref(false);
const confirmLogout = () => {
    authStore.logout();
    window.location.href = "/login";
};

// 当前活动的设置项
const activeSection = ref<string | null>(null);
const toggleSection = (section: string) => {
  activeSection.value = activeSection.value === section ? null : section;
};
</script>

<template src="./SettingsPage.template.html"></template>

<style scoped>
@import './styles/settings-page.css';
</style>
