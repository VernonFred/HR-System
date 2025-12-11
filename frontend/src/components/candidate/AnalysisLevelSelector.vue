<script setup lang="ts">
import { ref, computed } from 'vue';

export interface AnalysisLevel {
  key: 'pro' | 'expert';  // V5: 只保留 pro 和 expert
  name: string;
  description: string;
  icon: string;
  warning?: string;
}

const props = withDefaults(defineProps<{
  modelValue?: 'pro' | 'expert';  // V5: 默认为 pro
  disabled?: boolean;
}>(), {
  modelValue: 'pro',  // Pro(32B) 为默认
});

const emit = defineEmits<{
  'update:modelValue': [value: 'pro' | 'expert'];
  'confirm-change': [level: 'pro' | 'expert'];
}>();

// 分析级别配置 - V5: 深度分析为默认，只显示两个按钮
const levels: AnalysisLevel[] = [
  {
    key: 'pro',
    name: '深度分析',
    description: '交叉分析测评数据与简历内容，生成详细画像',
    icon: 'ri-bar-chart-grouped-line',
    // 深度分析是默认级别，不需要警告
  },
  {
    key: 'expert',
    name: '专家分析',
    description: '专家级推理分析，包含发展潜力与团队配置建议',
    icon: 'ri-brain-line',
    warning: '将进行更深入的推理分析，生成时间较长',
  },
];

// 确认弹窗状态
const showConfirmModal = ref(false);
const pendingLevel = ref<'pro' | 'expert' | null>(null);

const currentLevel = computed(() => {
  return levels.find(l => l.key === props.modelValue) || levels[0];
});

const handleSelect = (level: AnalysisLevel) => {
  if (props.disabled) return;
  
  // 如果选择的是当前级别，不做任何操作
  if (level.key === props.modelValue) return;
  
  // 如果有警告（Pro/Expert），显示确认弹窗
  if (level.warning) {
    pendingLevel.value = level.key;
    showConfirmModal.value = true;
  } else {
    emit('update:modelValue', level.key);
    emit('confirm-change', level.key);
  }
};

const confirmChange = () => {
  if (pendingLevel.value) {
    emit('update:modelValue', pendingLevel.value);
    emit('confirm-change', pendingLevel.value);
  }
  showConfirmModal.value = false;
  pendingLevel.value = null;
};

const cancelChange = () => {
  showConfirmModal.value = false;
  pendingLevel.value = null;
};

const pendingLevelInfo = computed(() => {
  return levels.find(l => l.key === pendingLevel.value);
});
</script>

<template>
  <div class="analysis-level-selector">
    <!-- 级别选择按钮组 -->
    <div class="level-buttons">
      <button
        v-for="level in levels"
        :key="level.key"
        :class="['level-btn', { active: modelValue === level.key, disabled }]"
        @click="handleSelect(level)"
        :disabled="disabled"
      >
        <i :class="level.icon"></i>
        <span>{{ level.name }}</span>
      </button>
    </div>
    
    <!-- 当前级别描述 -->
    <div class="level-description">
      <i :class="currentLevel.icon"></i>
      <span>{{ currentLevel.description }}</span>
    </div>
  </div>
  
  <!-- 确认弹窗 -->
  <Teleport to="body">
    <Transition name="modal">
      <div v-if="showConfirmModal" class="confirm-overlay" @click.self="cancelChange">
        <div class="confirm-modal">
          <div class="modal-icon warning">
            <i class="ri-error-warning-line"></i>
          </div>
          <h3>切换到「{{ pendingLevelInfo?.name }}」</h3>
          <p class="warning-text">{{ pendingLevelInfo?.warning }}</p>
          <p class="confirm-text">确定要继续吗？</p>
          <div class="modal-actions">
            <button class="btn-cancel" @click="cancelChange">取消</button>
            <button class="btn-confirm" @click="confirmChange">确定切换</button>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.analysis-level-selector {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.level-buttons {
  display: flex;
  gap: 8px;
  background: var(--bg-secondary, #f5f7fa);
  padding: 4px;
  border-radius: 12px;
}

.level-btn {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 10px 16px;
  border: none;
  border-radius: 10px;
  background: transparent;
  color: var(--text-secondary, #666);
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
}

.level-btn i {
  font-size: 16px;
}

.level-btn:hover:not(.disabled):not(.active) {
  background: rgba(99, 102, 241, 0.08);
  color: var(--primary, #6366f1);
}

.level-btn.active {
  background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);
  color: white;
  box-shadow: 0 4px 12px rgba(99, 102, 241, 0.3);
}

.level-btn.disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.level-description {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 14px;
  background: var(--bg-secondary, #f5f7fa);
  border-radius: 8px;
  font-size: 13px;
  color: var(--text-secondary, #666);
}

.level-description i {
  color: var(--primary, #6366f1);
  font-size: 16px;
}

/* 确认弹窗样式 */
.confirm-overlay {
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

.confirm-modal {
  background: white;
  border-radius: 20px;
  padding: 32px;
  max-width: 420px;
  width: 90%;
  text-align: center;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.2);
}

.modal-icon {
  width: 64px;
  height: 64px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto 20px;
  font-size: 32px;
}

.modal-icon.warning {
  background: linear-gradient(135deg, #fef3c7 0%, #fde68a 100%);
  color: #d97706;
}

.confirm-modal h3 {
  font-size: 20px;
  font-weight: 600;
  color: var(--text-primary, #1a1a2e);
  margin-bottom: 12px;
}

.warning-text {
  font-size: 14px;
  color: var(--text-secondary, #666);
  line-height: 1.6;
  margin-bottom: 8px;
  padding: 12px 16px;
  background: #fef3c7;
  border-radius: 8px;
  border-left: 3px solid #d97706;
}

.confirm-text {
  font-size: 14px;
  color: var(--text-secondary, #666);
  margin-bottom: 24px;
}

.modal-actions {
  display: flex;
  gap: 12px;
  justify-content: center;
}

.btn-cancel,
.btn-confirm {
  padding: 12px 28px;
  border-radius: 10px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
}

.btn-cancel {
  background: var(--bg-secondary, #f5f7fa);
  border: 1px solid var(--border, #e5e7eb);
  color: var(--text-secondary, #666);
}

.btn-cancel:hover {
  background: #e5e7eb;
}

.btn-confirm {
  background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);
  border: none;
  color: white;
  box-shadow: 0 4px 12px rgba(99, 102, 241, 0.3);
}

.btn-confirm:hover {
  transform: translateY(-1px);
  box-shadow: 0 6px 16px rgba(99, 102, 241, 0.4);
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

.modal-enter-from .confirm-modal,
.modal-leave-to .confirm-modal {
  transform: scale(0.9) translateY(20px);
}
</style>

