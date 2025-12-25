<script setup lang="ts">
import { computed } from 'vue';

interface ResumeData {
  name?: string;
  email?: string;
  phone?: string;
  location?: string;
  target_position?: string;  // ⭐ 新增：目标岗位
  education?: Array<{
    school: string;
    major?: string;
    degree?: string;
    start_date?: string;
    end_date?: string;
  }>;
  experience?: Array<{
    company: string;
    position: string;
    start_date?: string;
    end_date?: string;
    responsibilities?: string[];
  }>;
  projects?: Array<{
    name: string;
    role?: string;
    start_date?: string;
    end_date?: string;
    description?: string;
    technologies?: string[];
  }>;
  skills?: string[];
  certificates?: string[];
  languages?: string[];
  summary?: string;
}

const props = defineProps<{
  resumeData: ResumeData;
  fileName?: string;
  uploadedAt?: string;
  onDownload?: () => void;
  onDelete?: () => void;
  onParse?: (level: 'pro' | 'expert') => void;  // 开始解析（带级别），解析完成后自动生成画像
  isParsing?: boolean;               // 是否正在解析
  isParsed?: boolean;                // 是否已解析完成
  isRegenerating?: boolean;          // 是否正在重新生成画像
}>();

// 深度分析级别固定为 pro（后端默认 DeepSeek），隐藏级别选择
const handleParse = () => {
  if (props.onParse) {
    props.onParse('pro');
  }
};

// 注：画像生成已整合到解析流程中，解析完成后自动生成画像

// 解析按钮文字
const parseButtonText = computed(() => {
  if (props.isParsing) return 'AI解析中...';
  if (props.isRegenerating) return '生成画像中...';
  if (props.isParsed) return '重新解析';
  return '开始解析';
});

// 解析按钮是否禁用
const isParseDisabled = computed(() => {
  return props.isParsing || props.isRegenerating;
});

const hasData = computed(() => {
  return props.resumeData && Object.keys(props.resumeData).length > 0;
});

const formattedDate = computed(() => {
  if (!props.uploadedAt) return '';
  return new Date(props.uploadedAt).toLocaleString('zh-CN');
});
</script>

<template>
  <div class="resume-display">
    <!-- 文件信息卡片 -->
    <div class="file-info-card">
      <div class="file-header">
        <div class="file-icon-wrapper">
          <i class="ri-file-text-line"></i>
        </div>
        <div class="file-meta">
          <h3 class="file-name">{{ fileName || '简历.pdf' }}</h3>
          <p class="upload-time">上传于 {{ formattedDate }}</p>
        </div>
      </div>
      
      <div class="file-actions">
        <button 
          v-if="onParse" 
          class="action-btn primary" 
          :class="{ parsing: isParsing || isRegenerating, parsed: isParsed }"
          @click="handleParse" 
          :disabled="isParseDisabled"
          :title="parseButtonText"
        >
          <i :class="(isParsing || isRegenerating) ? 'ri-loader-4-line spin' : (isParsed ? 'ri-refresh-line' : 'ri-play-circle-line')"></i>
          {{ parseButtonText }}
        </button>
        <button v-if="onDownload" class="action-btn" @click="onDownload" title="下载简历">
          <i class="ri-download-line"></i>
          下载
        </button>
        <button v-if="onDelete" class="action-btn danger" @click="onDelete" title="删除简历">
          <i class="ri-delete-bin-line"></i>
          删除
        </button>
      </div>
    </div>
    
    <!-- AI分析级别选择区域（隐藏UI，固定使用深度分析） -->
    <div v-if="false"></div>
    
    <!-- 解析结果 -->
    <div v-if="hasData" class="parsed-content">
      <!-- 基本信息 -->
      <div v-if="resumeData.name || resumeData.email || resumeData.phone || resumeData.target_position" class="info-section">
        <h4 class="section-title">
          <i class="ri-user-line"></i>
          基本信息
        </h4>
        <div class="info-grid">
          <div v-if="resumeData.name" class="info-item">
            <span class="info-label">姓名</span>
            <span class="info-value">{{ resumeData.name }}</span>
          </div>
          <div v-if="resumeData.target_position" class="info-item highlight">
            <span class="info-label">目标岗位</span>
            <span class="info-value position-value">{{ resumeData.target_position }}</span>
          </div>
          <div v-if="resumeData.email" class="info-item">
            <span class="info-label">邮箱</span>
            <span class="info-value">{{ resumeData.email }}</span>
          </div>
          <div v-if="resumeData.phone" class="info-item">
            <span class="info-label">电话</span>
            <span class="info-value">{{ resumeData.phone }}</span>
          </div>
          <div v-if="resumeData.location" class="info-item">
            <span class="info-label">所在地</span>
            <span class="info-value">{{ resumeData.location }}</span>
          </div>
        </div>
      </div>
      
      <!-- 教育背景 -->
      <div v-if="resumeData.education && resumeData.education.length > 0" class="info-section">
        <h4 class="section-title">
          <i class="ri-graduation-cap-line"></i>
          教育背景
        </h4>
        <div class="timeline">
          <div v-for="(edu, index) in resumeData.education" :key="index" class="timeline-item">
            <div class="timeline-dot"></div>
            <div class="timeline-content">
              <div class="timeline-header">
                <h5 class="timeline-title">{{ edu.school }}</h5>
                <span v-if="edu.start_date || edu.end_date" class="timeline-date">
                  {{ edu.start_date }} - {{ edu.end_date }}
                </span>
              </div>
              <p v-if="edu.major || edu.degree" class="timeline-subtitle">
                {{ edu.major }} {{ edu.degree ? `· ${edu.degree}` : '' }}
              </p>
            </div>
          </div>
        </div>
      </div>
      
      <!-- 工作经历 -->
      <div v-if="resumeData.experience && resumeData.experience.length > 0" class="info-section">
        <h4 class="section-title">
          <i class="ri-briefcase-line"></i>
          工作经历
        </h4>
        <div class="timeline">
          <div v-for="(exp, index) in resumeData.experience" :key="index" class="timeline-item">
            <div class="timeline-dot"></div>
            <div class="timeline-content">
              <div class="timeline-header">
                <h5 class="timeline-title">{{ exp.company }}</h5>
                <span v-if="exp.start_date || exp.end_date" class="timeline-date">
                  {{ exp.start_date }} - {{ exp.end_date }}
                </span>
              </div>
              <p class="timeline-subtitle">{{ exp.position }}</p>
              <ul v-if="exp.responsibilities && exp.responsibilities.length > 0" class="responsibility-list">
                <li v-for="(resp, i) in exp.responsibilities" :key="i">{{ resp }}</li>
              </ul>
            </div>
          </div>
        </div>
      </div>
      
      <!-- 技能 -->
      <div v-if="resumeData.skills && resumeData.skills.length > 0" class="info-section">
        <h4 class="section-title">
          <i class="ri-code-s-slash-line"></i>
          技能
        </h4>
        <div class="tag-list">
          <span v-for="(skill, index) in resumeData.skills" :key="index" class="tag">
            {{ skill }}
          </span>
        </div>
      </div>
    </div>
    
    <!-- 无数据状态 -->
    <div v-else class="empty-state">
      <i class="ri-file-search-line"></i>
      <p>暂无解析数据</p>
    </div>
  </div>
</template>

<style scoped>
.resume-display {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.file-info-card {
  background: white;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  padding: 1.25rem;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 1rem;
}

.file-header {
  display: flex;
  align-items: center;
  gap: 1rem;
  flex: 1;
}

.file-icon-wrapper {
  width: 48px;
  height: 48px;
  border-radius: 10px;
  background: linear-gradient(135deg, #6366f1, #8b5cf6);
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  font-size: 1.5rem;
  flex-shrink: 0;
}

.file-meta {
  flex: 1;
  min-width: 0;
}

.file-name {
  font-size: 1rem;
  font-weight: 600;
  color: #1e293b;
  margin: 0 0 0.25rem 0;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.upload-time {
  font-size: 0.8125rem;
  color: #64748b;
  margin: 0;
}

.file-actions {
  display: flex;
  gap: 0.5rem;
  flex-shrink: 0;
}

.action-btn {
  padding: 0.5rem 0.875rem;
  border-radius: 8px;
  border: 1px solid #e2e8f0;
  background: white;
  color: #475569;
  font-size: 0.8125rem;
  font-weight: 500;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 0.375rem;
  transition: all 0.2s ease;
}

.action-btn:hover {
  background: #f8fafc;
  border-color: #cbd5e1;
}

.action-btn.danger {
  color: #dc2626;
}

.action-btn.danger:hover {
  background: #fef2f2;
  border-color: #fecaca;
}

.action-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.action-btn.parsing {
  color: #6366f1;
  border-color: #c7d2fe;
  background: #eef2ff;
}

.action-btn.parsed {
  color: #059669;
  border-color: #a7f3d0;
}

.action-btn.parsed:hover {
  background: #ecfdf5;
  border-color: #6ee7b7;
}

.parsed-content {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.info-section {
  background: white;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  padding: 1.5rem;
}

.section-title {
  font-size: 1rem;
  font-weight: 700;
  color: #1e293b;
  margin: 0 0 1.25rem 0;
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.section-title i {
  color: #6366f1;
  font-size: 1.125rem;
}

.info-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 1rem;
}

.info-item {
  display: flex;
  flex-direction: column;
  gap: 0.375rem;
}

.info-label {
  font-size: 0.75rem;
  font-weight: 600;
  color: #64748b;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.info-value {
  font-size: 0.9375rem;
  color: #1e293b;
}

.info-item.highlight {
  grid-column: span 2;
  background: linear-gradient(135deg, #eef2ff 0%, #e0e7ff 100%);
  padding: 0.75rem 1rem;
  border-radius: 8px;
  border-left: 3px solid #6366f1;
}

.position-value {
  font-weight: 600;
  color: #4f46e5;
  font-size: 1rem;
}

.timeline {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.timeline-item {
  display: flex;
  gap: 1rem;
  position: relative;
}

.timeline-item:not(:last-child)::before {
  content: '';
  position: absolute;
  left: 7px;
  top: 24px;
  bottom: -24px;
  width: 2px;
  background: #e2e8f0;
}

.timeline-dot {
  width: 16px;
  height: 16px;
  border-radius: 50%;
  background: #6366f1;
  border: 3px solid #eef2ff;
  flex-shrink: 0;
  margin-top: 4px;
  z-index: 1;
}

.timeline-content {
  flex: 1;
}

.timeline-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 1rem;
  margin-bottom: 0.375rem;
}

.timeline-title {
  font-size: 0.9375rem;
  font-weight: 600;
  color: #1e293b;
  margin: 0;
}

.timeline-date {
  font-size: 0.8125rem;
  color: #6366f1;
  font-weight: 500;
  white-space: nowrap;
}

.timeline-subtitle {
  font-size: 0.875rem;
  color: #64748b;
  margin: 0 0 0.75rem 0;
}

.responsibility-list {
  margin: 0;
  padding-left: 1.25rem;
  font-size: 0.8125rem;
  color: #475569;
  line-height: 1.8;
}

.responsibility-list li {
  margin-bottom: 0.375rem;
}

.tag-list {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}

.tag {
  padding: 0.375rem 0.75rem;
  border-radius: 6px;
  background: #eef2ff;
  color: #6366f1;
  font-size: 0.8125rem;
  font-weight: 500;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 3rem;
  color: #94a3b8;
}

.empty-state i {
  font-size: 4rem;
  margin-bottom: 1rem;
  opacity: 0.5;
}

.empty-state p {
  margin: 0;
  font-size: 0.9375rem;
}

/* AI分析区域 */
.analysis-section {
  background: linear-gradient(135deg, #faf5ff 0%, #f3e8ff 100%);
  border: 1px solid #e9d5ff;
  border-radius: 16px;
  padding: 1.5rem;
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
}

.analysis-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
}

.analysis-info {
  display: flex;
  align-items: flex-start;
  gap: 0.875rem;
  flex: 1;
}

.analysis-info > i {
  font-size: 1.75rem;
  color: #9333ea;
  flex-shrink: 0;
  margin-top: 0.125rem;
}

.analysis-info h4 {
  font-size: 1rem;
  font-weight: 600;
  color: #6b21a8;
  margin: 0 0 0.375rem 0;
}

.analysis-info p {
  font-size: 0.8125rem;
  color: #7c3aed;
  opacity: 0.85;
  margin: 0;
  line-height: 1.5;
}

.level-selector-wrapper {
  background: white;
  border-radius: 12px;
  padding: 1rem;
  box-shadow: 0 2px 8px rgba(147, 51, 234, 0.08);
}

/* 状态提示 */
.status-hint {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  padding: 0.75rem;
  background: rgba(147, 51, 234, 0.1);
  border-radius: 8px;
  color: #7c3aed;
  font-size: 0.875rem;
  font-weight: 500;
}

.status-hint i {
  font-size: 1.125rem;
}

/* 主要操作按钮样式 */
.action-btn.primary {
  background: linear-gradient(135deg, #9333ea 0%, #7c3aed 100%);
  color: white;
  border: none;
  box-shadow: 0 2px 8px rgba(147, 51, 234, 0.25);
}

.action-btn.primary:hover:not(:disabled) {
  box-shadow: 0 4px 12px rgba(147, 51, 234, 0.35);
  transform: translateY(-1px);
}

.action-btn.primary:disabled {
  opacity: 0.6;
  background: linear-gradient(135deg, #9ca3af 0%, #6b7280 100%);
  box-shadow: none;
  transform: none;
}

.action-btn.primary.parsing {
  background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);
}

/* 已解析状态的主要按钮 - 绿色渐变 */
.action-btn.primary.parsed {
  background: linear-gradient(135deg, #10b981 0%, #059669 100%);
  box-shadow: 0 2px 8px rgba(16, 185, 129, 0.25);
}

.action-btn.primary.parsed:hover:not(:disabled) {
  background: linear-gradient(135deg, #059669 0%, #047857 100%);
  box-shadow: 0 4px 12px rgba(16, 185, 129, 0.35);
  transform: translateY(-1px);
}

.spin {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}
</style>

