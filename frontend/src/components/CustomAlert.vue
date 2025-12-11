<script setup lang="ts">
import { ref, watch } from 'vue';

interface Props {
  show: boolean;
  title?: string;
  message: string;
  type?: 'info' | 'warning' | 'error' | 'success';
  confirmText?: string;
  cancelText?: string;
  showCancel?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
  title: '提示',
  type: 'warning',
  confirmText: '确定',
  cancelText: '取消',
  showCancel: false
});

const emit = defineEmits<{
  confirm: [];
  close: [];
}>();

const visible = ref(false);

watch(() => props.show, (newVal) => {
  visible.value = newVal;
});

const handleConfirm = () => {
  visible.value = false;
  emit('confirm');
  emit('close');
};

const handleClose = () => {
  visible.value = false;
  emit('close');
};

const iconMap = {
  info: 'ri-information-line',
  warning: 'ri-error-warning-line',
  error: 'ri-close-circle-line',
  success: 'ri-checkbox-circle-line'
};

const colorMap = {
  info: '#3b82f6',
  warning: '#f59e0b',
  error: '#ef4444',
  success: '#10b981'
};
</script>

<template>
  <Teleport to="body">
    <Transition name="alert-fade">
      <div v-if="visible" class="custom-alert-overlay" @click="handleClose">
        <Transition name="alert-scale">
          <div v-if="visible" class="custom-alert-box" @click.stop>
            <!-- 图标 -->
            <div class="alert-icon" :style="{ background: colorMap[type] + '15', color: colorMap[type] }">
              <i :class="iconMap[type]"></i>
            </div>

            <!-- 标题 -->
            <h3 class="alert-title">{{ title }}</h3>

            <!-- 消息 -->
            <p class="alert-message">{{ message }}</p>

            <!-- 按钮 -->
            <div class="alert-actions">
              <button v-if="showCancel" class="btn-cancel" @click="handleClose">{{ cancelText }}</button>
              <button class="btn-confirm" :style="{ background: colorMap[type] }" @click="handleConfirm">
                {{ confirmText }}
              </button>
            </div>
          </div>
        </Transition>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.custom-alert-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  backdrop-filter: blur(4px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 9999;
  padding: 20px;
}

.custom-alert-box {
  background: white;
  border-radius: 16px;
  padding: 32px 28px;
  max-width: 400px;
  width: 100%;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
  text-align: center;
}

.alert-icon {
  width: 64px;
  height: 64px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto 20px;
  font-size: 32px;
}

.alert-title {
  font-size: 20px;
  font-weight: 600;
  color: #1f2937;
  margin: 0 0 12px;
}

.alert-message {
  font-size: 15px;
  color: #6b7280;
  line-height: 1.6;
  margin: 0 0 24px;
}

.alert-actions {
  display: flex;
  gap: 12px;
}

.btn-confirm {
  flex: 1;
  padding: 12px 24px;
  border: none;
  border-radius: 8px;
  font-size: 15px;
  font-weight: 500;
  color: white;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-confirm:hover {
  opacity: 0.9;
  transform: translateY(-1px);
}

.btn-confirm:active {
  transform: translateY(0);
}

.btn-cancel {
  flex: 1;
  padding: 12px 24px;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  font-size: 15px;
  font-weight: 500;
  color: #6b7280;
  background: white;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-cancel:hover {
  background: #f3f4f6;
}

/* 动画 */
.alert-fade-enter-active,
.alert-fade-leave-active {
  transition: opacity 0.3s;
}

.alert-fade-enter-from,
.alert-fade-leave-to {
  opacity: 0;
}

.alert-scale-enter-active {
  transition: all 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
}

.alert-scale-leave-active {
  transition: all 0.2s;
}

.alert-scale-enter-from {
  opacity: 0;
  transform: scale(0.9) translateY(10px);
}

.alert-scale-leave-to {
  opacity: 0;
  transform: scale(0.95);
}
</style>

