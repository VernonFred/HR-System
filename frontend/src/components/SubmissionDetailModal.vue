<script setup lang="ts">
/**
 * 提交详情弹窗组件
 *
 * 功能：
 * 1. 显示候选人信息
 * 2. 显示测评信息（问卷名称、类型、时间）
 * 3. 显示测评结果（MBTI/DISC/EPQ专业报告 或 普通问卷分数）
 * 4. 显示答题详情
 * 5. 导出报告功能
 */
import { ref, computed } from 'vue'
import type { Submission } from '../api/assessments'

// ===== Props =====
const props = defineProps<{
  submission: Submission | null
}>()

// ===== Emits =====
const emit = defineEmits<{
  (e: 'close'): void
  (e: 'delete', sub: Submission): void
  (e: 'export-pdf', sub: Submission): void
}>()

// ===== 计算属性 =====
const isProfessionalAssessment = computed(() => {
  const type = props.submission?.questionnaire_type?.toUpperCase()
  return type === 'MBTI' || type === 'DISC' || type === 'EPQ'
})

const resultDetails = computed(() => props.submission?.result_details || {})
const submissionDepartment = computed(() => {
  const value = props.submission?.custom_data?.department
  if (value === undefined || value === null) return ''
  return String(value).trim()
})
const meetingIdentity = computed(() => props.submission?.custom_data?.meeting_identity || {})
const meetingIdentityRows = computed(() => {
  const identity = meetingIdentity.value
  const currentName = String(props.submission?.candidate_name || '').trim()
  const currentPhone = String(props.submission?.candidate_phone || '').trim()
  const showMeetingName = !currentName || ['匿名', '未知'].includes(currentName)
  const showMeetingPhone = !currentPhone
  return [
    { key: 'candidate_name', icon: 'ri-user-line', value: showMeetingName ? identity.candidate_name : '' },
    { key: 'candidate_phone', icon: 'ri-phone-line', value: showMeetingPhone ? identity.candidate_phone : '' },
    { key: 'candidate_email', icon: 'ri-mail-line', value: identity.candidate_email },
    { key: 'school', icon: 'ri-school-line', value: identity.school },
    { key: 'department', icon: 'ri-building-line', value: identity.department },
    { key: 'target_position', icon: 'ri-briefcase-line', value: identity.target_position },
  ].filter(row => row.value !== undefined && row.value !== null && String(row.value).trim())
})

// ===== 方法 =====
const close = () => emit('close')

const handleDelete = () => {
  if (props.submission) {
    emit('delete', props.submission)
  }
}

const handleExportPDF = () => {
  if (props.submission) {
    emit('export-pdf', props.submission)
  }
}

const formatDate = (dateStr: string | null | undefined) => {
  if (!dateStr) return '-'
  return new Date(dateStr).toLocaleString('zh-CN')
}

// MBTI 维度标签
const getDimensionLabel = (key: string) => {
  const labels: Record<string, string> = {
    'E-I': '外向-内向',
    'S-N': '感觉-直觉',
    'T-F': '思考-情感',
    'J-P': '判断-知觉'
  }
  return labels[key] || key
}

// DISC 类型标签
const getDISCLabel = (key: string) => {
  const labels: Record<string, string> = {
    'D': '支配型',
    'I': '影响型',
    'S': '稳健型',
    'C': '谨慎型'
  }
  return labels[key] || key
}

// 获取等级颜色类
const getGradeClass = (grade: string | null | undefined) => {
  if (!grade) return ''
  return `grade-${grade.toLowerCase()}`
}

// 获取维度值（支持多种数据格式）
const getDimensionValue = (dim: any): number => {
  if (typeof dim === 'number') return dim
  if (typeof dim === 'object' && dim !== null) {
    return dim.value ?? dim.score ?? dim.percent ?? 0
  }
  return 0
}
</script>

<template>
  <div class="modal-overlay" @click="close">
    <div class="modal-dialog" @click.stop>
      <!-- 头部 -->
      <div class="modal-header">
        <div class="header-left">
          <span class="detail-code">{{ submission?.code }}</span>
          <span
            class="status-badge"
            :class="submission?.status === 'completed' ? 'completed' : 'progress'"
          >
            <i :class="submission?.status === 'completed' ? 'ri-checkbox-circle-fill' : 'ri-time-fill'"></i>
            {{ submission?.status === 'completed' ? '已完成' : '进行中' }}
          </span>
        </div>
        <div class="header-actions">
          <button class="btn-action" @click="handleExportPDF" title="导出PDF">
            <i class="ri-file-pdf-line"></i>
          </button>
          <button class="btn-action delete" @click="handleDelete" title="删除">
            <i class="ri-delete-bin-line"></i>
          </button>
          <button class="btn-close" @click="close">
            <i class="ri-close-line"></i>
          </button>
        </div>
      </div>

      <!-- 内容 -->
      <div class="modal-body">
        <!-- 候选人信息卡片 -->
        <div class="candidate-card">
          <div class="candidate-avatar">
            {{ (submission?.candidate_name || 'U')[0].toUpperCase() }}
          </div>
          <div class="candidate-info">
            <h3>{{ submission?.candidate_name || '未知' }}</h3>
            <div class="info-row">
              <i class="ri-phone-line"></i>
              <span>{{ submission?.candidate_phone || '-' }}</span>
            </div>
            <div v-if="submissionDepartment" class="info-row">
              <i class="ri-building-line"></i>
              <span>{{ submissionDepartment }}</span>
            </div>
            <div
              v-for="row in meetingIdentityRows"
              :key="row.key"
              class="info-row"
            >
              <i :class="row.icon"></i>
              <span>{{ row.value }}</span>
            </div>
          </div>
          <div v-if="submission?.total_score !== null && submission?.total_score !== undefined" class="score-badge">
            <span class="score-value">{{ submission.total_score }}</span>
            <span class="score-label">分</span>
          </div>
          <div v-if="submission?.grade" class="grade-badge" :class="getGradeClass(submission.grade)">
            {{ submission.grade }}
          </div>
        </div>

        <!-- 测评信息 -->
        <div class="detail-section">
          <h4 class="section-title">
            <i class="ri-file-list-3-line"></i>
            测评信息
          </h4>
          <div class="info-grid">
            <div class="info-item">
              <label>问卷名称</label>
              <span>{{ submission?.questionnaire_name || 'N/A' }}</span>
            </div>
            <div class="info-item">
              <label>问卷类型</label>
              <span class="type-badge">{{ submission?.questionnaire_type || 'CUSTOM' }}</span>
            </div>
            <div class="info-item">
              <label>开始时间</label>
              <span>{{ formatDate(submission?.started_at) }}</span>
            </div>
            <div class="info-item">
              <label>提交时间</label>
              <span>{{ formatDate(submission?.submitted_at) }}</span>
            </div>
          </div>
        </div>

        <!-- 测评结果 - MBTI -->
        <div v-if="submission?.status === 'completed' && submission?.questionnaire_type === 'MBTI'" class="detail-section">
          <h4 class="section-title">
            <i class="ri-brain-line"></i>
            MBTI 测评结果
          </h4>

          <div class="personality-card mbti">
            <div class="personality-icon">
              <i class="ri-brain-line"></i>
            </div>
            <div class="personality-info">
              <h3 class="personality-type">{{ resultDetails.mbti_type }}</h3>
              <p class="personality-desc">{{ resultDetails.mbti_description || '人格类型' }}</p>
            </div>
          </div>

          <div v-if="resultDetails.mbti_dimensions" class="dimensions-list">
            <div
              v-for="(dim, key) in resultDetails.mbti_dimensions"
              :key="key"
              class="dimension-bar-item"
            >
              <div class="bar-header">
                <span class="bar-label">{{ key }} - {{ getDimensionLabel(key) }}</span>
                <span class="bar-value">{{ getDimensionValue(dim) }}%</span>
              </div>
              <div class="bar-track">
                <div
                  class="bar-fill mbti"
                  :style="{ width: getDimensionValue(dim) + '%' }"
                ></div>
              </div>
            </div>
          </div>
        </div>

        <!-- 测评结果 - DISC -->
        <div v-else-if="submission?.status === 'completed' && submission?.questionnaire_type === 'DISC'" class="detail-section">
          <h4 class="section-title">
            <i class="ri-contacts-line"></i>
            DISC 测评结果
          </h4>

          <div class="personality-card disc">
            <div class="personality-icon">
              <i class="ri-contacts-line"></i>
            </div>
            <div class="personality-info">
              <h3 class="personality-type">{{ resultDetails.disc_type }}</h3>
              <p class="personality-desc">{{ resultDetails.disc_description || '行为风格' }}</p>
            </div>
          </div>

          <div v-if="resultDetails.disc_dimensions" class="dimensions-list">
            <div
              v-for="(dim, key) in resultDetails.disc_dimensions"
              :key="key"
              class="dimension-bar-item"
            >
              <div class="bar-header">
                <span class="bar-label">{{ key }}型 - {{ getDISCLabel(key) }}</span>
                <span class="bar-value">{{ typeof dim === 'object' ? dim.value : dim }}%</span>
              </div>
              <div class="bar-track">
                <div
                  class="bar-fill"
                  :class="`disc-${key.toLowerCase()}`"
                  :style="{ width: (typeof dim === 'object' ? dim.value : dim) + '%' }"
                ></div>
              </div>
            </div>
          </div>
        </div>

        <!-- 测评结果 - EPQ -->
        <div v-else-if="submission?.status === 'completed' && submission?.questionnaire_type === 'EPQ'" class="detail-section">
          <h4 class="section-title">
            <i class="ri-mental-health-line"></i>
            EPQ 测评结果
          </h4>

          <div class="personality-card epq">
            <div class="personality-icon">
              <i class="ri-mental-health-line"></i>
            </div>
            <div class="personality-info">
              <h3 class="personality-type">{{ resultDetails.epq_personality_trait || resultDetails.personality_trait }}</h3>
              <p class="personality-desc">{{ resultDetails.epq_description || '人格特征' }}</p>
            </div>
          </div>

          <div v-if="resultDetails.epq_dimensions || resultDetails.dimensions" class="epq-dimensions">
            <div
              v-for="(dim, key) in (resultDetails.epq_dimensions || resultDetails.dimensions)"
              :key="key"
              class="epq-dimension"
            >
              <div class="epq-header">
                <span class="epq-key">{{ key }}</span>
                <span class="epq-name">{{ dim.label }}</span>
                <span class="epq-level" :class="`level-${dim.level?.toLowerCase()}`">{{ dim.level }}</span>
              </div>
              <div class="epq-scores">
                <span class="epq-score">原始分: {{ dim.value }}</span>
                <span class="epq-score highlight">T分: {{ dim.t_score }}</span>
              </div>
              <div class="epq-bar">
                <div
                  class="epq-fill"
                  :style="{ width: (dim.t_score / 100 * 100) + '%' }"
                ></div>
              </div>
            </div>
          </div>
        </div>

        <!-- 普通问卷结果 -->
        <div v-else-if="submission?.status === 'completed'" class="detail-section">
          <h4 class="section-title">
            <i class="ri-bar-chart-grouped-line"></i>
            测评结果
          </h4>

          <div class="score-summary">
            <div class="summary-item">
              <span class="summary-label">总分</span>
              <span class="summary-value">{{ submission?.total_score ?? '-' }}</span>
            </div>
            <div class="summary-divider"></div>
            <div class="summary-item">
              <span class="summary-label">等级</span>
              <span class="summary-value grade" :class="getGradeClass(submission?.grade)">
                {{ submission?.grade || '-' }}
              </span>
            </div>
          </div>
        </div>

        <!-- 答题详情 -->
        <div v-if="resultDetails.answers && resultDetails.answers.length > 0" class="detail-section">
          <h4 class="section-title">
            <i class="ri-questionnaire-line"></i>
            答题详情 (共{{ resultDetails.answers.length }}题)
          </h4>

          <div class="answers-list">
            <div
              v-for="(answer, index) in resultDetails.answers"
              :key="index"
              class="answer-item"
            >
              <div class="answer-header">
                <span class="answer-index">#{{ index + 1 }}</span>
                <span class="answer-title">{{ answer.question_title }}</span>
              </div>
              <div class="answer-content">
                <!-- 单选/多选答案 -->
                <div v-if="answer.selected_options" class="answer-options">
                  <span
                    v-for="opt in (Array.isArray(answer.selected_options) ? answer.selected_options : [answer.selected_options])"
                    :key="opt"
                    class="option-tag"
                  >
                    {{ opt }}
                  </span>
                </div>
                <!-- 文本答案 -->
                <div v-else-if="answer.text_answer" class="answer-text">
                  {{ answer.text_answer }}
                </div>
                <!-- 量表答案 -->
                <div v-else-if="answer.scale_value !== undefined" class="answer-scale">
                  <span class="scale-value">{{ answer.scale_value }}</span>
                  <span class="scale-label">/ {{ answer.scale_max || 10 }}</span>
                </div>
              </div>
              <!-- 得分信息（V44: 分值为0时隐藏） -->
              <div v-if="answer.scoring && (answer.scoring.earned_score > 0 || answer.scoring.max_score > 0)" class="answer-score">
                <span class="score-earned">{{ answer.scoring.earned_score }}</span>
                <span class="score-separator">/</span>
                <span class="score-max">{{ answer.scoring.max_score }}</span>
                <span class="score-percent">({{ answer.scoring.percentage }}%)</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 底部 -->
      <div class="modal-footer">
        <button class="btn-secondary" @click="close">关闭</button>
        <button class="btn-primary" @click="handleExportPDF">
          <i class="ri-file-pdf-line"></i>
          导出报告
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
@import './styles/submission-detail-modal.css';
</style>
