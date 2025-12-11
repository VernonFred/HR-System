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

// ⭐ Token 管理
const tokenStatus = ref<{
  available: boolean;
  expires: string | null;
  days_remaining: number | null;
  warning: string | null;
} | null>(null);
const tokenLoading = ref(false);
const newToken = ref("");
const newTokenExpires = ref("");  // 新增：Token 过期时间
const showTokenInput = ref(false);
const tokenSaving = ref(false);
const tokenUpdateSuccess = ref(false);
const tokenUpdateError = ref("");

// Token 状态样式
const tokenStatusClass = computed(() => {
  if (!tokenStatus.value) return '';
  if (!tokenStatus.value.available) return 'error';
  if (tokenStatus.value.days_remaining !== null && tokenStatus.value.days_remaining < 7) return 'warning';
  return 'success';
});

// 加载 Token 状态 - V45: 使用统一的 API 客户端（支持自动刷新 Token）
const loadTokenStatus = async () => {
  tokenLoading.value = true;
  try {
    const data = await apiRequest<any>({
      path: '/api/ai/router-status',
      auth: true,
    });
      tokenStatus.value = data.api_key_status;
  } catch (error) {
    console.error('加载Token状态失败:', error);
  } finally {
    tokenLoading.value = false;
  }
};

// ⭐ 真正的 Token 更新 - V45: 使用统一的 API 客户端
const updateToken = async () => {
  if (!newToken.value.trim()) {
    tokenUpdateError.value = "请输入新的 Token";
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
        expires: newTokenExpires.value.trim() || undefined,
      },
      auth: true,
    });
    
    tokenUpdateSuccess.value = true;
    showTokenInput.value = false;
    newToken.value = "";
    newTokenExpires.value = "";
    
      // 刷新Token状态
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
            <p>管理 ModelScope API Token</p>
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
                      {{ tokenStatus.available ? 'Token 状态正常' : 'Token 未配置或已失效' }}
              </div>
                    <div v-if="tokenStatus.days_remaining !== null" class="status-card-meta">
                      <i class="ri-calendar-line"></i>
                      剩余有效期：{{ tokenStatus.days_remaining }} 天
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

                <div class="form-container">
            <div class="form-group">
                    <label class="form-label">
                      <i class="ri-key-2-line"></i>
                      API Token
                    </label>
                    <div class="input-wrapper">
              <input
                v-model="newToken"
                type="text"
                        class="form-input"
                        placeholder="请输入 ModelScope API Token"
              />
                    </div>
                    <p class="form-hint">
                      <i class="ri-information-line"></i>
                      从 ModelScope 控制台获取
                    </p>
            </div>
            
            <div class="form-group" style="margin-top: 20px;">
                    <label class="form-label">
                      <i class="ri-calendar-line"></i>
                      Token 过期时间
                    </label>
                    <div class="input-wrapper">
              <input
                v-model="newTokenExpires"
                type="date"
                        class="form-input"
                        placeholder="YYYY-MM-DD"
              />
                    </div>
                    <p class="form-hint">
                      <i class="ri-information-line"></i>
                      请填写 ModelScope 显示的 Token 有效期
                    </p>
            </div>
            
                  <div v-if="tokenUpdateError" class="alert alert-error">
              <i class="ri-error-warning-fill"></i>
              {{ tokenUpdateError }}
            </div>
            
                  <div v-if="tokenUpdateSuccess" class="alert alert-success">
            <i class="ri-checkbox-circle-fill"></i>
            Token 更新成功
          </div>

                  <div class="form-actions">
                    <button class="btn-primary" :disabled="tokenSaving || !newToken.trim()" @click="updateToken">
                      <i :class="tokenSaving ? 'ri-loader-4-line spin' : 'ri-save-line'"></i>
                      {{ tokenSaving ? '保存中...' : '保存 Token' }}
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
.settings-page {
  min-height: 100vh;
  background: transparent;
}

/* 顶部区域 */
.settings-header {
  background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 50%, #a855f7 100%);
  padding: 2.5rem 2rem 4rem;
  position: relative;
}

.header-content {
  max-width: 1200px;
  margin: 0 auto;
  position: relative;
  z-index: 1;
}

.header-brand {
  display: flex;
  align-items: center;
  gap: 1.25rem;
}

.brand-badge {
  background: rgba(255, 255, 255, 0.2);
  backdrop-filter: blur(10px);
  padding: 0.75rem 1.25rem;
  border-radius: 14px;
  border: 1px solid rgba(255, 255, 255, 0.3);
}

.brand-text {
  font-size: 1.25rem;
  font-weight: 800;
  color: white;
  letter-spacing: -0.02em;
}

.brand-dot {
  color: #fbbf24;
}

.header-title h1 {
  margin: 0;
  font-size: 1.625rem;
  font-weight: 700;
  color: white;
}

.header-title p {
  margin: 0.25rem 0 0;
  font-size: 0.9375rem;
  color: rgba(255, 255, 255, 0.85);
}

.header-wave {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  height: 60px;
  overflow: hidden;
}

.header-wave svg {
  width: 100%;
  height: 100%;
}

/* 主内容区 */
.settings-main {
  max-width: 1200px;
  margin: -2rem auto 0;
  padding: 0 2rem 3rem;
  display: grid;
  grid-template-columns: 300px 1fr;
  gap: 1.5rem;
  position: relative;
  z-index: 2;
}

@media (max-width: 900px) {
  .settings-main {
    grid-template-columns: 1fr;
  }
}

/* 用户卡片 */
.user-card {
  background: white;
  border-radius: 16px;
  padding: 1.5rem;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.05);
  height: fit-content;
  position: sticky;
  top: 2rem;
}

.user-card-header {
  text-align: center;
  padding-bottom: 1.25rem;
  border-bottom: 1px solid #f1f5f9;
  margin-bottom: 1.25rem;
}

/* 用户名编辑区域 */
.username-section {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  margin-bottom: 0.5rem;
}

.username-section h2 {
  margin: 0;
  font-size: 1.125rem;
  font-weight: 600;
  color: #1e293b;
}

.edit-username-btn {
  width: 28px;
  height: 28px;
  border-radius: 6px;
  border: none;
  background: #f1f5f9;
  color: #94a3b8;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
}

.edit-username-btn:hover {
  background: #e2e8f0;
  color: #6366f1;
}

.username-edit-form {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.username-input {
  width: 140px;
  padding: 0.5rem 0.75rem;
  border: 2px solid #e2e8f0;
  border-radius: 8px;
  font-size: 0.9375rem;
  color: #1e293b;
  text-align: center;
  transition: all 0.2s;
}

.username-input:focus {
  outline: none;
  border-color: #6366f1;
  box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.1);
}

.username-edit-actions {
  display: flex;
  gap: 0.25rem;
}

.username-edit-actions button {
  width: 28px;
  height: 28px;
  border-radius: 6px;
  border: none;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
}

.username-edit-actions .save-btn {
  background: #10b981;
  color: white;
}

.username-edit-actions .save-btn:hover:not(:disabled) {
  background: #059669;
}

.username-edit-actions .save-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.username-edit-actions .cancel-btn {
  background: #f1f5f9;
  color: #64748b;
}

.username-edit-actions .cancel-btn:hover {
  background: #e2e8f0;
}

.username-error {
  margin-top: 0.375rem;
  font-size: 0.75rem;
  color: #dc2626;
}

.username-success {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.25rem;
  margin-bottom: 0.5rem;
  font-size: 0.75rem;
  color: #10b981;
  font-weight: 500;
}

.user-avatar-large {
  width: 72px;
  height: 72px;
  margin: 0 auto 0.875rem;
  background: linear-gradient(135deg, #6366f1 0%, #a855f7 100%);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.75rem;
  font-weight: 700;
  color: white;
  box-shadow: 0 8px 20px rgba(99, 102, 241, 0.3);
}

.user-card-header h2 {
  margin: 0 0 0.5rem;
  font-size: 1.125rem;
  font-weight: 600;
  color: #1e293b;
}

.user-badges {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.75rem;
  margin-top: 0.75rem;
}

.user-role-badge {
  display: inline-flex;
  align-items: center;
  gap: 0.375rem;
  padding: 0.25rem 0.75rem;
  background: #f0e6ff;
  border-radius: 20px;
  font-size: 0.75rem;
  color: #7c3aed;
  font-weight: 500;
}

.online-indicator {
  display: inline-flex;
  align-items: center;
  gap: 0.375rem;
  font-size: 0.75rem;
  color: #10b981;
  font-weight: 500;
}

.pulse {
  width: 6px;
  height: 6px;
  background: #10b981;
  border-radius: 50%;
  animation: pulse 2s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.5; transform: scale(1.3); }
}

.user-stats {
  margin-bottom: 1.25rem;
}

.stat-item {
  display: flex;
  align-items: center;
  gap: 0.625rem;
  padding: 0.75rem;
  background: #f8fafc;
  border-radius: 10px;
}

.stat-item > i {
  font-size: 1.125rem;
  color: #94a3b8;
}

.stat-item > div {
  display: flex;
  flex-direction: column;
}

.stat-label {
  font-size: 0.6875rem;
  color: #94a3b8;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.stat-value {
  font-size: 0.8125rem;
  color: #475569;
  font-weight: 500;
}

.btn-logout {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  padding: 0.75rem;
  background: #fef2f2;
  border: none;
  border-radius: 10px;
  color: #dc2626;
  font-size: 0.875rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-logout:hover {
  background: #fee2e2;
}

/* 设置选项卡片 */
.settings-options {
  display: flex;
  flex-direction: column;
  gap: 0.875rem;
}

.option-card {
  background: white;
  border-radius: 16px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.04);
  overflow: hidden;
  transition: all 0.3s ease;
  border: 1px solid transparent;
}

.option-card.expanded {
  box-shadow: 0 8px 30px rgba(99, 102, 241, 0.12);
  border-color: rgba(99, 102, 241, 0.1);
}

.option-header {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 1.25rem;
  cursor: pointer;
  transition: background 0.2s;
}

.option-header:hover {
  background: #fafafa;
}

.option-icon {
  width: 48px;
  height: 48px;
  border-radius: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.375rem;
  color: white;
  flex-shrink: 0;
}

.option-icon.blue { background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%); }
.option-icon.orange { background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%); }
.option-icon.purple { background: linear-gradient(135deg, #8b5cf6 0%, #7c3aed 100%); }

.option-info {
  flex: 1;
}

.option-info h3 {
  margin: 0;
  font-size: 1rem;
  font-weight: 600;
  color: #1e293b;
}

.option-info p {
  margin: 0.25rem 0 0;
  font-size: 0.8125rem;
  color: #94a3b8;
}

/* 状态徽章 */
.status-badge {
  display: inline-flex;
  align-items: center;
  gap: 0.375rem;
  padding: 0.375rem 0.75rem;
  border-radius: 20px;
  font-size: 0.75rem;
  font-weight: 600;
}

.status-badge .status-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
}

.status-badge.success { background: #ecfdf5; color: #059669; }
.status-badge.success .status-dot { background: #10b981; }
.status-badge.warning { background: #fffbeb; color: #d97706; }
.status-badge.warning .status-dot { background: #f59e0b; }
.status-badge.error { background: #fef2f2; color: #dc2626; }
.status-badge.error .status-dot { background: #ef4444; }

.toggle-arrow {
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 10px;
  background: #f1f5f9;
  color: #64748b;
  transition: all 0.3s ease;
  font-size: 1.125rem;
}

.toggle-arrow.rotated {
  background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);
  color: white;
  transform: rotate(180deg);
}

.option-content {
  padding: 0 1.25rem 1.5rem;
  background: transparent;
}

/* 表单容器 - 移除白色方块背景 */
.form-container {
  background: transparent;
  padding: 0.5rem 0;
}

.form-grid {
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.form-label {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.875rem;
  font-weight: 600;
  color: #475569;
}

.form-label i {
  font-size: 1rem;
  color: #6366f1;
}

.input-wrapper {
  position: relative;
  display: flex;
  align-items: center;
}

.form-input {
  width: 100%;
  padding: 0.875rem 1rem;
  background: white;
  border: 2px solid #e2e8f0;
  border-radius: 10px;
  font-size: 0.9375rem;
  color: #1e293b;
  transition: all 0.2s;
}

.form-input:focus {
  outline: none;
  border-color: #6366f1;
  box-shadow: 0 0 0 4px rgba(99, 102, 241, 0.1);
}

.form-input::placeholder {
  color: #94a3b8;
}

.input-action {
  position: absolute;
  right: 0.75rem;
  padding: 0.5rem;
  background: transparent;
  border: none;
  color: #94a3b8;
  cursor: pointer;
  border-radius: 6px;
  transition: all 0.2s;
}

.input-action:hover {
  color: #6366f1;
  background: #f1f5f9;
}

.form-hint {
  display: flex;
  align-items: center;
  gap: 0.375rem;
  margin: 0;
  font-size: 0.75rem;
  color: #94a3b8;
}

.form-hint i {
  font-size: 0.875rem;
}

/* 提示框 */
.alert {
  display: flex;
  align-items: center;
  gap: 0.625rem;
  padding: 0.875rem 1rem;
  border-radius: 10px;
  font-size: 0.875rem;
  font-weight: 500;
  margin-top: 1rem;
}

.alert-error {
  background: linear-gradient(135deg, #fef2f2 0%, #fee2e2 100%);
  color: #dc2626;
  border: 1px solid #fecaca;
}

.alert-success {
  background: linear-gradient(135deg, #f0fdf4 0%, #dcfce7 100%);
  color: #16a34a;
  border: 1px solid #bbf7d0;
}

/* 按钮 */
.form-actions {
  display: flex;
  gap: 0.75rem;
  margin-top: 1.25rem;
}

.btn-primary {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  padding: 0.875rem 1.5rem;
  background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);
  color: white;
  border: none;
  border-radius: 10px;
  font-size: 0.9375rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
  box-shadow: 0 4px 12px rgba(99, 102, 241, 0.25);
}

.btn-primary:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 8px 20px rgba(99, 102, 241, 0.35);
}

.btn-primary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
  transform: none;
}

.btn-secondary {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  padding: 0.875rem 1.5rem;
  background: white;
  border: 2px solid #e2e8f0;
  border-radius: 10px;
  font-size: 0.9375rem;
  font-weight: 500;
  color: #64748b;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-secondary:hover {
  background: #f8fafc;
  border-color: #cbd5e1;
  color: #475569;
  }

/* Token 状态卡片 */
.loading-state {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.75rem;
  padding: 2.5rem;
  color: #64748b;
}

.status-card {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 1.25rem;
  border-radius: 14px;
  margin-bottom: 1.25rem;
  position: relative;
  overflow: hidden;
}

.status-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  width: 4px;
  height: 100%;
}

.status-card.success { 
  background: linear-gradient(135deg, #f0fdf4 0%, #dcfce7 100%);
  border: 1px solid #bbf7d0;
}
.status-card.success::before { background: #10b981; }

.status-card.warning { 
  background: linear-gradient(135deg, #fffbeb 0%, #fef3c7 100%);
  border: 1px solid #fde68a;
}
.status-card.warning::before { background: #f59e0b; }

.status-card.error { 
  background: linear-gradient(135deg, #fef2f2 0%, #fee2e2 100%);
  border: 1px solid #fecaca;
}
.status-card.error::before { background: #ef4444; }

.status-card-icon {
  width: 44px;
  height: 44px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.375rem;
}

.status-card.success .status-card-icon { background: #dcfce7; color: #16a34a; }
.status-card.warning .status-card-icon { background: #fef3c7; color: #d97706; }
.status-card.error .status-card-icon { background: #fee2e2; color: #dc2626; }

.status-card-content {
  flex: 1;
}

.status-card-title {
  display: block;
  font-size: 0.9375rem;
  font-weight: 600;
  color: #1e293b;
}

.status-card-meta {
  display: flex;
  align-items: center;
  gap: 0.375rem;
  font-size: 0.8125rem;
  color: #64748b;
  margin-top: 0.25rem;
}

.status-card-meta i {
  font-size: 0.875rem;
}

.status-card-badge {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(16, 185, 129, 0.15);
  color: #10b981;
  font-size: 1.125rem;
}

.warning-banner {
  display: flex;
  align-items: center;
  gap: 0.625rem;
  padding: 1rem;
  background: linear-gradient(135deg, #fffbeb 0%, #fef3c7 100%);
  border: 1px solid #fde68a;
  border-radius: 12px;
  font-size: 0.875rem;
  font-weight: 500;
  color: #d97706;
  margin-bottom: 1.25rem;
}

.warning-banner i {
  font-size: 1.125rem;
}

/* 关于系统 - 信息网格 */
.info-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 0.875rem;
  margin-bottom: 1.25rem;
}

.info-card {
  display: flex;
  align-items: center;
  gap: 0.875rem;
  padding: 1rem;
  background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%);
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  transition: all 0.2s;
}

.info-card:hover {
  border-color: #cbd5e1;
  transform: translateY(-1px);
}

.info-card-icon {
  width: 40px;
  height: 40px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);
  color: white;
  font-size: 1.125rem;
}

.info-card-content {
  display: flex;
  flex-direction: column;
}

.info-label {
  font-size: 0.6875rem;
  color: #94a3b8;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  font-weight: 500;
}

.info-value {
  font-size: 0.9375rem;
  font-weight: 600;
  color: #1e293b;
  margin-top: 0.125rem;
}

/* 品牌展示 */
.brand-showcase {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 1.25rem;
  background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 50%, #a855f7 100%);
  border-radius: 14px;
  position: relative;
  overflow: hidden;
}

.brand-logo {
  width: 56px;
  height: 56px;
  background: rgba(255, 255, 255, 0.2);
  backdrop-filter: blur(10px);
  border-radius: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 1px solid rgba(255, 255, 255, 0.3);
  flex-shrink: 0;
}

.logo-text {
  font-size: 1.25rem;
  font-weight: 800;
  color: white;
}

.logo-dot {
  color: #fbbf24;
}

.brand-info {
  flex: 1;
}

.brand-info h4 {
  margin: 0;
  font-size: 1.125rem;
  font-weight: 700;
  color: white;
}

.brand-info p {
  margin: 0.25rem 0 0;
  font-size: 0.875rem;
  color: rgba(255, 255, 255, 0.85);
}

.brand-decoration {
  position: absolute;
  right: 1.5rem;
  display: flex;
  gap: 0.5rem;
}

.decoration-circle {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.3);
}

.decoration-circle:nth-child(1) {
  animation: float 3s ease-in-out infinite;
}

.decoration-circle:nth-child(2) {
  animation: float 3s ease-in-out infinite 0.5s;
}

.decoration-circle:nth-child(3) {
  animation: float 3s ease-in-out infinite 1s;
}

@keyframes float {
  0%, 100% { transform: translateY(0); opacity: 0.3; }
  50% { transform: translateY(-4px); opacity: 0.6; }
}

/* 退出登录弹窗 */
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.4);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.logout-modal {
  background: white;
  border-radius: 20px;
  padding: 2rem;
  max-width: 360px;
  width: 90%;
  text-align: center;
  box-shadow: 0 25px 60px rgba(0, 0, 0, 0.2);
}

.modal-icon {
  width: 64px;
  height: 64px;
  margin: 0 auto 1.25rem;
  background: linear-gradient(135deg, #fef2f2 0%, #fee2e2 100%);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.75rem;
  color: #dc2626;
}

.logout-modal h3 {
  margin: 0 0 0.5rem;
  font-size: 1.25rem;
  font-weight: 600;
  color: #1e293b;
}

.logout-modal p {
  margin: 0 0 1.5rem;
  font-size: 0.9375rem;
  color: #64748b;
}

.modal-actions {
  display: flex;
  gap: 0.75rem;
}

.cancel-btn {
  flex: 1;
  padding: 0.875rem;
  background: #f1f5f9;
  border: none;
  border-radius: 10px;
  font-size: 0.9375rem;
  font-weight: 500;
  color: #64748b;
  cursor: pointer;
  transition: all 0.2s;
}

.cancel-btn:hover {
  background: #e2e8f0;
}

.confirm-btn {
  flex: 1;
  padding: 0.875rem;
  background: linear-gradient(135deg, #dc2626 0%, #b91c1c 100%);
  border: none;
  border-radius: 10px;
  font-size: 0.9375rem;
  font-weight: 600;
  color: white;
  cursor: pointer;
  transition: all 0.2s;
  box-shadow: 0 4px 12px rgba(220, 38, 38, 0.25);
}

.confirm-btn:hover {
  transform: translateY(-1px);
  box-shadow: 0 6px 16px rgba(220, 38, 38, 0.35);
}

/* 动画 */
@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.spin {
  animation: spin 1s linear infinite;
}

.slide-enter-active,
.slide-leave-active {
  transition: all 0.3s ease;
  overflow: hidden;
}

.slide-enter-from,
.slide-leave-to {
  opacity: 0;
  max-height: 0;
  padding-top: 0;
  padding-bottom: 0;
}

.slide-enter-to,
.slide-leave-from {
  opacity: 1;
  max-height: 600px;
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
