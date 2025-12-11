<script setup lang="ts">
/**
 * 画像抽屉组件 - 从右侧滑出显示完整AI画像
 * 直接复用 CandidatePortraitCard 组件，保留工具栏
 */
import { watch } from 'vue';
import type { CandidateProfile, AssessmentRecord } from '../../types/candidate';
import CandidatePortraitCard from './CandidatePortraitCard.vue';

const props = defineProps<{
  visible: boolean;
  profile: CandidateProfile | null;
  assessment: AssessmentRecord | null;
  isRefreshing?: boolean;
}>();

const emit = defineEmits<{
  (e: 'close'): void;
  (e: 'portrait-regenerated', level: 'pro' | 'expert', forceRefresh: boolean): void;  // ⭐ V38: 添加 forceRefresh 参数
}>();

// 阻止滚动穿透
watch(() => props.visible, (val) => {
  document.body.style.overflow = val ? 'hidden' : '';
});
</script>

<template>
  <Teleport to="body">
    <Transition name="drawer">
      <div v-if="visible" class="drawer-overlay" @click.self="emit('close')">
        <div class="drawer-container">
          <!-- 抽屉头部：简洁关闭按钮 -->
          <div class="drawer-header">
            <button class="close-btn" @click="emit('close')" title="关闭">
              <i class="ri-close-line"></i>
            </button>
          </div>

          <!-- 抽屉内容 - 直接复用原有的画像组件，保留工具栏 -->
          <div class="drawer-body" :class="{ 'is-refreshing': isRefreshing }">
            <CandidatePortraitCard 
              v-if="profile"
              :profile="profile" 
              :hideAssessmentList="true"
              @portrait-regenerated="(level, forceRefresh) => emit('portrait-regenerated', level, forceRefresh)"
            />
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
/* 遮罩层 */
.drawer-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  backdrop-filter: blur(4px);
  z-index: 1000;
  display: flex;
  justify-content: flex-end;
}

/* 抽屉容器 */
.drawer-container {
  width: 70vw;
  max-width: 1000px;
  min-width: 600px;
  height: 100vh;
  background: #f8fafc;
  display: flex;
  flex-direction: column;
  box-shadow: -8px 0 32px rgba(0, 0, 0, 0.15);
  position: relative;
}

/* 抽屉头部 - 只有关闭按钮 */
.drawer-header {
  position: absolute;
  top: 1rem;
  right: 1rem;
  z-index: 100;
}

.close-btn {
  width: 40px;
  height: 40px;
  border: none;
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.9);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  color: #6b7280;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
}

.close-btn:hover { 
  background: white;
  color: #1f2937;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

.close-btn i { font-size: 1.5rem; }

/* 抽屉内容 */
.drawer-body {
  flex: 1;
  overflow-y: auto;
  overflow-x: hidden;
  transition: all 0.3s ease;
}

/* 画像刷新动画 */
.drawer-body.is-refreshing {
  animation: portraitRefresh 0.8s ease-out;
}

@keyframes portraitRefresh {
  0% {
    opacity: 0.6;
    transform: scale(0.98);
  }
  50% {
    opacity: 1;
    transform: scale(1.01);
    box-shadow: inset 0 0 60px rgba(99, 102, 241, 0.15);
  }
  100% {
    opacity: 1;
    transform: scale(1);
    box-shadow: none;
  }
}

/* 覆盖 CandidatePortraitCard 的一些样式使其适应抽屉 */
.drawer-body :deep(.portrait-card) {
  border-radius: 0;
  box-shadow: none;
  min-height: auto;
}

/* 隐藏测评记录列表 */
.drawer-body :deep(.assessment-list-container) {
  display: none !important;
}

/* 动画 */
.drawer-enter-active,
.drawer-leave-active {
  transition: all 0.35s cubic-bezier(0.4, 0, 0.2, 1);
}

.drawer-enter-active .drawer-container,
.drawer-leave-active .drawer-container {
  transition: transform 0.35s cubic-bezier(0.4, 0, 0.2, 1);
}

.drawer-enter-from,
.drawer-leave-to {
  opacity: 0;
}

.drawer-enter-from .drawer-container,
.drawer-leave-to .drawer-container {
  transform: translateX(100%);
}

/* 滚动条美化 */
.drawer-body::-webkit-scrollbar {
  width: 6px;
}

.drawer-body::-webkit-scrollbar-track {
  background: transparent;
}

.drawer-body::-webkit-scrollbar-thumb {
  background: #d1d5db;
  border-radius: 3px;
}

.drawer-body::-webkit-scrollbar-thumb:hover {
  background: #9ca3af;
}

/* 响应式 */
@media (max-width: 768px) {
  .drawer-container {
    width: 100vw;
    min-width: unset;
  }
}
</style>
