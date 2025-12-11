<script setup lang="ts">
/**
 * 统计视图组件
 * 
 * 用于显示问卷的满意度分析和统计数据
 */
import { computed } from 'vue'

interface Questionnaire {
  id: number
  name: string
}

interface Submission {
  id: number
  total_score?: number
  max_score?: number
  grade?: string
  status: string
}

interface QuestionStat {
  id: string
  text: string
  avgScore: number
  scorePercentage: number
  options: {
    value: string
    label: string
    score: number
    count: number
    percentage: number
  }[]
}

interface GradeDistribution {
  grade: string
  count: number
  percentage: number
}

const props = defineProps<{
  questionnaires: Questionnaire[]
  selectedQuestionnaireId: number | null
  submissions: Submission[]
  questionStats: QuestionStat[]
  gradeDistribution: GradeDistribution[]
}>()

const emit = defineEmits<{
  (e: 'update:selectedQuestionnaireId', id: number | null): void
  (e: 'export-stats'): void
  (e: 'export-excel'): void
}>()

// 选中的问卷
const selectedQuestionnaire = computed(() => {
  if (!props.selectedQuestionnaireId) return null
  return props.questionnaires.find(q => q.id === props.selectedQuestionnaireId)
})

// 平均分
const averageScore = computed(() => {
  const completed = props.submissions.filter(s => s.status === 'completed' && s.total_score !== undefined)
  if (completed.length === 0) return 0
  const total = completed.reduce((sum, s) => sum + (s.total_score || 0), 0)
  return total / completed.length
})

// 完成率
const completionRate = computed(() => {
  if (props.submissions.length === 0) return 0
  const completed = props.submissions.filter(s => s.status === 'completed').length
  return (completed / props.submissions.length) * 100
})

// 等级名称
function getGradeName(grade: string): string {
  const names: Record<string, string> = {
    'A': '优秀',
    'B': '良好',
    'C': '合格',
    'D': '待提升'
  }
  return names[grade.toUpperCase()] || ''
}

// 处理问卷选择
function handleQuestionnaireChange(event: Event) {
  const target = event.target as HTMLSelectElement
  const value = target.value
  emit('update:selectedQuestionnaireId', value ? Number(value) : null)
}
</script>

<template>
  <div class="statistics-view-fullwidth">
    <!-- 统计视图标题栏 -->
    <div class="statistics-view-header">
      <div class="statistics-title">
        <i class="ri-bar-chart-grouped-line"></i>
        <h3>统计视图 - {{ selectedQuestionnaire?.name || '全部问卷' }}</h3>
      </div>
      <div class="statistics-toolbar">
        <select 
          :value="selectedQuestionnaireId" 
          @change="handleQuestionnaireChange"
          class="questionnaire-select"
        >
          <option :value="null">全部问卷</option>
          <option v-for="q in questionnaires" :key="q.id" :value="q.id">{{ q.name }}</option>
        </select>
        <button class="btn-export-stats" @click="emit('export-stats')">
          <i class="ri-file-pdf-line"></i>
          导出统计报告
        </button>
        <button class="btn-export-excel" @click="emit('export-excel')">
          <i class="ri-file-excel-line"></i>
          导出原始数据
        </button>
      </div>
    </div>
    
    <!-- 整体概览卡片 -->
    <div class="overview-section">
      <h4><i class="ri-line-chart-line"></i> 整体概览</h4>
      <div class="overview-cards">
        <div class="overview-card">
          <div class="overview-icon participants"><i class="ri-group-line"></i></div>
          <div class="overview-data">
            <span class="overview-value">{{ submissions.length }}</span>
            <span class="overview-label">参与人数</span>
          </div>
        </div>
        <div class="overview-card">
          <div class="overview-icon score"><i class="ri-award-line"></i></div>
          <div class="overview-data">
            <span class="overview-value">{{ averageScore.toFixed(1) }}<small>分</small></span>
            <span class="overview-label">平均得分</span>
          </div>
        </div>
        <div class="overview-card">
          <div class="overview-icon completion"><i class="ri-checkbox-circle-line"></i></div>
          <div class="overview-data">
            <span class="overview-value">{{ completionRate.toFixed(0) }}<small>%</small></span>
            <span class="overview-label">完成率</span>
          </div>
        </div>
      </div>
      
      <!-- 等级分布条形图 -->
      <div class="grade-distribution-chart">
        <h5>等级分布</h5>
        <div class="grade-bars">
          <div class="grade-bar-row" v-for="grade in gradeDistribution" :key="grade.grade">
            <div class="grade-name">{{ grade.grade }}{{ getGradeName(grade.grade) }}</div>
            <div class="grade-bar-container">
              <div 
                class="grade-bar-fill-new" 
                :class="`grade-${grade.grade.toLowerCase()}`"
                :style="{ width: Math.max(grade.percentage, 2) + '%' }"
              >
                <span class="grade-bar-text" v-if="grade.percentage > 10">{{ grade.percentage.toFixed(0) }}%</span>
              </div>
            </div>
            <div class="grade-count-new">{{ grade.count }}人</div>
          </div>
        </div>
      </div>
    </div>
    
    <!-- 各题得分统计 -->
    <div class="questions-stats-section">
      <h4><i class="ri-survey-line"></i> 各题得分统计</h4>
      
      <div v-if="questionStats.length === 0" class="empty-stats">
        <i class="ri-pie-chart-line"></i>
        <p>暂无题目统计数据</p>
        <span>请先选择一份问卷</span>
      </div>
      
      <div v-else class="questions-list">
        <div v-for="(qStat, idx) in questionStats" :key="qStat.id" class="question-stat-card">
          <div class="question-header">
            <span class="question-number">Q{{ idx + 1 }}</span>
            <span class="question-text">{{ qStat.text }}</span>
            <span class="question-avg-score">平均分：<strong>{{ qStat.avgScore.toFixed(1) }}</strong>分</span>
          </div>
          
          <div class="question-score-bar">
            <div class="score-bar-track">
              <div 
                class="score-bar-fill" 
                :style="{ width: qStat.scorePercentage + '%' }"
              ></div>
            </div>
            <span class="score-percentage">{{ qStat.scorePercentage.toFixed(0) }}%</span>
          </div>
          
          <!-- 选项分布 -->
          <div class="option-distribution">
            <div v-for="opt in qStat.options" :key="opt.value" class="option-row">
              <div class="option-label">{{ opt.label }} ({{ opt.score }}分)</div>
              <div class="option-bar-container">
                <div 
                  class="option-bar-fill" 
                  :style="{ width: Math.max(opt.percentage, 2) + '%' }"
                ></div>
              </div>
              <div class="option-count">{{ opt.count }}人 {{ opt.percentage.toFixed(0) }}%</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
/* 统计视图容器 */
.statistics-view-fullwidth {
  background: white;
  border-radius: 16px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
  padding: 24px;
}

.statistics-view-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
  padding-bottom: 16px;
  border-bottom: 1px solid #f1f5f9;
}

.statistics-title {
  display: flex;
  align-items: center;
  gap: 10px;
}

.statistics-title h3 {
  font-size: 18px;
  font-weight: 600;
  color: #1e293b;
  margin: 0;
}

.statistics-title i {
  font-size: 22px;
  color: #10b981;
}

.statistics-toolbar {
  display: flex;
  align-items: center;
  gap: 12px;
}

.questionnaire-select {
  padding: 10px 16px;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  font-size: 14px;
  color: #334155;
  background: white;
  cursor: pointer;
  min-width: 160px;
}

.questionnaire-select:focus {
  outline: none;
  border-color: #10b981;
}

/* 概览区域 */
.overview-section {
  background: linear-gradient(135deg, #f8fafc, #f1f5f9);
  border-radius: 16px;
  padding: 24px;
  margin-bottom: 28px;
}

.overview-section h4 {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 16px;
  font-weight: 600;
  color: #334155;
  margin: 0 0 20px;
}

.overview-section h4 i {
  font-size: 20px;
  color: #10b981;
}

.overview-cards {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 20px;
  margin-bottom: 28px;
}

.overview-card {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 20px 24px;
  background: white;
  border-radius: 14px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
}

.overview-icon {
  width: 56px;
  height: 56px;
  border-radius: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 26px;
  flex-shrink: 0;
}

.overview-icon.participants {
  background: linear-gradient(135deg, #dbeafe, #bfdbfe);
  color: #2563eb;
}

.overview-icon.score {
  background: linear-gradient(135deg, #d1fae5, #a7f3d0);
  color: #059669;
}

.overview-icon.completion {
  background: linear-gradient(135deg, #fef3c7, #fde68a);
  color: #d97706;
}

.overview-data {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.overview-value {
  font-size: 32px;
  font-weight: 700;
  color: #1e293b;
  line-height: 1;
}

.overview-value small {
  font-size: 16px;
  font-weight: 500;
}

.overview-label {
  font-size: 14px;
  color: #64748b;
}

/* 等级分布 */
.grade-distribution-chart {
  background: white;
  border-radius: 14px;
  padding: 20px;
}

.grade-distribution-chart h5 {
  font-size: 15px;
  font-weight: 600;
  color: #334155;
  margin: 0 0 16px;
}

.grade-bars {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.grade-bar-row {
  display: flex;
  align-items: center;
  gap: 12px;
}

.grade-name {
  width: 60px;
  font-size: 13px;
  font-weight: 600;
  color: #475569;
}

.grade-bar-container {
  flex: 1;
  height: 24px;
  background: #e2e8f0;
  border-radius: 12px;
  overflow: hidden;
}

.grade-bar-fill-new {
  height: 100%;
  border-radius: 12px;
  transition: width 0.5s ease;
  display: flex;
  align-items: center;
  justify-content: flex-end;
  padding-right: 8px;
}

.grade-bar-fill-new.grade-a { background: linear-gradient(90deg, #10b981, #059669); }
.grade-bar-fill-new.grade-b { background: linear-gradient(90deg, #3b82f6, #2563eb); }
.grade-bar-fill-new.grade-c { background: linear-gradient(90deg, #f59e0b, #d97706); }
.grade-bar-fill-new.grade-d { background: linear-gradient(90deg, #ef4444, #dc2626); }

.grade-bar-text {
  font-size: 12px;
  font-weight: 600;
  color: white;
}

.grade-count-new {
  width: 60px;
  text-align: right;
  font-size: 13px;
  color: #64748b;
}

/* 各题统计 */
.questions-stats-section {
  margin-top: 28px;
}

.questions-stats-section h4 {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 16px;
  font-weight: 600;
  color: #334155;
  margin: 0 0 20px;
}

.questions-stats-section h4 i {
  font-size: 20px;
  color: #6366f1;
}

.empty-stats {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px 20px;
  color: #94a3b8;
}

.empty-stats i {
  font-size: 48px;
  margin-bottom: 16px;
  opacity: 0.5;
}

.empty-stats p {
  font-size: 16px;
  font-weight: 500;
  margin: 0 0 8px;
}

.empty-stats span {
  font-size: 14px;
}

.questions-list {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.question-stat-card {
  background: #f8fafc;
  border-radius: 14px;
  padding: 20px;
}

.question-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
}

.question-number {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  background: linear-gradient(135deg, #6366f1, #8b5cf6);
  color: white;
  border-radius: 8px;
  font-size: 12px;
  font-weight: 600;
}

.question-text {
  flex: 1;
  font-size: 14px;
  font-weight: 500;
  color: #334155;
}

.question-avg-score {
  font-size: 13px;
  color: #64748b;
}

.question-avg-score strong {
  color: #10b981;
  font-size: 16px;
}

.question-score-bar {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
}

.score-bar-track {
  flex: 1;
  height: 8px;
  background: #e2e8f0;
  border-radius: 4px;
  overflow: hidden;
}

.score-bar-fill {
  height: 100%;
  background: linear-gradient(90deg, #10b981, #059669);
  border-radius: 4px;
  transition: width 0.5s ease;
}

.score-percentage {
  font-size: 13px;
  font-weight: 600;
  color: #10b981;
  width: 50px;
  text-align: right;
}

.option-distribution {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.option-row {
  display: flex;
  align-items: center;
  gap: 12px;
}

.option-label {
  width: 120px;
  font-size: 12px;
  color: #64748b;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.option-bar-container {
  flex: 1;
  height: 16px;
  background: #e2e8f0;
  border-radius: 8px;
  overflow: hidden;
}

.option-bar-fill {
  height: 100%;
  background: linear-gradient(90deg, #6366f1, #8b5cf6);
  border-radius: 8px;
  transition: width 0.5s ease;
}

.option-count {
  width: 80px;
  text-align: right;
  font-size: 12px;
  color: #64748b;
}

/* 导出按钮 */
.btn-export-stats,
.btn-export-excel {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 10px 16px;
  border: none;
  border-radius: 10px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
}

.btn-export-stats {
  background: linear-gradient(135deg, #ef4444, #dc2626);
  color: white;
}

.btn-export-excel {
  background: linear-gradient(135deg, #10b981, #059669);
  color: white;
}

.btn-export-stats:hover,
.btn-export-excel:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
}
</style>

