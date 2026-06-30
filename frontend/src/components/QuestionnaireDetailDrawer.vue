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
import { fetchQuestionnaireQuestionStats, type QuestionnaireQuestionStats } from '../api/assessments'
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

const averageScore = computed(() => {
  const scores = completedSubmissions.value
    .filter(s => s.total_score !== null && s.total_score !== undefined)
    .map(s => s.total_score!)

  if (scores.length === 0) return 0
  return Math.round(scores.reduce((a, b) => a + b, 0) / scores.length * 10) / 10
})

const gradeDistribution = computed(() => {
  const dist = { A: 0, B: 0, C: 0, D: 0 }
  completedSubmissions.value.forEach(s => {
    const grade = (s.grade || 'D').toUpperCase() as keyof typeof dist
    if (grade in dist) dist[grade]++
  })
  return dist
})

const getGradeCount = (grade: string) => {
  const key = grade.toUpperCase() as keyof typeof gradeDistribution.value
  return gradeDistribution.value[key] || 0
}

const getGradePercent = (grade: string) => {
  if (completedSubmissions.value.length === 0) return 0
  return getGradeCount(grade) / completedSubmissions.value.length * 100
}

const getGradePercentLabel = (grade: string) => Math.round(getGradePercent(grade))

// ⭐ V42: 判断问卷类型
const isScored = computed(() => {
  return (props.questionnaire as any)?.category === 'scored' ||
         (props.questionnaire as any)?.custom_type === 'scored'
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
const highScoreRate = computed(() => {
  // 优良率 = (A+B等级) / 总完成数
  const total = completedSubmissions.value.length
  if (total === 0) return 0
  const highCount = gradeDistribution.value.A + gradeDistribution.value.B
  return Math.round((highCount / total) * 100)
})

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

// ⭐ 按候选人分组的提交记录
interface GroupedCandidate {
  phone: string
  name: string
  submissions: Submission[]
  totalSubmissions: number
  latestSubmission: Submission | null
  completedCount: number
  __anonymousAggregate?: boolean
}

const ANONYMOUS_NAMES = new Set(['匿名', '未知', 'unknown', 'n/a', 'na', '-', '--', 'null', ''])

const isAnonymousSubmission = (name?: string, phone?: string) => {
  const safeName = (name || '').trim().toLowerCase()
  const safePhone = (phone || '').trim()
  if (safePhone) return false
  return !safeName || ANONYMOUS_NAMES.has(safeName)
}

const getGroupKey = (group: GroupedCandidate) => {
  if (group.__anonymousAggregate) return '__anonymous__'
  return group.phone || group.name || 'unknown'
}

const getGroupDisplayName = (group: GroupedCandidate) => {
  if (group.__anonymousAggregate || isAnonymousSubmission(group.name, group.phone)) {
    return `匿名填写（${group.totalSubmissions}人）`
  }
  return group.name || '未知'
}

const getGroupInitial = (group: GroupedCandidate) => {
  const name = getGroupDisplayName(group)
  return name ? name[0].toUpperCase() : 'U'
}

const getLatestSubmission = (subs: Submission[]) => {
  let latest: Submission | null = null
  subs.forEach(sub => {
    const time = sub.submitted_at || sub.started_at
    if (!time) return
    if (!latest) {
      latest = sub
      return
    }
    const latestTime = latest.submitted_at || latest.started_at
    if (latestTime && new Date(time) > new Date(latestTime)) {
      latest = sub
    }
  })
  return latest
}

const groupPageSize = 10
const groupPageMap = ref<Record<string, number>>({})
const groupListPageSize = 10
const groupListPage = ref(1)

const getGroupPage = (group: GroupedCandidate) => {
  return groupPageMap.value[getGroupKey(group)] || 1
}

const setGroupPage = (group: GroupedCandidate, page: number) => {
  groupPageMap.value = {
    ...groupPageMap.value,
    [getGroupKey(group)]: page
  }
}

const getGroupTotalPages = (group: GroupedCandidate) => {
  return Math.max(1, Math.ceil(group.submissions.length / groupPageSize))
}

const getGroupSubmissions = (group: GroupedCandidate) => {
  const page = getGroupPage(group)
  const start = (page - 1) * groupPageSize
  return group.submissions.slice(start, start + groupPageSize)
}

const getGroupPendingCount = (group: GroupedCandidate) => {
  return Math.max(0, group.totalSubmissions - group.completedCount)
}

const changeGroupPage = (group: GroupedCandidate, page: number) => {
  const totalPages = getGroupTotalPages(group)
  if (page < 1 || page > totalPages) return
  setGroupPage(group, page)
}

const changeGroupListPage = (page: number) => {
  if (page < 1 || page > groupListTotalPages.value) return
  groupListPage.value = page
}

const groupedSubmissions = computed<GroupedCandidate[]>(() => {
  const groups = new Map<string, GroupedCandidate>()

  // V45: 使用筛选后的提交记录
  const anonymousSubs = filteredSubmissions.value.filter(sub =>
    isAnonymousSubmission(sub.candidate_name, sub.candidate_phone)
  )

  if (anonymousSubs.length > 0) {
    const latest = getLatestSubmission(anonymousSubs)
    groups.set('__anonymous__', {
      phone: '',
      name: `匿名填写（${anonymousSubs.length}人）`,
      submissions: anonymousSubs,
      totalSubmissions: anonymousSubs.length,
      latestSubmission: latest,
      completedCount: anonymousSubs.filter(s => s.status === 'completed').length,
      __anonymousAggregate: true
    })
  }

  filteredSubmissions.value.forEach(sub => {
    if (isAnonymousSubmission(sub.candidate_name, sub.candidate_phone)) return
    const key = sub.candidate_phone || sub.candidate_name || 'unknown'

    if (!groups.has(key)) {
      groups.set(key, {
        phone: sub.candidate_phone || '',
        name: sub.candidate_name || '',
        submissions: [],
        totalSubmissions: 0,
        latestSubmission: null,
        completedCount: 0,
      })
    }

    const group = groups.get(key)!
    group.submissions.push(sub)
    group.totalSubmissions++
    if (sub.status === 'completed') group.completedCount++

    // 更新最新提交
    if (!group.latestSubmission ||
        (sub.submitted_at && group.latestSubmission.submitted_at &&
         new Date(sub.submitted_at) > new Date(group.latestSubmission.submitted_at))) {
      group.latestSubmission = sub
    }
  })

  // 按最新提交时间排序
  return Array.from(groups.values()).sort((a, b) => {
    const timeA = a.latestSubmission?.submitted_at ? new Date(a.latestSubmission.submitted_at).getTime() : 0
    const timeB = b.latestSubmission?.submitted_at ? new Date(b.latestSubmission.submitted_at).getTime() : 0
    return timeB - timeA
  })
})

const groupListTotalPages = computed(() =>
  Math.ceil(groupedSubmissions.value.length / groupListPageSize) || 1
)

const paginatedGroupedSubmissions = computed<GroupedCandidate[]>(() => {
  const start = (groupListPage.value - 1) * groupListPageSize
  const end = start + groupListPageSize
  return groupedSubmissions.value.slice(start, end)
})

const visibleGroupKeys = computed(() =>
  paginatedGroupedSubmissions.value.map(group => getGroupKey(group))
)

const areVisibleGroupsExpanded = computed(() => {
  if (visibleGroupKeys.value.length === 0) return false
  return visibleGroupKeys.value.every(key => expandedCandidates.value.has(key))
})

watch([filterYear, filterMonth], () => {
  groupListPage.value = 1
})

watch(groupListTotalPages, (total) => {
  if (groupListPage.value > total) {
    groupListPage.value = total
  }
})

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
