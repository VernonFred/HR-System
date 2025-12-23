<script setup lang="ts">
import { ref } from "vue";
import { useRouter } from "vue-router";
import { useAuthStore } from "../stores/auth";

// 扩展页面类型
export type PageKey =
  | "candidates"
  | "jobprofiles"
  | "assessments"
  | "questionnaire-center"
  | "users"
  | "settings";

// 导航分组类型
interface NavGroup {
  key: string;
  label: string;
  icon: string;
  children: NavItem[];
}

interface NavItem {
  key: PageKey;
  label: string;
  icon: string;
  path: string;
}

const props = defineProps<{
  active: PageKey;
}>();

const router = useRouter();
const authStore = useAuthStore();

// 展开状态
const expandedGroups = ref<Set<string>>(new Set(["portrait", "survey"]));

// 退出登录确认
const showLogoutConfirm = ref(false);

// 退出登录
const handleLogout = () => {
  showLogoutConfirm.value = true;
};

const confirmLogout = () => {
  authStore.clear();
  window.location.href = "/login";
};

const cancelLogout = () => {
  showLogoutConfirm.value = false;
};

// 导航分组配置（仅画像中心有子菜单）
const navGroups: NavGroup[] = [
  {
    key: "portrait",
    label: "画像中心",
    icon: "ri-user-search-line",
    children: [
      { key: "candidates", label: "候选人画像", icon: "ri-team-line", path: "/candidates" },
      { key: "jobprofiles", label: "岗位画像配置", icon: "ri-briefcase-4-line", path: "/jobprofiles" },
      { key: "assessments", label: "专业测评", icon: "ri-file-list-3-line", path: "/assessments" },
    ],
  },
];

// 独立菜单项（问卷中心改为单一入口）
const standaloneItems: NavItem[] = [
  { key: "questionnaire-center", label: "问卷中心", icon: "ri-questionnaire-line", path: "/questionnaire-center" },
  { key: "users", label: "人员管理", icon: "ri-group-2-line", path: "/users" },
  { key: "settings", label: "系统设置", icon: "ri-settings-3-line", path: "/settings" },
];

// 切换分组展开
const toggleGroup = (groupKey: string) => {
  if (expandedGroups.value.has(groupKey)) {
    expandedGroups.value.delete(groupKey);
  } else {
    expandedGroups.value.add(groupKey);
  }
};

// 判断分组是否展开
const isGroupExpanded = (groupKey: string) => expandedGroups.value.has(groupKey);

// 判断分组是否有激活项
const isGroupActive = (group: NavGroup) => {
  return group.children.some(item => item.key === props.active);
};

// 点击导航项
const handleClick = (item: NavItem) => {
  router.push(item.path);
};
</script>

<template>
  <aside class="sidebar">
    <div class="sidebar-header">
      <div class="logo-dot"></div>
      <div class="logo-title">QZ·TalentLens</div>
    </div>
    
    <nav class="nav-list">
      <!-- 分组导航 -->
      <div v-for="group in navGroups" :key="group.key" class="nav-group">
        <button 
          class="nav-group-header"
          :class="{ expanded: isGroupExpanded(group.key), 'has-active': isGroupActive(group) }"
          @click="toggleGroup(group.key)"
        >
          <i :class="group.icon"></i>
          <span>{{ group.label }}</span>
          <i class="expand-icon ri-arrow-down-s-line" :class="{ rotated: isGroupExpanded(group.key) }"></i>
        </button>
        
        <transition name="slide">
          <div v-show="isGroupExpanded(group.key)" class="nav-group-children">
            <button
              v-for="item in group.children"
              :key="item.key"
              class="nav-item"
              :class="{ active: props.active === item.key }"
              @click="handleClick(item)"
            >
              <i :class="item.icon"></i>
              <span>{{ item.label }}</span>
            </button>
          </div>
        </transition>
      </div>

      <!-- 分隔线 -->
      <div class="nav-divider"></div>
      
      <!-- 独立菜单项 -->
      <button
        v-for="item in standaloneItems"
        :key="item.key"
        class="nav-item standalone"
        :class="{ active: props.active === item.key }"
        @click="handleClick(item)"
      >
        <i :class="item.icon"></i>
        <span>{{ item.label }}</span>
      </button>
    </nav>
    
    <div class="sidebar-footer">
      <div class="user-card">
        <div class="user-avatar">{{ authStore.userInitial }}</div>
        <div class="user-info">
          <div class="user-name">{{ authStore.username }}</div>
          <div class="user-role">
            <span class="online-dot"></span>
            在线
          </div>
        </div>
      </div>
      <button class="logout-btn" @click="handleLogout">
        <i class="ri-logout-circle-r-line"></i>
        退出登录
      </button>
    </div>
    
    <!-- 退出登录确认弹窗 -->
    <Teleport to="body">
      <transition name="fade">
        <div v-if="showLogoutConfirm" class="logout-overlay" @click.self="cancelLogout">
          <div class="logout-modal">
            <div class="modal-icon">
              <i class="ri-logout-circle-r-line"></i>
            </div>
            <h3>确认退出登录？</h3>
            <p>退出后需要重新登录才能访问系统</p>
            <div class="modal-actions">
              <button class="btn-cancel" @click="cancelLogout">取消</button>
              <button class="btn-confirm" @click="confirmLogout">确认退出</button>
            </div>
          </div>
        </div>
      </transition>
    </Teleport>
  </aside>
</template>

<style scoped>
.sidebar {
  background: var(--bg-subtle);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-lg);
  padding: var(--space-4);
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
  min-width: 220px;
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
  gap: 4px;
}

/* 导航分组 */
.nav-group {
  display: flex;
  flex-direction: column;
}

.nav-group-header {
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
  transition: all var(--transition-base);
  font-weight: 500;
}

.nav-group-header:hover {
  background: rgba(99, 102, 241, 0.04);
  color: var(--text-primary);
}

.nav-group-header.expanded {
  color: var(--text-primary);
}

.nav-group-header.has-active {
  color: var(--primary);
}

.nav-group-header i:first-child {
  font-size: 18px;
}

.nav-group-header .expand-icon {
  margin-left: auto;
  font-size: 16px;
  transition: transform 0.2s ease;
}

.nav-group-header .expand-icon.rotated {
  transform: rotate(180deg);
}

.nav-group-children {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding-left: 12px;
  margin-top: 4px;
  overflow: hidden;
}

/* 子项展开动画 */
.slide-enter-active,
.slide-leave-active {
  transition: all 0.2s ease;
}

.slide-enter-from,
.slide-leave-to {
  opacity: 0;
  transform: translateY(-8px);
}

/* 导航项 */
.nav-item {
  width: 100%;
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: 8px 12px;
  border-radius: var(--radius-md);
  border: 1px solid transparent;
  background: transparent;
  color: var(--text-tertiary);
  cursor: pointer;
  transition: all var(--transition-base);
  font-size: 14px;
}

.nav-item:hover {
  background: rgba(99, 102, 241, 0.04);
  color: var(--text-secondary);
}

.nav-item i {
  font-size: 16px;
}

.nav-item.active {
  background: rgba(99, 102, 241, 0.1);
  border-color: rgba(99, 102, 241, 0.2);
  color: var(--primary);
  font-weight: 500;
}

.nav-item.standalone {
  padding: 10px 12px;
  color: var(--text-secondary);
}

.nav-item.standalone i {
  font-size: 18px;
}

/* 分隔线 */
.nav-divider {
  height: 1px;
  background: var(--border-default);
  margin: 8px 0;
}

.sidebar-footer {
  margin-top: auto;
  display: grid;
  gap: var(--space-2);
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
  color: white;
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
  display: flex;
  align-items: center;
  gap: 4px;
  color: var(--text-tertiary);
  font-size: var(--text-sm);
}

.online-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #22c55e;
  animation: pulse 2s infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

.logout-btn {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 10px;
  border-radius: var(--radius-md);
  border: 1px solid #fecaca;
  background: #fef2f2;
  color: #dc2626;
  cursor: pointer;
  font-size: 13px;
  font-weight: 500;
  transition: all 0.2s;
}

.logout-btn:hover {
  background: #fee2e2;
  border-color: #fca5a5;
}

.logout-btn i {
  font-size: 16px;
}

/* 退出登录确认弹窗 */
.logout-overlay {
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

.logout-modal {
  background: white;
  border-radius: 16px;
  padding: 2rem;
  max-width: 360px;
  width: 90%;
  text-align: center;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.2);
}

.logout-modal .modal-icon {
  width: 64px;
  height: 64px;
  border-radius: 50%;
  background: linear-gradient(135deg, #fef2f2 0%, #fee2e2 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto 1rem;
  font-size: 1.75rem;
  color: #dc2626;
}

.logout-modal h3 {
  font-size: 1.25rem;
  font-weight: 600;
  color: #1f2937;
  margin: 0 0 0.5rem;
}

.logout-modal p {
  font-size: 0.875rem;
  color: #6b7280;
  margin: 0 0 1.5rem;
}

.modal-actions {
  display: flex;
  gap: 0.75rem;
}

.modal-actions button {
  flex: 1;
  padding: 0.75rem;
  border-radius: 10px;
  font-size: 0.9375rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-cancel {
  background: #f3f4f6;
  border: none;
  color: #6b7280;
}

.btn-cancel:hover {
  background: #e5e7eb;
}

.btn-confirm {
  background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%);
  border: none;
  color: white;
}

.btn-confirm:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(239, 68, 68, 0.3);
}

/* 弹窗动画 */
.fade-enter-active,
.fade-leave-active {
  transition: all 0.3s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

.fade-enter-from .logout-modal,
.fade-leave-to .logout-modal {
  transform: scale(0.95);
}

@media (max-width: 960px) {
  .sidebar {
    flex-direction: row;
    align-items: center;
    justify-content: space-between;
    min-width: unset;
  }
  .nav-list {
    flex-direction: row;
    flex-wrap: wrap;
  }
  .nav-group {
    flex-direction: row;
  }
  .nav-group-children {
    padding-left: 0;
    flex-direction: row;
  }
}
</style>
