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
@import './styles/resume-display.css';
</style>
