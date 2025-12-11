<script setup lang="ts">
import { ref, computed, watch } from 'vue';
import ResumeUpload from './ResumeUpload.vue';
import ResumeDisplay from './ResumeDisplay.vue';

const props = defineProps<{
  visible: boolean;
  candidateId?: number;
  candidateName?: string;
  resumeInfo?: any;
  loading?: boolean;
  isRegeneratingPortrait?: boolean;  // 是否正在重新生成画像
}>();

const emit = defineEmits<{
  close: [];
  uploaded: [data: any];
  error: [error: string];
  download: [];
  delete: [];
  parse: [level: 'pro' | 'expert'];  // 解析简历（带级别），解析完成后自动生成画像
  'parse-complete': [level: 'pro' | 'expert'];  // 解析完成（带级别）
}>();

// 解析状态
const isParsing = ref(false);
const showParseToast = ref(false);
const currentParseLevel = ref<'pro' | 'expert'>('pro');  // 当前解析级别

// 是否有简历
const hasResume = computed(() => {
  return props.resumeInfo?.has_resume || false;
});

// 是否已解析（检查 parsing_status 或 parsed_data）
const isParsed = computed(() => {
  if (!props.resumeInfo) return false;
  // 优先检查 parsing_status
  if (props.resumeInfo.parsing_status === 'completed') return true;
  // 兼容：检查 parsed_data 是否有有效数据
  const parsedData = props.resumeInfo.parsed_data;
  if (parsedData && typeof parsedData === 'object') {
    return Object.keys(parsedData).length > 0;
  }
  return false;
});

// 处理解析（带级别）
const handleParse = (level: 'pro' | 'expert' = 'pro') => {
  isParsing.value = true;
  currentParseLevel.value = level;
  emit('parse', level);
};

// 监听 resumeInfo 变化，检测解析完成
watch(() => props.resumeInfo?.parsing_status, (newStatus, oldStatus) => {
  if (newStatus === 'completed' && oldStatus !== 'completed' && isParsing.value) {
    isParsing.value = false;
    showParseToast.value = true;
    emit('parse-complete', currentParseLevel.value);
    // 3秒后自动隐藏 Toast
    setTimeout(() => {
      showParseToast.value = false;
    }, 3000);
  }
});

// 监听 parsed_data 变化（兼容方案）
watch(() => props.resumeInfo?.parsed_data, (newData) => {
  if (newData && Object.keys(newData).length > 0 && isParsing.value) {
    isParsing.value = false;
    showParseToast.value = true;
    emit('parse-complete', currentParseLevel.value);
    setTimeout(() => {
      showParseToast.value = false;
    }, 3000);
  }
});

const handleClose = () => {
  emit('close');
};

const handleClickOutside = (event: MouseEvent) => {
  const target = event.target as HTMLElement;
  if (target.classList.contains('modal-overlay')) {
    handleClose();
  }
};
</script>

<template>
  <Transition name="modal">
    <div
      v-if="visible"
      class="modal-overlay"
      @click="handleClickOutside"
    >
      <div class="modal-container">
        <!-- 模态框头部 -->
        <div class="modal-header">
          <div class="header-content">
            <i class="ri-file-text-line header-icon"></i>
            <div>
              <h3 class="modal-title">简历管理</h3>
              <p v-if="candidateName" class="modal-subtitle">{{ candidateName }}</p>
            </div>
          </div>
          <button class="close-btn" @click="handleClose">
            <i class="ri-close-line"></i>
          </button>
        </div>

        <!-- 模态框内容 -->
        <div class="modal-body">
          <div v-if="loading" class="loading-state">
            <i class="ri-loader-4-line spin"></i>
            <p>加载中...</p>
          </div>

          <!-- 上传界面 -->
          <ResumeUpload
            v-else-if="!hasResume && candidateId"
            :candidate-id="candidateId"
            :candidate-name="candidateName"
            @uploaded="(data) => emit('uploaded', data)"
            @error="(error) => emit('error', error)"
          />

          <!-- 展示界面 -->
          <ResumeDisplay
            v-else-if="hasResume"
            :resume-data="resumeInfo.parsed_data || {}"
            :file-name="resumeInfo.file_name"
            :uploaded-at="resumeInfo.uploaded_at"
            :on-download="() => emit('download')"
            :on-delete="() => emit('delete')"
            :on-parse="handleParse"
            :is-parsing="isParsing"
            :is-parsed="isParsed"
            :is-regenerating="isRegeneratingPortrait"
          />
          
          <!-- 解析完成 Toast -->
          <Transition name="toast">
            <div v-if="showParseToast" class="parse-toast">
              <i class="ri-checkbox-circle-fill"></i>
              <span>简历解析完成！</span>
            </div>
          </Transition>
        </div>
      </div>
    </div>
  </Transition>
</template>

<style scoped>
/* 模态框过渡动画 */
.modal-enter-active,
.modal-leave-active {
  transition: opacity 0.3s ease;
}

.modal-enter-from,
.modal-leave-to {
  opacity: 0;
}

.modal-enter-active .modal-container,
.modal-leave-active .modal-container {
  transition: transform 0.3s ease;
}

.modal-enter-from .modal-container,
.modal-leave-to .modal-container {
  transform: scale(0.95);
}

/* 模态框遮罩 */
.modal-overlay {
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
  z-index: 1000;
  padding: 2rem;
}

/* 模态框容器 */
.modal-container {
  background: white;
  border-radius: 16px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
  max-width: 800px;
  width: 100%;
  max-height: 90vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

/* 模态框头部 */
.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 1.5rem;
  border-bottom: 1px solid #e2e8f0;
  background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%);
}

.header-content {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.header-icon {
  width: 48px;
  height: 48px;
  border-radius: 12px;
  background: linear-gradient(135deg, #6366f1, #8b5cf6);
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  font-size: 1.5rem;
  flex-shrink: 0;
}

.modal-title {
  font-size: 1.25rem;
  font-weight: 700;
  color: #1e293b;
  margin: 0;
}

.modal-subtitle {
  font-size: 0.875rem;
  color: #64748b;
  margin: 0.25rem 0 0 0;
}

.close-btn {
  width: 36px;
  height: 36px;
  border-radius: 8px;
  border: none;
  background: transparent;
  color: #64748b;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s ease;
  font-size: 1.25rem;
}

.close-btn:hover {
  background: #f1f5f9;
  color: #1e293b;
}

/* 模态框内容 */
.modal-body {
  flex: 1;
  overflow-y: auto;
  padding: 1.5rem;
}

/* 加载状态 */
.loading-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 3rem;
  color: #64748b;
}

.loading-state i {
  font-size: 3rem;
  color: #6366f1;
  margin-bottom: 1rem;
}

.loading-state p {
  margin: 0;
  font-size: 0.9375rem;
}

.spin {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

/* 解析完成 Toast */
.parse-toast {
  position: fixed;
  top: 2rem;
  left: 50%;
  transform: translateX(-50%);
  background: linear-gradient(135deg, #10b981 0%, #059669 100%);
  color: white;
  padding: 0.875rem 1.5rem;
  border-radius: 12px;
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-weight: 600;
  font-size: 0.9375rem;
  box-shadow: 0 8px 24px rgba(16, 185, 129, 0.35);
  z-index: 2000;
}

.parse-toast i {
  font-size: 1.25rem;
}

/* Toast 动画 */
.toast-enter-active,
.toast-leave-active {
  transition: all 0.3s ease;
}

.toast-enter-from {
  opacity: 0;
  transform: translateX(-50%) translateY(-20px);
}

.toast-leave-to {
  opacity: 0;
  transform: translateX(-50%) translateY(-20px);
}

/* 响应式 */
@media (max-width: 768px) {
  .modal-overlay {
    padding: 1rem;
  }

  .modal-container {
    max-width: 100%;
  }

  .modal-header {
    padding: 1rem;
  }

  .modal-body {
    padding: 1rem;
  }
}
</style>

