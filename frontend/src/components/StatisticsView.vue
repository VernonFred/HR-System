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
@import './styles/statistics-view.css';
</style>
