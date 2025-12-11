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
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal-dialog {
  background: white;
  border-radius: 20px;
  width: 100%;
  max-width: 720px;
  max-height: 90vh;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.2);
}

/* 头部 */
.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 20px 24px;
  border-bottom: 1px solid #e2e8f0;
  background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%);
}

.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.detail-code {
  font-size: 14px;
  font-weight: 600;
  color: #64748b;
  font-family: monospace;
}

.status-badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  border-radius: 20px;
  font-size: 13px;
  font-weight: 500;
}

.status-badge.completed {
  background: #d1fae5;
  color: #065f46;
}

.status-badge.progress {
  background: #fef3c7;
  color: #92400e;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.btn-action {
  width: 36px;
  height: 36px;
  border: none;
  background: white;
  border-radius: 10px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #64748b;
  font-size: 18px;
  transition: all 0.2s;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.btn-action:hover {
  background: #f1f5f9;
  color: #334155;
}

.btn-action.delete:hover {
  background: #fee2e2;
  color: #ef4444;
}

.btn-close {
  width: 36px;
  height: 36px;
  border: none;
  background: #f1f5f9;
  border-radius: 10px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #64748b;
  font-size: 20px;
  transition: all 0.2s;
}

.btn-close:hover {
  background: #fee2e2;
  color: #ef4444;
}

/* 内容 */
.modal-body {
  flex: 1;
  overflow-y: auto;
  padding: 24px;
}

/* 候选人卡片 */
.candidate-card {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 20px;
  background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);
  border-radius: 16px;
  margin-bottom: 24px;
  color: white;
}

.candidate-avatar {
  width: 56px;
  height: 56px;
  background: rgba(255, 255, 255, 0.2);
  border-radius: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 24px;
  font-weight: 600;
}

.candidate-info {
  flex: 1;
}

.candidate-info h3 {
  font-size: 20px;
  font-weight: 600;
  margin: 0 0 6px;
}

.candidate-info .info-row {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  opacity: 0.9;
}

.score-badge {
  display: flex;
  align-items: baseline;
  gap: 4px;
  padding: 8px 16px;
  background: rgba(255, 255, 255, 0.2);
  border-radius: 12px;
}

.score-value {
  font-size: 28px;
  font-weight: 700;
}

.score-label {
  font-size: 14px;
  opacity: 0.8;
}

.grade-badge {
  width: 48px;
  height: 48px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 24px;
  font-weight: 700;
  background: rgba(255, 255, 255, 0.2);
}

.grade-badge.grade-a { background: #10b981; }
.grade-badge.grade-b { background: #3b82f6; }
.grade-badge.grade-c { background: #f59e0b; }
.grade-badge.grade-d { background: #ef4444; }

/* 详情区块 */
.detail-section {
  background: #f8fafc;
  border-radius: 16px;
  padding: 20px;
  margin-bottom: 20px;
}

.section-title {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 16px;
  font-weight: 600;
  color: #334155;
  margin: 0 0 16px;
}

.section-title i {
  font-size: 20px;
  color: #6366f1;
}

/* 信息网格 */
.info-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
}

.info-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.info-item label {
  font-size: 12px;
  color: #64748b;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.info-item span {
  font-size: 14px;
  font-weight: 500;
  color: #1e293b;
}

.type-badge {
  display: inline-block;
  padding: 4px 10px;
  background: linear-gradient(135deg, #6366f1, #8b5cf6);
  color: white;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 600;
}

/* 人格卡片 */
.personality-card {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 20px;
  border-radius: 14px;
  margin-bottom: 20px;
}

.personality-card.mbti {
  background: linear-gradient(135deg, #dbeafe 0%, #e0e7ff 100%);
}

.personality-card.disc {
  background: linear-gradient(135deg, #fef3c7 0%, #fde68a 100%);
}

.personality-card.epq {
  background: linear-gradient(135deg, #d1fae5 0%, #a7f3d0 100%);
}

.personality-icon {
  width: 56px;
  height: 56px;
  border-radius: 14px;
  background: white;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 28px;
}

.personality-card.mbti .personality-icon { color: #3b82f6; }
.personality-card.disc .personality-icon { color: #f59e0b; }
.personality-card.epq .personality-icon { color: #10b981; }

.personality-info h3 {
  font-size: 28px;
  font-weight: 700;
  margin: 0 0 4px;
  color: #1e293b;
}

.personality-info p {
  font-size: 14px;
  color: #64748b;
  margin: 0;
}

/* 维度网格 */
.dimensions-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
}

.dimension-item {
  background: white;
  border-radius: 12px;
  padding: 16px;
}

.dimension-header {
  display: flex;
  justify-content: space-between;
  margin-bottom: 8px;
}

.dimension-key {
  font-size: 13px;
  font-weight: 600;
  color: #475569;
}

.dimension-value {
  font-size: 14px;
  font-weight: 700;
  color: #3b82f6;
}

.dimension-bar {
  width: 100%;
  height: 8px;
  background: #e2e8f0;
  border-radius: 4px;
  overflow: hidden;
  margin-bottom: 8px;
}

.dimension-fill {
  height: 100%;
  border-radius: 4px;
  transition: width 0.5s ease;
}

.dimension-fill.mbti {
  background: linear-gradient(90deg, #3b82f6, #6366f1);
}

.dimension-label {
  font-size: 12px;
  color: #64748b;
}

/* DISC 维度列表 */
.dimensions-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.dimension-bar-item {
  background: white;
  border-radius: 12px;
  padding: 16px;
}

.bar-header {
  display: flex;
  justify-content: space-between;
  margin-bottom: 10px;
}

.bar-label {
  font-size: 14px;
  font-weight: 500;
  color: #334155;
}

.bar-value {
  font-size: 14px;
  font-weight: 700;
  color: #1e293b;
}

.bar-track {
  height: 12px;
  background: #e2e8f0;
  border-radius: 6px;
  overflow: hidden;
}

.bar-fill {
  height: 100%;
  border-radius: 6px;
  transition: width 0.5s ease;
}

.bar-fill.disc-d { background: linear-gradient(90deg, #ef4444, #f87171); }
.bar-fill.disc-i { background: linear-gradient(90deg, #f59e0b, #fbbf24); }
.bar-fill.disc-s { background: linear-gradient(90deg, #10b981, #34d399); }
.bar-fill.disc-c { background: linear-gradient(90deg, #3b82f6, #60a5fa); }

/* MBTI 维度条颜色 */
.bar-fill.mbti { background: linear-gradient(90deg, #8b5cf6, #a78bfa); }

/* EPQ 维度 */
.epq-dimensions {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.epq-dimension {
  background: white;
  border-radius: 12px;
  padding: 16px;
}

.epq-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 12px;
}

.epq-key {
  width: 32px;
  height: 32px;
  background: linear-gradient(135deg, #10b981, #059669);
  color: white;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  font-weight: 700;
}

.epq-name {
  flex: 1;
  font-size: 14px;
  font-weight: 500;
  color: #334155;
}

.epq-level {
  padding: 4px 10px;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 600;
}

.epq-level.level-high { background: #fee2e2; color: #dc2626; }
.epq-level.level-medium { background: #fef3c7; color: #d97706; }
.epq-level.level-low { background: #d1fae5; color: #059669; }

.epq-scores {
  display: flex;
  gap: 20px;
  margin-bottom: 12px;
}

.epq-score {
  font-size: 13px;
  color: #64748b;
}

.epq-score.highlight {
  font-weight: 600;
  color: #10b981;
}

.epq-bar {
  height: 8px;
  background: #e2e8f0;
  border-radius: 4px;
  overflow: hidden;
}

.epq-fill {
  height: 100%;
  background: linear-gradient(90deg, #10b981, #059669);
  border-radius: 4px;
  transition: width 0.5s ease;
}

/* 分数汇总 */
.score-summary {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 40px;
  padding: 20px;
  background: white;
  border-radius: 14px;
}

.summary-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
}

.summary-label {
  font-size: 13px;
  color: #64748b;
}

.summary-value {
  font-size: 32px;
  font-weight: 700;
  color: #1e293b;
}

.summary-value.grade {
  padding: 8px 20px;
  border-radius: 12px;
  font-size: 24px;
  color: white;
}

.summary-value.grade.grade-a { background: #10b981; }
.summary-value.grade.grade-b { background: #3b82f6; }
.summary-value.grade.grade-c { background: #f59e0b; }
.summary-value.grade.grade-d { background: #ef4444; }

.summary-divider {
  width: 1px;
  height: 50px;
  background: #e2e8f0;
}

/* 答题详情 */
.answers-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
  max-height: 400px;
  overflow-y: auto;
}

.answer-item {
  background: white;
  border-radius: 12px;
  padding: 16px;
}

.answer-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 12px;
  padding-bottom: 12px;
  border-bottom: 1px solid #f1f5f9;
}

.answer-index {
  padding: 4px 10px;
  background: linear-gradient(135deg, #6366f1, #8b5cf6);
  color: white;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 600;
}

.answer-title {
  flex: 1;
  font-size: 14px;
  font-weight: 500;
  color: #334155;
}

.answer-content {
  margin-bottom: 12px;
}

.answer-options {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.option-tag {
  padding: 6px 12px;
  background: #f1f5f9;
  border-radius: 6px;
  font-size: 13px;
  color: #475569;
}

.answer-text {
  font-size: 14px;
  color: #475569;
  line-height: 1.6;
}

.answer-scale {
  display: flex;
  align-items: baseline;
  gap: 4px;
}

.scale-value {
  font-size: 24px;
  font-weight: 700;
  color: #6366f1;
}

.scale-label {
  font-size: 14px;
  color: #64748b;
}

.answer-score {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 8px 12px;
  background: #d1fae5;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 500;
  color: #065f46;
}

.score-earned {
  font-weight: 700;
  color: #059669;
}

.score-separator {
  color: #94a3b8;
}

.score-max {
  color: #64748b;
}

.score-percent {
  color: #10b981;
  margin-left: 8px;
}

/* 底部 */
.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  padding: 16px 24px;
  border-top: 1px solid #e2e8f0;
  background: #f8fafc;
}

.btn-primary {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 12px 24px;
  background: linear-gradient(135deg, #6366f1, #8b5cf6);
  color: white;
  border: none;
  border-radius: 12px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-primary:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(99, 102, 241, 0.3);
}

.btn-secondary {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 12px 24px;
  background: white;
  color: #475569;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-secondary:hover {
  background: #f1f5f9;
}

/* 响应式 */
@media (max-width: 640px) {
  .modal-dialog {
    margin: 16px;
    max-height: calc(100vh - 32px);
  }
  
  .info-grid {
    grid-template-columns: 1fr;
  }
  
  .dimensions-grid {
    grid-template-columns: 1fr;
  }
  
  .candidate-card {
    flex-wrap: wrap;
  }
}
</style>

