<script setup lang="ts">
/**
 * 问卷详情侧滑抽屉
 *
 * 功能：
 * 1. 提交记录 Tab - 显示该问卷的所有提交记录（支持折叠/展开）
 * 2. 问卷统计 Tab - 显示统计数据（参与人数、平均分、等级分布、题目分析）
 */
import { ref, computed, watch } from 'vue'
import EChartContainer from './EChartContainer.vue'
import QuestionnaireStatsExportReport from './questionnaire-detail/QuestionnaireStatsExportReport.vue'
import QuestionnaireDetailExportModals from './questionnaire-detail/QuestionnaireDetailExportModals.vue'
import type {
  Questionnaire,
  Submission,
} from '../api/assessments'
import {
  fetchQuestionnaireQuestionStats,
  recalculateQuestionnaireScores,
  type QuestionnaireQuestionStats,
} from '../api/assessments'
import {
  getQuestionTypeLabel,
  isSingleChoiceQuestionType as isSingleChoiceQuestion,
  isTextQuestionType as isTextQuestion,
} from '../utils/questionnaireQuestionTypes'
import {
  buildAnswerDetailRows,
  buildOptionPersonRows,
  buildQuestionStatsRows,
  buildSubmissionRows,
} from '../utils/questionnaireSubmissionExport'
import { useQuestionTextAnswers } from './questionnaire-detail/useQuestionTextAnswers'
import { useQuestionVisuals } from './questionnaire-detail/useQuestionVisuals'
import { useTrendChart } from './questionnaire-detail/useTrendChart'
import { useQuestionnaireExports } from './questionnaire-detail/useQuestionnaireExports'
import { useGroupedSubmissions } from './questionnaire-detail/useGroupedSubmissions'
import {
  buildScoringDisplayConfig,
  getDistributionRows,
} from '../utils/scoringDisplayConfig'

// ===== Props =====
const props = defineProps<{
  questionnaire: Questionnaire | null
  submissions: Submission[]
}>()

// ===== Emits =====
const emit = defineEmits<{
  (e: 'close'): void
  (e: 'distribute', q: Questionnaire): void
  (e: 'view-submission', sub: Submission): void
  (e: 'delete-submission', sub: Submission): void
  (e: 'delete-batch', submissions: Submission[]): void  // ⭐ V44: 批量删除
}>()

// ===== 状态 =====
const activeTab = ref<'submissions' | 'statistics'>('submissions')

// 选中的提交记录（用于显示详情）
const selectedSubmission = ref<Submission | null>(null)

// 展开的候选人
const expandedCandidates = ref<Set<string>>(new Set())

// V45: 年份/月份筛选
const filterYear = ref<number | null>(null)
const filterMonth = ref<number | null>(null)

// 生成年份选项（从2024年到当前年份）
const yearOptions = computed(() => {
  const currentYear = new Date().getFullYear()
  const years: number[] = []
  for (let y = currentYear; y >= 2024; y--) {
    years.push(y)
  }
  return years
})

// 月份选项
const monthOptions = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]

// V45: 筛选后的提交记录
const filteredSubmissions = computed(() => {
  let result = [...props.submissions]

  // 年份筛选
  if (filterYear.value) {
    result = result.filter(s => {
      const dateStr = s.submitted_at || s.started_at
      if (!dateStr) return false
      const date = new Date(dateStr)
      return date.getFullYear() === filterYear.value
    })
  }

  // 月份筛选
  if (filterMonth.value) {
    result = result.filter(s => {
      const dateStr = s.submitted_at || s.started_at
      if (!dateStr) return false
      const date = new Date(dateStr)
      return (date.getMonth() + 1) === filterMonth.value
    })
  }

  return result
})

// ⭐ V44: 批量删除功能
const selectedSubmissions = ref<Set<number>>(new Set())
const showBatchDeleteModal = ref(false)
const isSelectMode = ref(false)

// 切换选择模式
const toggleSelectMode = () => {
  isSelectMode.value = !isSelectMode.value
  if (!isSelectMode.value) {
    selectedSubmissions.value.clear()
  }
}

// 切换单条记录选择
const toggleSubmissionSelect = (id: number) => {
  if (selectedSubmissions.value.has(id)) {
    selectedSubmissions.value.delete(id)
  } else {
    selectedSubmissions.value.add(id)
  }
}

// 全选/取消全选
const toggleSelectAll = () => {
  if (selectedSubmissions.value.size === props.submissions.length) {
    selectedSubmissions.value.clear()
  } else {
    selectedSubmissions.value = new Set(props.submissions.map(s => s.id))
  }
}

// 打开批量删除确认弹窗
const openBatchDeleteModal = () => {
  if (selectedSubmissions.value.size === 0) return
  showBatchDeleteModal.value = true
}

// 确认批量删除
const confirmBatchDelete = () => {
  const toDelete = props.submissions.filter(s => selectedSubmissions.value.has(s.id))
  emit('delete-batch', toDelete)
  showBatchDeleteModal.value = false
  selectedSubmissions.value.clear()
  isSelectMode.value = false
}

// ⭐ V42: 问卷统计数据
const questionStats = ref<QuestionnaireQuestionStats | null>(null)
const statsLoading = ref(false)
const statsError = ref<string | null>(null)
const trendRange = ref<'week' | 'month'>('week')
const scoreRecalculating = ref(false)

// ⭐ V43: 题目分析分页
const questionPageSize = 10
const questionCurrentPage = ref(1)

// 文本题分页与聚合展示
const {
  getTextTags,
  getTextLongAnswers,
  getTextEmptyCount,
  getTextPage,
  setTextPage,
  getTextTotalPages,
  getTextLongAnswerPage,
  hasTextSummary,
  resetTextPages,
} = useQuestionTextAnswers()

// 加载问卷统计数据
const loadQuestionStats = async () => {
  if (!props.questionnaire?.id) return

  statsLoading.value = true
  statsError.value = null

  try {
    const data = await fetchQuestionnaireQuestionStats(props.questionnaire.id, trendRange.value)
    questionStats.value = data
  } catch (err) {
    console.error('加载问卷统计失败:', err)
    statsError.value = '加载统计数据失败'
  } finally {
    statsLoading.value = false
  }
}

// 当切换到统计Tab时加载数据
// V46: 每次切换都重新加载，确保数据最新
watch(activeTab, (newTab) => {
  if (newTab === 'statistics' && props.questionnaire?.id) {
    loadQuestionStats()
  }
})

watch(trendRange, () => {
  if (activeTab.value === 'statistics' && props.questionnaire?.id) {
    loadQuestionStats()
  }
})

// 当问卷变化时重新加载
watch(() => props.questionnaire?.id, (newId) => {
  if (newId) {
    // 重置统计数据
    questionStats.value = null
    if (activeTab.value === 'statistics') {
    loadQuestionStats()
    }
  }
})

watch(questionStats, () => {
  resetTextPages()
})

// ===== 计算属性 =====
// V45: 使用筛选后的提交记录
const completedSubmissions = computed(() =>
  filteredSubmissions.value.filter(s => s.status === 'completed')
)

// V46: 是否有提交数据 - 优先使用 props 中的数据
const hasSubmissions = computed(() =>
  props.submissions.length > 0 ||
  completedSubmissions.value.length > 0 ||
  (questionStats.value?.total_submissions ?? 0) > 0
)

// V46: 实际提交人数 - 优先使用 props 数据
const actualSubmissionCount = computed(() => {
  // 优先使用 API 返回的数据
  if (questionStats.value?.total_submissions && questionStats.value.total_submissions > 0) {
    return questionStats.value.total_submissions
  }
  // 回退到 props 中的提交记录数量
  return completedSubmissions.value.length || props.submissions.length
})

const totalRecordCount = computed(() =>
  props.submissions.length || actualSubmissionCount.value
)

const completionRateDisplay = computed(() => {
  if (totalRecordCount.value > 0) {
    return Math.round(actualSubmissionCount.value / totalRecordCount.value * 100)
  }
  return actualSubmissionCount.value > 0 ? (questionStats.value?.completion_rate ?? 100) : 0
})

const averageScore = computed(() => {
  const scores = completedSubmissions.value
    .filter(s => s.total_score !== null && s.total_score !== undefined)
    .map(s => s.total_score!)

  if (scores.length === 0) return 0
  return Math.round(scores.reduce((a, b) => a + b, 0) / scores.length * 10) / 10
})

const scoreSummary = computed(() => questionStats.value?.score_summary ?? null)
const hasScoreSummary = computed(() =>
  Boolean(scoreSummary.value && (scoreSummary.value.scored_submission_count ?? 0) > 0)
)
const scoringConfig = computed(() => (props.questionnaire as any)?.scoring_config || {})
const scoringDisplayConfig = computed(() => buildScoringDisplayConfig({
  purpose: props.questionnaire?.purpose,
  scoringConfig: scoringConfig.value,
}))

const formatScoreValue = (value: number | null | undefined) => {
  if (value === null || value === undefined) return '-'
  return Number.isInteger(value) ? String(value) : value.toFixed(1)
}

const scoredSubmissionCount = computed(() => {
  if (scoreSummary.value?.scored_submission_count !== undefined) {
    return scoreSummary.value.scored_submission_count
  }
  if (questionStats.value?.scored_submission_count !== undefined) {
    return questionStats.value.scored_submission_count
  }
  return completedSubmissions.value.filter(s => s.total_score !== null && s.total_score !== undefined).length
})

const averageScoreDisplay = computed(() => (
  hasScoreSummary.value ? scoreSummary.value?.average_score ?? null : null
))

const scoreMaxDisplay = computed(() => scoreSummary.value?.max_score ?? 100)

const scoreCompletionRate = computed(() => {
  if (actualSubmissionCount.value === 0) return 0
  return Math.round(scoredSubmissionCount.value / actualSubmissionCount.value * 100)
})

const gradeDistribution = computed(() => {
  const dist = { A: 0, B: 0, C: 0, D: 0 }
  const summaryDist = scoreSummary.value?.grade_distribution
  if (summaryDist) {
    return {
      A: summaryDist.A || 0,
      B: summaryDist.B || 0,
      C: summaryDist.C || 0,
      D: summaryDist.D || 0,
    }
  }
  if (isScored.value && !hasScoreSummary.value) return dist

  const apiDist = questionStats.value?.grade_distribution
  if (apiDist) {
    return {
      A: apiDist.A || 0,
      B: apiDist.B || 0,
      C: apiDist.C || 0,
      D: apiDist.D || 0,
    }
  }
  return dist
})

const distributionRows = computed(() =>
  getDistributionRows(scoringConfig.value, gradeDistribution.value, props.questionnaire?.purpose)
)

const getGradeCount = (grade: string) => {
  const key = grade.toUpperCase() as keyof typeof gradeDistribution.value
  return gradeDistribution.value[key] || 0
}

const getGradePercent = (grade: string) => {
  const total = scoredSubmissionCount.value
  if (total === 0) return 0
  return getGradeCount(grade) / total * 100
}

const getGradePercentLabel = (grade: string) => Math.round(getGradePercent(grade))

// ⭐ V42: 判断问卷类型
const isScored = computed(() => {
  return (props.questionnaire as any)?.category === 'scored' ||
         (props.questionnaire as any)?.custom_type === 'scored'
})

const scoreStatus = computed(() => {
  if (!isScored.value) return 'not_scored'
  if (questionStats.value?.score_status) return questionStats.value.score_status
  if (hasScoreSummary.value) return 'scored'
  return actualSubmissionCount.value > 0 ? 'pending_recalculation' : 'no_submissions'
})

const shouldShowScoreNotice = computed(() =>
  isScored.value && ['pending_recalculation', 'partially_scored'].includes(scoreStatus.value)
)

const scoreNoticeTitle = computed(() =>
  scoreStatus.value === 'partially_scored' ? '部分答卷尚未计分' : '历史答卷尚未计分'
)

const scoreNoticeMessage = computed(() => {
  const count = questionStats.value?.unscored_submission_count ?? actualSubmissionCount.value
  if (scoreStatus.value === 'partially_scored') {
    return `还有 ${count} 份完成答卷未生成分数，重算后平均分、${scoringDisplayConfig.value.rateLabel}和${scoringDisplayConfig.value.distributionTitle}会按全部已计分答卷更新。`
  }
  return `已启用评分配置，但 ${count} 份完成答卷尚未生成分数。请重算历史得分后查看平均分、${scoringDisplayConfig.value.rateLabel}和${scoringDisplayConfig.value.distributionTitle}。`
})

// ⭐ V43: 题目分析分页计算
const paginatedQuestions = computed(() => {
  if (!questionStats.value?.questions) return []
  const start = (questionCurrentPage.value - 1) * questionPageSize
  return questionStats.value.questions.slice(start, start + questionPageSize)
})

const questionTotalPages = computed(() => {
  if (!questionStats.value?.questions) return 0
  return Math.ceil(questionStats.value.questions.length / questionPageSize)
})

// ⭐ V43: 更有意义的统计指标
const highScoreRate = computed<number | null>(() => {
  if (!hasScoreSummary.value) return null
  if (scoreSummary.value?.high_score_rate !== null && scoreSummary.value?.high_score_rate !== undefined) {
    return Math.round(scoreSummary.value.high_score_rate)
  }
  const highCount = gradeDistribution.value.A + gradeDistribution.value.B
  const total = scoredSubmissionCount.value
  if (total === 0) return null
  return Math.round((highCount / total) * 100)
})

const highScoreRateLabel = computed(() =>
  highScoreRate.value === null ? '-' : `${highScoreRate.value}%`
)

const {
  questionChartSetOptionOpts,
  normalizePercentage,
  getQuestionResponseText,
  getQuestionOptionColor,
  getQuestionChartHeight,
  getQuestionVisualMode,
  getQuestionVisualLabel,
  getQuestionVisualOption,
  getQuestionChartMode,
  setQuestionChartMode,
  getOptionSortMode,
  setOptionSortMode,
  getSortedQuestionOptions,
  getQuestionExportOptionWidth,
  getQuestionExportChartKey,
} = useQuestionVisuals()

const {
  trendChartWidth,
  trendSvgHeight,
  trendLabelY,
  trendContainerRef,
  trendTooltip,
  trendSeries,
  trendRangeLabel,
  trendPoints,
  trendLabelPoints,
  trendLinePath,
  trendAreaPath,
  getTrendBarHeight,
  formatTrendDate,
  showTrendTooltip,
  moveTrendTooltip,
  hideTrendTooltip,
} = useTrendChart({
  trendRange,
  questionStats,
  completedSubmissions,
})

const {
  getGroupKey,
  getGroupDisplayName,
  getGroupInitial,
  getGroupPage,
  setGroupPage,
  getGroupTotalPages,
  getGroupSubmissions,
  getGroupPendingCount,
  changeGroupPage,
  changeGroupListPage,
  groupedSubmissions,
  groupListTotalPages,
  paginatedGroupedSubmissions,
  visibleGroupKeys,
  areVisibleGroupsExpanded,
} = useGroupedSubmissions(filteredSubmissions, expandedCandidates)

// ===== 方法 =====
const close = () => {
  emit('close')
}

const handleDistribute = () => {
  if (props.questionnaire) {
    emit('distribute', props.questionnaire)
  }
}

const selectSubmission = (sub: Submission) => {
  selectedSubmission.value = sub
  emit('view-submission', sub)
}

const handleDeleteSubmission = (sub: Submission) => {
  emit('delete-submission', sub)
}

const handleRecalculateScores = async () => {
  if (!props.questionnaire?.id || scoreRecalculating.value) return
  scoreRecalculating.value = true
  try {
    await recalculateQuestionnaireScores(props.questionnaire.id)
    await loadQuestionStats()
  } catch (error) {
    console.error('重算历史得分失败:', error)
    alert('重算历史得分失败，请稍后重试')
  } finally {
    scoreRecalculating.value = false
  }
}

// 切换候选人展开状态
const toggleCandidateExpand = (key: string) => {
  if (expandedCandidates.value.has(key)) {
    expandedCandidates.value.delete(key)
  } else {
    expandedCandidates.value.add(key)
    const group = groupedSubmissions.value.find(g => getGroupKey(g) === key)
    if (group) setGroupPage(group, 1)
  }
}

// 全部展开/收起
const toggleAllCandidates = () => {
  const keys = visibleGroupKeys.value
  if (areVisibleGroupsExpanded.value) {
    keys.forEach(key => expandedCandidates.value.delete(key))
    return
  }
  keys.forEach(key => {
    expandedCandidates.value.add(key)
    const group = groupedSubmissions.value.find(g => getGroupKey(g) === key)
    if (group) setGroupPage(group, 1)
  })
}

const formatDate = (dateStr: string | null | undefined) => {
  if (!dateStr) return '-'
  return new Date(dateStr).toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  })
}

const formatShortDate = (dateStr: string | null | undefined) => {
  if (!dateStr) return '-'
  return new Date(dateStr).toLocaleDateString('zh-CN', {
    month: 'short',
    day: 'numeric'
  })
}

// ⭐ V42: 导出功能
const getStatusLabel = (status: string) => {
  const labels: Record<string, string> = {
    'completed': '已完成',
    'in_progress': '进行中',
    'pending': '待处理'
  }
  return labels[status] || status
}

const {
  showExportModal,
  exportFormat,
  exportLoading,
  showExportSuccessToast,
  showStatsExportModal,
  statsExportFormat,
  statsExportLoading,
  renderStatsExportReport,
  statsExportReportRef,
  statsExportChartImages,
  showStatsExportToast,
  statsExportToastMessage,
  statsExportToastType,
  openExportModal,
  closeExportModal,
  executeExport,
  closeStatsExportModal,
  openStatsExportModal,
  getExportDateText,
  executeStatsExport,
} = useQuestionnaireExports({
  questionnaire: computed(() => props.questionnaire),
  submissions: computed(() => props.submissions),
  questionStats,
  loadQuestionStats,
  formatDate,
  getStatusLabel,
  actualSubmissionCount,
  averageScore,
  completedSubmissions,
  gradeDistribution,
  scoringDisplayConfig,
  distributionRows,
  isScored,
  trendRangeLabel,
  trendSeries,
  formatTrendDate,
  getTextTags,
  getTextLongAnswers,
  getTextEmptyCount,
  questionChartSetOptionOpts,
  getQuestionChartHeight,
  getQuestionVisualOption,
  getQuestionExportChartKey,
})


</script>

<template src="./QuestionnaireDetailDrawer.template.html"></template>
<style scoped>
@import './styles/questionnaire-detail-drawer.css';
</style>
