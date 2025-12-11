<script setup lang="ts">
import { ref, computed } from 'vue';
import { uploadResume } from '../../api/resumes';

const props = defineProps<{
  candidateId: number;
  candidateName?: string;
}>();

const emit = defineEmits<{
  uploaded: [data: any];
  error: [error: string];
}>();

const isDragging = ref(false);
const isUploading = ref(false);
const uploadProgress = ref(0);
const selectedFile = ref<File | null>(null);
const fileInput = ref<HTMLInputElement | null>(null);

const acceptedFormats = ['.pdf', '.doc', '.docx'];
const maxFileSize = 10 * 1024 * 1024; // 10MB

// 文件验证
const validateFile = (file: File): string | null => {
  const fileExt = '.' + file.name.split('.').pop()?.toLowerCase();
  
  if (!acceptedFormats.includes(fileExt)) {
    return `不支持的文件格式。支持的格式：${acceptedFormats.join(', ')}`;
  }
  
  if (file.size > maxFileSize) {
    return `文件大小超过限制（最大 ${maxFileSize / 1024 / 1024}MB）`;
  }
  
  return null;
};

// 文件选择
const handleFileSelect = (event: Event) => {
  const target = event.target as HTMLInputElement;
  if (target.files && target.files[0]) {
    const file = target.files[0];
    const error = validateFile(file);
    
    if (error) {
      emit('error', error);
      return;
    }
    
    selectedFile.value = file;
  }
};

// 拖拽事件
const handleDragOver = (event: DragEvent) => {
  event.preventDefault();
  isDragging.value = true;
};

const handleDragLeave = () => {
  isDragging.value = false;
};

const handleDrop = (event: DragEvent) => {
  event.preventDefault();
  isDragging.value = false;
  
  if (event.dataTransfer?.files && event.dataTransfer.files[0]) {
    const file = event.dataTransfer.files[0];
    const error = validateFile(file);
    
    if (error) {
      emit('error', error);
      return;
    }
    
    selectedFile.value = file;
  }
};

// 点击选择文件
const triggerFileSelect = () => {
  fileInput.value?.click();
};

// 清除选择
const clearSelection = () => {
  selectedFile.value = null;
  if (fileInput.value) {
    fileInput.value.value = '';
  }
};

// 上传文件
const handleUpload = async () => {
  if (!selectedFile.value) return;
  
  isUploading.value = true;
  uploadProgress.value = 0;
  
  try {
    // 模拟进度
    const progressInterval = setInterval(() => {
      if (uploadProgress.value < 90) {
        uploadProgress.value += 10;
      }
    }, 200);
    
    const result = await uploadResume(props.candidateId, selectedFile.value);
    
    clearInterval(progressInterval);
    uploadProgress.value = 100;
    
    setTimeout(() => {
      emit('uploaded', result);
      clearSelection();
      isUploading.value = false;
      uploadProgress.value = 0;
    }, 500);
    
  } catch (error: any) {
    isUploading.value = false;
    uploadProgress.value = 0;
    emit('error', error.response?.data?.detail || '上传失败');
  }
};

// 格式化文件大小
const formatFileSize = (bytes: number): string => {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
};

// 文件图标
const fileIcon = computed(() => {
  if (!selectedFile.value) return 'ri-file-line';
  const ext = selectedFile.value.name.split('.').pop()?.toLowerCase();
  if (ext === 'pdf') return 'ri-file-pdf-line';
  if (ext === 'doc' || ext === 'docx') return 'ri-file-word-line';
  return 'ri-file-line';
});
</script>

<template>
  <div class="resume-upload">
    <input
      ref="fileInput"
      type="file"
      :accept="acceptedFormats.join(',')"
      @change="handleFileSelect"
      style="display: none"
    />
    
    <div
      class="upload-area"
      :class="{ dragging: isDragging, 'has-file': selectedFile }"
      @dragover="handleDragOver"
      @dragleave="handleDragLeave"
      @drop="handleDrop"
      @click="!selectedFile && triggerFileSelect()"
    >
      <!-- 无文件状态 -->
      <div v-if="!selectedFile" class="upload-prompt">
        <i class="ri-upload-cloud-2-line upload-icon"></i>
        <h3 class="upload-title">拖拽文件到此处或点击选择</h3>
        <p class="upload-hint">
          支持格式：PDF, DOC, DOCX
          <br />
          文件大小限制：10MB
        </p>
      </div>
      
      <!-- 已选择文件 -->
      <div v-else class="file-preview">
        <i :class="fileIcon" class="file-icon"></i>
        <div class="file-info">
          <div class="file-name">{{ selectedFile.name }}</div>
          <div class="file-size">{{ formatFileSize(selectedFile.size) }}</div>
        </div>
        <button
          v-if="!isUploading"
          class="remove-btn"
          @click.stop="clearSelection"
          title="移除文件"
        >
          <i class="ri-close-line"></i>
        </button>
      </div>
      
      <!-- 上传进度 -->
      <div v-if="isUploading" class="upload-progress">
        <div class="progress-bar">
          <div class="progress-fill" :style="{ width: `${uploadProgress}%` }"></div>
        </div>
        <div class="progress-text">{{ uploadProgress }}%</div>
      </div>
    </div>
    
    <!-- 操作按钮 -->
    <div v-if="selectedFile && !isUploading" class="upload-actions">
      <button class="btn-secondary" @click="clearSelection">
        <i class="ri-close-line"></i>
        取消
      </button>
      <button class="btn-primary" @click="handleUpload">
        <i class="ri-upload-line"></i>
        上传简历
      </button>
    </div>
  </div>
</template>

<style scoped>
.resume-upload {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.upload-area {
  border: 2px dashed #cbd5e1;
  border-radius: 12px;
  padding: 2rem;
  text-align: center;
  transition: all 0.3s ease;
  cursor: pointer;
  background: #f8fafc;
}

.upload-area:hover {
  border-color: #6366f1;
  background: #f1f5f9;
}

.upload-area.dragging {
  border-color: #6366f1;
  background: #eef2ff;
  transform: scale(1.02);
}

.upload-area.has-file {
  cursor: default;
  border-color: #10b981;
  background: #ecfdf5;
}

.upload-area.has-file:hover {
  background: #d1fae5;
}

.upload-prompt {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.75rem;
}

.upload-icon {
  font-size: 3.5rem;
  color: #6366f1;
  margin-bottom: 0.5rem;
}

.upload-title {
  font-size: 1.125rem;
  font-weight: 600;
  color: #1e293b;
  margin: 0;
}

.upload-hint {
  font-size: 0.875rem;
  color: #64748b;
  line-height: 1.6;
  margin: 0;
}

.file-preview {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 1rem;
  background: white;
  border-radius: 8px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.file-icon {
  font-size: 2.5rem;
  color: #6366f1;
  flex-shrink: 0;
}

.file-info {
  flex: 1;
  text-align: left;
  min-width: 0;
}

.file-name {
  font-weight: 600;
  color: #1e293b;
  font-size: 0.9375rem;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.file-size {
  font-size: 0.8125rem;
  color: #64748b;
  margin-top: 0.25rem;
}

.remove-btn {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  border: none;
  background: #fee2e2;
  color: #dc2626;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s ease;
  flex-shrink: 0;
}

.remove-btn:hover {
  background: #fecaca;
  transform: scale(1.1);
}

.upload-progress {
  margin-top: 1rem;
}

.progress-bar {
  width: 100%;
  height: 8px;
  background: #e2e8f0;
  border-radius: 4px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #6366f1, #8b5cf6);
  transition: width 0.3s ease;
}

.progress-text {
  margin-top: 0.5rem;
  font-size: 0.875rem;
  font-weight: 600;
  color: #6366f1;
}

.upload-actions {
  display: flex;
  gap: 0.75rem;
  justify-content: flex-end;
}

.btn-primary,
.btn-secondary {
  padding: 0.625rem 1.25rem;
  border-radius: 8px;
  font-size: 0.875rem;
  font-weight: 600;
  border: none;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 0.5rem;
  transition: all 0.2s ease;
}

.btn-primary {
  background: linear-gradient(135deg, #6366f1, #8b5cf6);
  color: white;
}

.btn-primary:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(99, 102, 241, 0.3);
}

.btn-secondary {
  background: #f1f5f9;
  color: #475569;
}

.btn-secondary:hover {
  background: #e2e8f0;
}
</style>

