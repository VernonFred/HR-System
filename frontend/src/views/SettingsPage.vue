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

<template>
  <div class="settings-page">
    <!-- 顶部区域 - 简洁现代风格 -->
    <div class="settings-header">
      <div class="header-content">
        <div class="header-brand">
          <div class="brand-badge">
            <span class="brand-text">QZ<span class="brand-dot">·</span>TalentLens</span>
      </div>
          <div class="header-title">
        <h1>系统设置</h1>
            <p>管理账户安全与系统配置</p>
      </div>
    </div>
          </div>
      <div class="header-wave">
        <svg viewBox="0 0 1440 120" preserveAspectRatio="none">
          <path d="M0,64 C480,150 960,-20 1440,64 L1440,120 L0,120 Z" fill="#f8fafc"/>
        </svg>
          </div>
        </div>

    <!-- 主内容区 -->
    <div class="settings-main">
      <!-- 左侧：用户信息卡片 -->
      <div class="user-card">
        <div class="user-card-header">
          <div class="user-avatar-large">
            {{ userInfo.username[0].toUpperCase() }}
            </div>

          <!-- 用户名显示/编辑 -->
          <div class="username-section">
            <template v-if="!isEditingUsername">
              <h2>{{ userInfo.username }}</h2>
              <button class="edit-username-btn" @click="startEditUsername" title="修改用户名">
                <i class="ri-pencil-line"></i>
              </button>
            </template>
            <template v-else>
              <div class="username-edit-form">
                <input
                  v-model="newUsername"
                  type="text"
                  class="username-input"
                  placeholder="输入新用户名"
                  maxlength="50"
                  @keyup.enter="saveUsername"
                  @keyup.escape="cancelEditUsername"
                />
                <div class="username-edit-actions">
                  <button class="save-btn" :disabled="usernameSaving" @click="saveUsername">
                    <i :class="usernameSaving ? 'ri-loader-4-line spin' : 'ri-check-line'"></i>
                  </button>
                  <button class="cancel-btn" @click="cancelEditUsername">
                    <i class="ri-close-line"></i>
                  </button>
            </div>
              </div>
            </template>
          </div>

          <div v-if="usernameUpdateError" class="username-error">
            {{ usernameUpdateError }}
              </div>

          <div v-if="usernameUpdateSuccess" class="username-success">
            <i class="ri-checkbox-circle-fill"></i> 用户名已更新
            </div>

          <div class="user-badges">
            <span class="user-role-badge">
              <i class="ri-shield-star-fill"></i>
              {{ userInfo.role }}
            </span>
            <div class="online-indicator">
              <span class="pulse"></span>
              在线
              </div>
            </div>
        </div>

        <div class="user-stats">
          <div class="stat-item">
            <i class="ri-time-fill"></i>
              <div>
              <span class="stat-label">最后登录</span>
              <span class="stat-value">{{ userInfo.lastLogin }}</span>
              </div>
            </div>
          </div>

        </div>

      <!-- 右侧：设置选项 -->
      <div class="settings-options">
        <!-- 修改密码 -->
        <div class="option-card" :class="{ expanded: activeSection === 'password' }">
          <div class="option-header" @click="toggleSection('password')">
            <div class="option-icon blue">
              <i class="ri-lock-password-fill"></i>
          </div>
            <div class="option-info">
            <h3>修改密码</h3>
              <p>更新登录密码保护账户安全</p>
            </div>
            <div class="toggle-arrow" :class="{ rotated: activeSection === 'password' }">
              <i class="ri-arrow-down-s-line"></i>
          </div>
        </div>

          <transition name="slide">
            <div v-if="activeSection === 'password'" class="option-content">
              <div class="form-container">
                <div class="form-grid">
          <div class="form-group">
                    <label class="form-label">
                      <i class="ri-lock-line"></i>
                      当前密码
                    </label>
                    <div class="input-wrapper">
              <input
                v-model="currentPassword"
                  :type="showCurrentPassword ? 'text' : 'password'"
                        class="form-input"
                placeholder="请输入当前密码"
              />
                      <button type="button" class="input-action" @click="showCurrentPassword = !showCurrentPassword">
                  <i :class="showCurrentPassword ? 'ri-eye-off-line' : 'ri-eye-line'"></i>
              </button>
            </div>
          </div>

          <div class="form-group">
                    <label class="form-label">
                      <i class="ri-lock-2-line"></i>
                      新密码
                    </label>
                    <div class="input-wrapper">
            <input
              v-model="newPassword"
                  :type="showNewPassword ? 'text' : 'password'"
                        class="form-input"
                  placeholder="请输入新密码（至少6位）"
            />
                      <button type="button" class="input-action" @click="showNewPassword = !showNewPassword">
                  <i :class="showNewPassword ? 'ri-eye-off-line' : 'ri-eye-line'"></i>
                </button>
              </div>
          </div>

          <div class="form-group">
                    <label class="form-label">
                      <i class="ri-lock-2-line"></i>
                      确认新密码
                    </label>
                    <div class="input-wrapper">
            <input
              v-model="confirmPassword"
                  :type="showNewPassword ? 'text' : 'password'"
                        class="form-input"
              placeholder="请再次输入新密码"
            />
                    </div>
              </div>
            </div>

                <div v-if="passwordChangeError" class="alert alert-error">
              <i class="ri-error-warning-fill"></i>
              {{ passwordChangeError }}
            </div>

                <div v-if="passwordChangeSuccess" class="alert alert-success">
              <i class="ri-checkbox-circle-fill"></i>
              密码修改成功
          </div>

                <div class="form-actions">
                  <button class="btn-primary" :disabled="saving" @click="changePassword">
                    <i :class="saving ? 'ri-loader-4-line spin' : 'ri-check-line'"></i>
              {{ saving ? '修改中...' : '确认修改' }}
            </button>
          </div>
        </div>
            </div>
          </transition>
      </div>

        <!-- AI 模型配置 -->
        <div class="option-card" :class="{ expanded: activeSection === 'ai' }">
          <div class="option-header" @click="toggleSection('ai')">
            <div class="option-icon orange">
              <i class="ri-robot-fill"></i>
          </div>
            <div class="option-info">
            <h3>AI 模型配置</h3>
            <p>DeepSeek V4 Pro 单模型运行</p>
          </div>
            <div v-if="tokenStatus" class="status-badge" :class="tokenStatusClass">
              <span class="status-dot"></span>
              {{ tokenStatus.available ? '运行中' : '未配置' }}
            </div>
            <div class="toggle-arrow" :class="{ rotated: activeSection === 'ai' }">
              <i class="ri-arrow-down-s-line"></i>
          </div>
        </div>

          <transition name="slide">
            <div v-if="activeSection === 'ai'" class="option-content">
              <div v-if="tokenLoading" class="loading-state">
            <i class="ri-loader-4-line spin"></i>
            <span>加载中...</span>
          </div>

              <template v-else>
                <!-- Token 状态卡片 -->
                <div v-if="tokenStatus" class="status-card" :class="tokenStatusClass">
                  <div class="status-card-icon">
                    <i :class="tokenStatusClass === 'error' ? 'ri-close-circle-fill' :
                           tokenStatusClass === 'warning' ? 'ri-alert-fill' :
                           'ri-checkbox-circle-fill'"></i>
              </div>
                  <div class="status-card-content">
                    <div class="status-card-title">
                      {{ tokenStatus.available ? 'DeepSeek API Key 已配置' : 'DeepSeek API Key 未配置' }}
              </div>
                    <div class="status-card-meta">
                      <i class="ri-cpu-line"></i>
                      当前模型：{{ aiModelInfo.model_id }}
                    </div>
                  </div>
                  <div v-if="tokenStatus.available" class="status-card-badge">
                    <i class="ri-shield-check-fill"></i>
              </div>
            </div>

                <div v-if="tokenStatus?.warning" class="warning-banner">
                  <i class="ri-alarm-warning-fill"></i>
              {{ tokenStatus.warning }}
          </div>

                <div class="ai-model-grid">
                  <div class="ai-model-card primary">
                    <span class="ai-model-label">模型</span>
                    <strong>{{ aiModelInfo.model_id }}</strong>
                    <small>DeepSeek V4 Pro</small>
                  </div>
                  <div class="ai-model-card">
                    <span class="ai-model-label">接口地址</span>
                    <strong>{{ aiModelInfo.api_base }}</strong>
                    <small>OpenAI 兼容格式</small>
                  </div>
                  <div class="ai-model-card">
                    <span class="ai-model-label">运行模式</span>
                    <strong>{{ aiModelInfo.fallback_available ? '多模型' : '单模型' }}</strong>
                    <small>固定 DeepSeek V4 Pro</small>
                  </div>
                  <div class="ai-model-card">
                    <span class="ai-model-label">路由策略</span>
                    <strong>{{ aiModelInfo.routing_strategy }}</strong>
                    <small>画像、报告、岗位分析共用</small>
                  </div>
                </div>

                <div class="form-container">
            <div class="form-group">
                    <label class="form-label">
                      <i class="ri-key-2-line"></i>
                      DeepSeek API Key
                    </label>
                    <div class="input-wrapper">
              <input
                v-model="newToken"
                type="password"
                        class="form-input"
                        placeholder="请输入 DeepSeek API Key"
              />
                    </div>
                    <p class="form-hint">
                      <i class="ri-information-line"></i>
                      API Key 仅用于服务端调用 DeepSeek，不会在前端明文展示
                    </p>
            </div>

                  <div v-if="tokenUpdateError" class="alert alert-error">
              <i class="ri-error-warning-fill"></i>
              {{ tokenUpdateError }}
            </div>

                  <div v-if="tokenUpdateSuccess" class="alert alert-success">
            <i class="ri-checkbox-circle-fill"></i>
            DeepSeek API Key 更新成功
          </div>

                  <div class="form-actions">
                    <button class="btn-primary" :disabled="tokenSaving || !newToken.trim()" @click="updateToken">
                      <i :class="tokenSaving ? 'ri-loader-4-line spin' : 'ri-save-line'"></i>
                      {{ tokenSaving ? '保存中...' : '保存 Key' }}
            </button>
                    <button class="btn-secondary" @click="loadTokenStatus">
                      <i class="ri-refresh-line"></i>
              刷新状态
            </button>
          </div>
        </div>
              </template>
            </div>
          </transition>
      </div>

      <!-- 关于系统 -->
        <div class="option-card" :class="{ expanded: activeSection === 'about' }">
          <div class="option-header" @click="toggleSection('about')">
            <div class="option-icon purple">
              <i class="ri-information-fill"></i>
          </div>
            <div class="option-info">
            <h3>关于系统</h3>
              <p>查看版本和技术信息</p>
            </div>
            <div class="toggle-arrow" :class="{ rotated: activeSection === 'about' }">
              <i class="ri-arrow-down-s-line"></i>
          </div>
        </div>

          <transition name="slide">
            <div v-if="activeSection === 'about'" class="option-content">
              <div class="info-grid">
                <div class="info-card">
                  <div class="info-card-icon">
                    <i class="ri-price-tag-3-fill"></i>
              </div>
                  <div class="info-card-content">
                    <span class="info-label">版本号</span>
                    <span class="info-value">v1.0.0</span>
            </div>
          </div>
                <div class="info-card">
                  <div class="info-card-icon">
                    <i class="ri-calendar-2-fill"></i>
            </div>
                  <div class="info-card-content">
                    <span class="info-label">更新时间</span>
                    <span class="info-value">2025-12-08</span>
          </div>
            </div>
                <div class="info-card">
                  <div class="info-card-icon">
                    <i class="ri-code-box-fill"></i>
                  </div>
                  <div class="info-card-content">
                    <span class="info-label">技术栈</span>
                    <span class="info-value">Vue 3 + FastAPI</span>
                  </div>
                </div>
                <div class="info-card">
                  <div class="info-card-icon">
                    <i class="ri-database-2-fill"></i>
                  </div>
                  <div class="info-card-content">
                    <span class="info-label">数据库</span>
                    <span class="info-value">SQLite / PostgreSQL</span>
          </div>
          </div>
        </div>

              <div class="brand-showcase">
                <div class="brand-logo">
                  <span class="logo-text">QZ<span class="logo-dot">·</span></span>
          </div>
                <div class="brand-info">
                  <h4>QZ·TalentLens</h4>
                  <p>人员初步画像智能工具</p>
        </div>
                <div class="brand-decoration">
                  <div class="decoration-circle"></div>
                  <div class="decoration-circle"></div>
                  <div class="decoration-circle"></div>
      </div>
    </div>
            </div>
          </transition>
        </div>
      </div>
    </div>

    <!-- 退出登录确认弹窗 -->
    <transition name="fade">
      <div v-if="showLogoutConfirm" class="modal-overlay" @click.self="showLogoutConfirm = false">
        <div class="logout-modal">
          <div class="modal-icon">
            <i class="ri-logout-circle-r-line"></i>
          </div>
          <h3>确认退出登录？</h3>
          <p>退出后需要重新登录才能访问系统</p>
          <div class="modal-actions">
            <button class="cancel-btn" @click="showLogoutConfirm = false">取消</button>
            <button class="confirm-btn" @click="confirmLogout">确认退出</button>
          </div>
        </div>
      </div>
    </transition>
  </div>
</template>

<style scoped>
@import './styles/settings-page.css';
</style>
