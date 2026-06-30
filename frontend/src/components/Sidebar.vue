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
@import './styles/sidebar.css';
</style>
