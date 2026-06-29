<script setup lang="ts">
/**
 * 问卷详情侧滑抽屉
 * 
 * 功能：
 * 1. 提交记录 Tab - 显示该问卷的所有提交记录（支持折叠/展开）
 * 2. 问卷统计 Tab - 显示统计数据（参与人数、平均分、等级分布、题目分析）
 */
import { ref, computed, watch, onMounted, onBeforeUnmount, nextTick } from 'vue'
import { init, type ECharts, type EChartsOption, type SetOptionOpts } from 'echarts/core'
import EChartContainer from './EChartContainer.vue'
import * as XLSX from 'xlsx'
import type { Questionnaire, Submission, QuestionStat, QuestionOptionStat, TextSummary, TextAnswerGroup } from '../api/assessments'
import { fetchQuestionnaireQuestionStats, type QuestionnaireQuestionStats } from '../api/assessments'

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

// ⭐ V42: 导出功能状态
const showExportModal = ref(false)
const exportFormat = ref<'csv' | 'excel'>('csv')
const exportLoading = ref(false)
const showExportSuccessToast = ref(false)

// 问卷统计导出
const showStatsExportModal = ref(false)
const statsExportFormat = ref<'pdf' | 'png' | 'excel'>('pdf')
const statsExportLoading = ref(false)
const renderStatsExportReport = ref(false)
const statsExportReportRef = ref<HTMLElement | null>(null)
const statsExportChartImages = ref<Record<string, string>>({})
const showStatsExportToast = ref(false)
const statsExportToastMessage = ref('')
const statsExportToastType = ref<'success' | 'error'>('success')

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
const textAnswerPageSize = 10
const textAnswerPageMap = ref<Record<string, number>>({})

const getTextSummary = (question: QuestionStat): TextSummary => {
  return question.text_summary || {}
}

const getTextTags = (question: QuestionStat): TextAnswerGroup[] => {
  return getTextSummary(question).tags || []
}

const getTextLongAnswers = (question: QuestionStat): TextAnswerGroup[] => {
  return getTextSummary(question).long_answers || []
}

const getTextEmptyCount = (question: QuestionStat): number => {
  return getTextSummary(question).empty_count || 0
}

const getTextPage = (question: QuestionStat): number => {
  return textAnswerPageMap.value[question.id] || 1
}

const setTextPage = (question: QuestionStat, page: number) => {
  const totalPages = getTextTotalPages(question)
  const nextPage = Math.min(Math.max(page, 1), totalPages)
  textAnswerPageMap.value = {
    ...textAnswerPageMap.value,
    [question.id]: nextPage
  }
}

const getTextTotalPages = (question: QuestionStat): number => {
  const total = getTextLongAnswers(question).length
  return Math.max(1, Math.ceil(total / textAnswerPageSize))
}

const getTextLongAnswerPage = (question: QuestionStat): TextAnswerGroup[] => {
  const page = getTextPage(question)
  const start = (page - 1) * textAnswerPageSize
  return getTextLongAnswers(question).slice(start, start + textAnswerPageSize)
}

const hasTextSummary = (question: QuestionStat): boolean => {
  const summary = getTextSummary(question)
  return Boolean(
    (summary.tags && summary.tags.length > 0) ||
    (summary.long_answers && summary.long_answers.length > 0) ||
    (summary.empty_count && summary.empty_count > 0)
  )
}

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
  textAnswerPageMap.value = {}
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

// ⭐ V42: 判断问卷类型
const isScored = computed(() => {
  return (props.questionnaire as any)?.category === 'scored' || 
         (props.questionnaire as any)?.custom_type === 'scored'
})

const isSurvey = computed(() => {
  return (props.questionnaire as any)?.category === 'survey' || 
         (props.questionnaire as any)?.custom_type === 'non_scored'
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
const responseRate = computed(() => {
  // 响应率 = 完成数 / 总分发数（如果有的话）
  const total = questionStats.value?.total_submissions || completedSubmissions.value.length
  if (total === 0) return 0
  return Math.round((completedSubmissions.value.length / total) * 100)
})

const highScoreRate = computed(() => {
  // 优良率 = (A+B等级) / 总完成数
  const total = completedSubmissions.value.length
  if (total === 0) return 0
  const highCount = gradeDistribution.value.A + gradeDistribution.value.B
  return Math.round((highCount / total) * 100)
})

// V46: 题目类型标签映射
const getQuestionTypeLabel = (type: string): string => {
  const typeMap: Record<string, string> = {
    'single': '单选',
    'radio': '单选',
    'multiple': '多选',
    'checkbox': '多选',
    'text': '文本',
    'textarea': '文本',
    'scale': '量表',
    'rating': '评分',
    'yesno': '是非',
    'choice': '选择'
  }
  return typeMap[type] || type
}

// V46: 判断是否为文本题
const isTextQuestion = (type: string): boolean => {
  return ['text', 'textarea'].includes(type)
}

const isSingleChoiceQuestion = (type: string): boolean => {
  return ['single', 'radio', 'yesno', 'choice'].includes(type)
}

const isMultipleChoiceQuestion = (type: string): boolean => {
  return ['multiple', 'checkbox'].includes(type)
}

const isScaleQuestion = (type: string): boolean => {
  return ['scale', 'rating'].includes(type)
}

const normalizePercentage = (percentage?: number): number => {
  const value = Number(percentage || 0)
  if (Number.isNaN(value)) return 0
  return Math.min(100, Math.max(0, Math.round(value * 10) / 10))
}

const getQuestionResponseText = (question: QuestionStat): string => {
  const answerCount = Number(question.total_answers || 0)
  const selectionCount = Number(question.total_selections || 0)

  if (isMultipleChoiceQuestion(question.type) && selectionCount > answerCount) {
    return `${answerCount} 份回答 · ${selectionCount} 次选择`
  }

  return `${answerCount} 份回答`
}

const truncateChartLabel = (value: string, max = 10) => {
  const text = String(value || '')
  return text.length > max ? `${text.slice(0, max)}...` : text
}

const QUESTION_CHART_COLORS = ['#38a3d8', '#60d5d8', '#ffdc5a', '#ff9b78', '#8b5cf6', '#22c55e', '#f97316', '#64748b']

const getQuestionOptionColor = (index: number): string => {
  return QUESTION_CHART_COLORS[index % QUESTION_CHART_COLORS.length]
}

const getQuestionChartHeight = (question: QuestionStat): number => {
  if (isSingleChoiceQuestion(question.type)) return 210
  if (isScaleQuestion(question.type)) return 230
  if (isMultipleChoiceQuestion(question.type) && question.options.length <= 8) return 230
  const extra = Math.max(0, (question.options?.length || 0) - 6) * 14
  return Math.min(300, 220 + extra)
}

const getQuestionChartOption = (question: QuestionStat): EChartsOption => {
  const options = question.options || []
  return {
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    grid: { left: '3%', right: '4%', top: '6%', bottom: '6%', containLabel: true },
    xAxis: {
      type: 'value',
      minInterval: 1,
      axisLabel: { color: '#94a3b8' },
      splitLine: { lineStyle: { color: '#f1f5f9' } },
    },
    yAxis: {
      type: 'category',
      data: options.map(opt => opt.text),
      axisLabel: { color: '#64748b', width: 140, overflow: 'truncate' },
    },
    series: [
      {
        type: 'bar',
        data: options.map((opt, index) => ({
          value: opt.count,
          itemStyle: { color: getQuestionOptionColor(index) },
        })),
        barWidth: 14,
        label: { show: true, position: 'right', color: '#7c3aed', formatter: '{c}人' },
      },
    ],
  }
}

const getQuestionPieOption = (question: QuestionStat): EChartsOption => {
  const options = question.options || []
  return {
    tooltip: { trigger: 'item', formatter: '{b}: {c}人 ({d}%)' },
    legend: { show: false },
    series: [
      {
        type: 'pie',
        radius: ['48%', '72%'],
        center: ['50%', '50%'],
        avoidLabelOverlap: true,
        label: { show: false },
        labelLine: { show: false },
        emphasis: {
          label: { show: false },
          scaleSize: 6,
        },
        data: options.map((opt, index) => ({
          name: opt.text,
          value: opt.count,
          itemStyle: { color: getQuestionOptionColor(index) },
        })),
      },
    ],
  }
}

const getQuestionRadarOption = (question: QuestionStat): EChartsOption => {
  const options = question.options || []
  const maxCount = Math.max(1, ...options.map(opt => opt.count))
  return {
    tooltip: { trigger: 'item' },
    radar: {
      radius: '68%',
      center: ['50%', '52%'],
      splitNumber: 4,
      axisName: {
        color: '#64748b',
        fontSize: 11,
        formatter: (value: string) => truncateChartLabel(value, 8),
      },
      splitLine: { lineStyle: { color: '#e2e8f0' } },
      splitArea: { areaStyle: { color: ['#ffffff', '#f8fafc'] } },
      axisLine: { lineStyle: { color: '#e2e8f0' } },
      indicator: options.map(opt => ({
        name: opt.text,
        max: maxCount,
      })),
    },
    series: [
      {
        type: 'radar',
        data: [{
          value: options.map(opt => opt.count),
          name: '选择人数',
          areaStyle: { color: 'rgba(124, 58, 237, 0.18)' },
          lineStyle: { color: '#7c3aed', width: 2 },
          itemStyle: { color: '#7c3aed' },
        }],
      },
    ],
  }
}

const getQuestionColumnOption = (question: QuestionStat): EChartsOption => {
  const options = question.options || []
  return {
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    grid: { left: '8%', right: '5%', top: '10%', bottom: '20%', containLabel: true },
    xAxis: {
      type: 'category',
      data: options.map(opt => opt.text),
      axisLabel: {
        color: '#64748b',
        interval: 0,
        rotate: options.length > 4 ? 24 : 0,
        formatter: (value: string) => truncateChartLabel(value, 6),
      },
      axisLine: { lineStyle: { color: '#e2e8f0' } },
    },
    yAxis: {
      type: 'value',
      minInterval: 1,
      axisLabel: { color: '#94a3b8' },
      splitLine: { lineStyle: { color: '#eef2f7' } },
    },
    series: [
      {
        type: 'bar',
        data: options.map((opt, index) => ({
          value: opt.count,
          itemStyle: { color: getQuestionOptionColor(index) },
        })),
        barMaxWidth: 34,
        label: { show: true, position: 'top', color: '#0284c7', formatter: '{c}' },
      },
    ],
  }
}

const getQuestionVisualMode = (question: QuestionStat): 'pie' | 'bar' | 'radar' | 'column' => {
  if (isSingleChoiceQuestion(question.type)) {
    return getQuestionChartMode(question)
  }
  if (isScaleQuestion(question.type)) {
    return 'column'
  }
  if (isMultipleChoiceQuestion(question.type) && question.options.length >= 3 && question.options.length <= 8) {
    return 'radar'
  }
  return 'bar'
}

const getQuestionVisualLabel = (question: QuestionStat): string => {
  const mode = getQuestionVisualMode(question)
  const labelMap = {
    pie: '环形占比',
    bar: '横向排行',
    radar: '雷达对比',
    column: '柱状分布',
  }
  return labelMap[mode]
}

const getQuestionVisualOption = (question: QuestionStat): EChartsOption => {
  const mode = getQuestionVisualMode(question)
  if (mode === 'pie') return getQuestionPieOption(question)
  if (mode === 'radar') return getQuestionRadarOption(question)
  if (mode === 'column') return getQuestionColumnOption(question)
  return getQuestionChartOption(question)
}

const questionChartSetOptionOpts: SetOptionOpts = {
  notMerge: true,
}

const questionChartModeMap = ref<Record<string, 'pie' | 'bar'>>({})
type OptionSortMode = 'default' | 'asc' | 'desc'
const optionSortModeMap = ref<Record<string, OptionSortMode>>({})

const getQuestionKey = (question: QuestionStat): string => String(question.id || question.index)

const getQuestionChartMode = (question: QuestionStat): 'pie' | 'bar' => {
  return questionChartModeMap.value[question.id] || 'pie'
}

const setQuestionChartMode = (question: QuestionStat, mode: 'pie' | 'bar') => {
  questionChartModeMap.value = {
    ...questionChartModeMap.value,
    [question.id]: mode
  }
}

const getOptionSortMode = (question: QuestionStat): OptionSortMode => {
  return optionSortModeMap.value[getQuestionKey(question)] || 'default'
}

const setOptionSortMode = (question: QuestionStat, mode: OptionSortMode) => {
  const questionKey = getQuestionKey(question)
  const nextMap = { ...optionSortModeMap.value }

  if (mode === 'default') {
    delete nextMap[questionKey]
  } else {
    nextMap[questionKey] = mode
  }

  optionSortModeMap.value = nextMap
}

const getSortedQuestionOptions = (question: QuestionStat): QuestionOptionStat[] => {
  const options = question.options || []
  const mode = getOptionSortMode(question)

  if (mode === 'default') return options

  return [...options].sort((a, b) => {
    const diff = (a.count || 0) - (b.count || 0)
    if (diff !== 0) return mode === 'asc' ? diff : -diff

    const aIndex = a.index ?? options.indexOf(a)
    const bIndex = b.index ?? options.indexOf(b)
    return aIndex - bIndex
  })
}

const getQuestionExportOptionWidth = (question: QuestionStat, option: QuestionOptionStat): number => {
  const percentage = normalizePercentage(option.percentage)
  if (percentage > 0) return percentage

  const maxCount = Math.max(1, ...(question.options || []).map(opt => opt.count || 0))
  return Math.min(100, Math.round(((option.count || 0) / maxCount) * 1000) / 10)
}

const getQuestionExportChartKey = (question: QuestionStat) => `${question.id || question.index}-${getQuestionVisualMode(question)}`

const disposeChartSafely = (chart: ECharts | null) => {
  if (!chart) return
  try {
    chart.dispose()
  } catch (error) {
    console.warn('销毁统计导出图表失败:', error)
  }
}

const pad2 = (value: number | string) => String(value).padStart(2, '0')
const trendChartWidth = ref(600)
const trendChartHeight = 100
const trendChartPaddingX = 0
const trendChartPaddingY = 10
const trendLabelOffset = 18
const trendSvgHeight = trendChartHeight + trendLabelOffset
const trendBaselineY = trendChartHeight - trendChartPaddingY
const trendLabelY = trendChartHeight + 12

const toDateKey = (date: Date) =>
  `${date.getFullYear()}-${pad2(date.getMonth() + 1)}-${pad2(date.getDate())}`

const parseTrendDateKey = (dateStr: string, dateMap: Map<string, string>) => {
  if (!dateStr) return null
  if (dateStr.includes('/')) {
    const [month, day] = dateStr.split('/')
    if (!month || !day) return null
    const key = `${pad2(month)}/${pad2(day)}`
    return dateMap.get(key) || null
  }
  if (/^\d{4}-\d{2}-\d{2}$/.test(dateStr)) return dateStr
  const parsed = new Date(dateStr)
  if (Number.isNaN(parsed.getTime())) return null
  return toDateKey(parsed)
}

const buildWeekDays = (baseDate: Date) => {
  const dayOfWeek = baseDate.getDay()
  const diffToMonday = (dayOfWeek + 6) % 7
  const monday = new Date(baseDate)
  monday.setDate(baseDate.getDate() - diffToMonday)
  monday.setHours(0, 0, 0, 0)
  return Array.from({ length: 7 }, (_, idx) => {
    const date = new Date(monday)
    date.setDate(monday.getDate() + idx)
    return date
  })
}

const buildMonthDays = (baseDate: Date) => {
  const start = new Date(baseDate)
  start.setDate(baseDate.getDate() - 29)
  start.setHours(0, 0, 0, 0)
  return Array.from({ length: 30 }, (_, idx) => {
    const date = new Date(start)
    date.setDate(start.getDate() + idx)
    return date
  })
}

const getRangeDays = () => {
  const today = new Date()
  return trendRange.value === 'month' ? buildMonthDays(today) : buildWeekDays(today)
}

const buildTrendSeriesFromApi = () => {
  const raw = questionStats.value?.daily_trend || []
  const rangeDays = getRangeDays()
  const dateMap = new Map<string, string>()
  rangeDays.forEach(date => {
    dateMap.set(`${pad2(date.getMonth() + 1)}/${pad2(date.getDate())}`, toDateKey(date))
  })
  const map = new Map<string, number>()
  raw.forEach(day => {
    const key = parseTrendDateKey(day.date, dateMap)
    if (key) map.set(key, day.count ?? 0)
  })
  return rangeDays.map(date => {
    const key = toDateKey(date)
    return {
      date: key,
      count: map.get(key) || 0
    }
  })
}

const buildTrendSeriesFromSubmissions = () => {
  const rangeDays = getRangeDays()
  const map = new Map<string, number>()
  completedSubmissions.value.forEach(sub => {
    if (!sub.submitted_at) return
    const parsed = new Date(sub.submitted_at)
    if (Number.isNaN(parsed.getTime())) return
    const dateKey = toDateKey(parsed)
    map.set(dateKey, (map.get(dateKey) || 0) + 1)
  })
  return rangeDays.map(date => {
    const key = toDateKey(date)
    return {
      date: key,
      count: map.get(key) || 0
    }
  })
}

const trendSeries = computed(() => {
  const apiSeries = buildTrendSeriesFromApi()
  const localSeries = buildTrendSeriesFromSubmissions()
  const apiHasCounts = apiSeries.some(day => day.count > 0)
  const localHasCounts = localSeries.some(day => day.count > 0)

  if (trendRange.value === 'month') {
    if (!apiHasCounts && localHasCounts) return localSeries
    return apiSeries
  }

  if (!apiHasCounts && localHasCounts) return localSeries
  const latestSubmission = completedSubmissions.value
    .map(sub => sub.submitted_at)
    .filter(Boolean)
    .map(value => new Date(value as string))
    .filter(date => !Number.isNaN(date.getTime()))
    .sort((a, b) => b.getTime() - a.getTime())[0]

  if (!latestSubmission) return apiSeries
  const latestKey = toDateKey(latestSubmission)
  const apiCount = apiSeries.find(day => day.date === latestKey)?.count || 0
  const localCount = localSeries.find(day => day.date === latestKey)?.count || 0
  if (localCount > apiCount) return localSeries
  return apiSeries
})

const trendRangeLabel = computed(() => trendRange.value === 'month' ? '近一个月' : '本周')

const maxTrendCount = computed(() => {
  return Math.max(1, ...trendSeries.value.map(day => day.count))
})

const getTrendBarHeight = (count: number) => {
  if (count <= 0) return '6%'
  return `${Math.max(8, Math.round((count / maxTrendCount.value) * 100))}%`
}

// ⭐ V43: 趋势图SVG路径计算
const trendPoints = computed(() => {
  if (trendSeries.value.length === 0) return []
  const data = trendSeries.value
  const maxCount = Math.max(...data.map(d => d.count), 1)
  
  return data.map((d, i) => ({
    x: trendChartPaddingX + (i / (data.length - 1 || 1)) * (trendChartWidth.value - trendChartPaddingX * 2),
    y: trendChartHeight - trendChartPaddingY - (d.count / maxCount) * (trendChartHeight - trendChartPaddingY * 2),
    count: d.count,
    date: d.date
  }))
})

const trendLabelPoints = computed(() => {
  if (trendPoints.value.length === 0) return []
  const labelPoints = trendRange.value === 'week'
    ? trendPoints.value
    : (() => {
        const interval = Math.ceil(trendPoints.value.length / 6)
        return trendPoints.value.filter((_, idx) => idx % interval === 0 || idx === trendPoints.value.length - 1)
      })()
  return labelPoints.map((point, idx) => ({
    ...point,
    anchor: idx === 0 ? 'start' : (idx === labelPoints.length - 1 ? 'end' : 'middle')
  }))
})

const trendContainerRef = ref<HTMLElement | null>(null)
const trendResizeObserver = ref<ResizeObserver | null>(null)

const updateTrendWidth = () => {
  const width = trendContainerRef.value?.clientWidth || 0
  if (width > 0) {
    trendChartWidth.value = width
  }
}

onMounted(() => {
  updateTrendWidth()
  if (typeof ResizeObserver !== 'undefined' && trendContainerRef.value) {
    trendResizeObserver.value = new ResizeObserver((entries) => {
      const entry = entries[0]
      if (!entry) return
      const width = Math.max(0, Math.floor(entry.contentRect.width))
      if (width > 0) {
        trendChartWidth.value = width
      }
    })
    trendResizeObserver.value.observe(trendContainerRef.value)
  } else if (typeof window !== 'undefined') {
    window.addEventListener('resize', updateTrendWidth)
  }
})

watch(trendContainerRef, (el, prev) => {
  if (trendResizeObserver.value && prev) {
    trendResizeObserver.value.unobserve(prev)
  }
  if (el) {
    updateTrendWidth()
    if (typeof ResizeObserver !== 'undefined') {
      if (!trendResizeObserver.value) {
        trendResizeObserver.value = new ResizeObserver((entries) => {
          const entry = entries[0]
          if (!entry) return
          const width = Math.max(0, Math.floor(entry.contentRect.width))
          if (width > 0) {
            trendChartWidth.value = width
          }
        })
      }
      trendResizeObserver.value.observe(el)
    }
  }
})

onBeforeUnmount(() => {
  if (trendResizeObserver.value && trendContainerRef.value) {
    trendResizeObserver.value.unobserve(trendContainerRef.value)
    trendResizeObserver.value.disconnect()
  }
  if (typeof window !== 'undefined') {
    window.removeEventListener('resize', updateTrendWidth)
  }
})
const trendTooltip = ref({ visible: false, x: 0, y: 0, text: '' })

const updateTrendTooltipPosition = (event: MouseEvent) => {
  const container = trendContainerRef.value
  if (!container) return
  const rect = container.getBoundingClientRect()
  const rawX = event.clientX - rect.left
  const rawY = event.clientY - rect.top
  const x = Math.max(12, Math.min(rawX, rect.width - 12))
  const y = Math.max(12, rawY - 12)
  trendTooltip.value.x = x
  trendTooltip.value.y = y
}

const showTrendTooltip = (event: MouseEvent, point: { date: string; count: number }) => {
  trendTooltip.value.visible = true
  trendTooltip.value.text = `${formatTrendDate(point.date)}：${point.count}人`
  updateTrendTooltipPosition(event)
}

const moveTrendTooltip = (event: MouseEvent) => {
  if (!trendTooltip.value.visible) return
  updateTrendTooltipPosition(event)
}

const hideTrendTooltip = () => {
  trendTooltip.value.visible = false
}

const trendLinePath = computed(() => {
  if (trendPoints.value.length === 0) return ''
  return trendPoints.value.map((p, i) => 
    `${i === 0 ? 'M' : 'L'} ${p.x} ${p.y}`
  ).join(' ')
})

const trendAreaPath = computed(() => {
  if (trendPoints.value.length === 0) return ''
  const points = trendPoints.value
  const firstX = points[0]?.x || 0
  const lastX = points[points.length - 1]?.x || trendChartWidth.value
  return `${trendLinePath.value} L ${lastX} ${trendBaselineY} L ${firstX} ${trendBaselineY} Z`
})

// 格式化趋势日期
const formatTrendDate = (dateStr: string) => {
  if (!dateStr) return ''
  // 输入格式如 "12/02" 或 "2025-12-02"
  if (dateStr.includes('/')) {
    return dateStr
  }
  if (/^\d{4}-\d{2}-\d{2}$/.test(dateStr)) {
    const [, month, day] = dateStr.split('-')
    return `${Number(month)}/${day}`
  }
  const date = new Date(dateStr)
  if (Number.isNaN(date.getTime())) return dateStr
  return `${date.getMonth() + 1}/${String(date.getDate()).padStart(2, '0')}`
}

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

const openExportModal = () => {
  if (props.submissions.length === 0) {
    showExportSuccessToast.value = true
    setTimeout(() => { showExportSuccessToast.value = false }, 2000)
    return
  }
  showExportModal.value = true
}

const closeExportModal = () => {
  showExportModal.value = false
}

const getQuestionTypeText = (type: string) => {
  const map: Record<string, string> = {
    single: '单选',
    radio: '单选',
    multiple: '多选',
    checkbox: '多选',
    text: '文本',
    textarea: '文本',
    scale: '量表',
    rating: '评分',
    yesno: '是非',
    choice: '选择',
  }
  return map[type] || type
}

const buildQuestionStatsRows = () => {
  const rows: Array<Record<string, string | number>> = []
  if (!questionStats.value?.questions?.length) return rows

  questionStats.value.questions.forEach((q) => {
    const questionLabel = `Q${q.index}`
    const questionType = getQuestionTypeText(q.type)

    if (q.options?.length) {
      q.options.forEach((opt) => {
        rows.push({
          '题号': questionLabel,
          '题目': q.text || '',
          '题型': questionType,
          '选项/答案': opt.text || '',
          '人数': opt.count ?? 0,
          '占比': `${opt.percentage ?? 0}%`,
        })
      })
      return
    }

    // 文本题：优先导出标签聚合，再导出长答案聚合
    const tags = q.text_summary?.tags || []
    const longAnswers = q.text_summary?.long_answers || []
    if (tags.length || longAnswers.length) {
      tags.forEach((item) => {
        rows.push({
          '题号': questionLabel,
          '题目': q.text || '',
          '题型': questionType,
          '选项/答案': `[标签] ${item.text || ''}`,
          '人数': item.count ?? 0,
          '占比': '',
        })
      })
      longAnswers.forEach((item) => {
        rows.push({
          '题号': questionLabel,
          '题目': q.text || '',
          '题型': questionType,
          '选项/答案': `[文本] ${item.text || ''}`,
          '人数': item.count ?? 0,
          '占比': '',
        })
      })
      return
    }

    rows.push({
      '题号': questionLabel,
      '题目': q.text || '',
      '题型': questionType,
      '选项/答案': '(无选项统计)',
      '人数': q.total_answers ?? 0,
      '占比': '',
    })
  })

  return rows
}

const executeExport = async () => {
  exportLoading.value = true
  
  try {
    // 确保导出时拿到最新题目统计
    if (!questionStats.value && props.questionnaire?.id) {
      await loadQuestionStats()
    }

    const data = props.submissions.map(r => ({
      '姓名': r.candidate_name || '',
      '联系方式': r.candidate_phone || '',
      '问卷': props.questionnaire?.name || '',
      '得分': r.total_score !== null && r.total_score !== undefined ? r.total_score : '',
      '等级': r.grade || '',
      '状态': getStatusLabel(r.status),
      '提交时间': formatDate(r.submitted_at)
    }))
    
    const headers = Object.keys(data[0] || {})
    const questionStatsRows = buildQuestionStatsRows()
    const questionStatsHeaders = Object.keys(questionStatsRows[0] || {})
    const dateStr = new Date().toISOString().slice(0, 10)
    const fileName = `${props.questionnaire?.name || '问卷'}_提交记录_${dateStr}`
    
    if (exportFormat.value === 'csv') {
      // CSV导出
      const lines = [
        headers.join(','),
        ...data.map(row => headers.map(h => `"${(row as any)[h] || ''}"`).join(','))
      ]
      
      if (questionStatsRows.length > 0) {
        lines.push('')
        lines.push('题目统计数据')
        lines.push(questionStatsHeaders.join(','))
        lines.push(
          ...questionStatsRows.map(row => questionStatsHeaders.map(h => `"${(row as any)[h] || ''}"`).join(','))
        )
      }

      const csvContent = lines.join('\n')
      
      const blob = new Blob(['\uFEFF' + csvContent], { type: 'text/csv;charset=utf-8;' })
      const link = document.createElement('a')
      link.href = URL.createObjectURL(blob)
      link.download = `${fileName}.csv`
      link.click()
    } else {
      // 真正的 .xlsx 导出，避免移动端/WPS将内容识别为源码
      const workbook = XLSX.utils.book_new()
      const detailSheet = XLSX.utils.json_to_sheet(data)
      XLSX.utils.book_append_sheet(workbook, detailSheet, '提交明细')

      if (questionStatsRows.length > 0) {
        const statsSheet = XLSX.utils.json_to_sheet(questionStatsRows)
        XLSX.utils.book_append_sheet(workbook, statsSheet, '题目统计')
      }

      const excelBuffer = XLSX.write(workbook, {
        bookType: 'xlsx',
        type: 'array'
      })
      const blob = new Blob([excelBuffer], {
        type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
      })
      const link = document.createElement('a')
      link.href = URL.createObjectURL(blob)
      link.download = `${fileName}.xlsx`
      link.click()
    }
    
    // 关闭弹窗并显示成功提示
    showExportModal.value = false
    showExportSuccessToast.value = true
    setTimeout(() => { showExportSuccessToast.value = false }, 3000)
    
  } catch (error) {
    console.error('导出失败:', error)
  } finally {
    exportLoading.value = false
  }
}

const showStatsExportMessage = (message: string, type: 'success' | 'error' = 'success') => {
  statsExportToastMessage.value = message
  statsExportToastType.value = type
  showStatsExportToast.value = true
  setTimeout(() => {
    showStatsExportToast.value = false
  }, 3000)
}

const hasStatsExportData = () => {
  return Boolean(
    questionStats.value &&
    (questionStats.value.total_submissions > 0 || questionStats.value.questions.length > 0)
  )
}

const closeStatsExportModal = () => {
  if (statsExportLoading.value) return
  showStatsExportModal.value = false
}

const openStatsExportModal = async () => {
  if (!questionStats.value && props.questionnaire?.id) {
    await loadQuestionStats()
  }

  if (!hasStatsExportData()) {
    showStatsExportMessage('暂无可导出的统计数据', 'error')
    return
  }

  showStatsExportModal.value = true
}

const delay = (ms: number) => new Promise(resolve => setTimeout(resolve, ms))

const getExportDateText = () => {
  return new Date().toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  })
}

const getExportDateKey = () => {
  const date = new Date()
  return `${date.getFullYear()}${pad2(date.getMonth() + 1)}${pad2(date.getDate())}`
}

const sanitizeFileName = (name: string) => {
  return name.replace(/[\\/:*?"<>|]/g, '_').replace(/\s+/g, '_').slice(0, 80)
}

const getStatsExportBaseName = () => {
  return sanitizeFileName(`${props.questionnaire?.name || '问卷'}_统计报告_${getExportDateKey()}`)
}

const downloadHref = (href: string, fileName: string) => {
  const link = document.createElement('a')
  link.href = href
  link.download = fileName
  document.body.appendChild(link)
  link.click()
  link.remove()
}

const downloadBlob = (blob: Blob, fileName: string) => {
  const url = URL.createObjectURL(blob)
  downloadHref(url, fileName)
  setTimeout(() => URL.revokeObjectURL(url), 1000)
}

const getStatsOverviewRows = () => {
  return [
    { '指标': '问卷名称', '数值': props.questionnaire?.name || questionStats.value?.questionnaire_name || '' },
    { '指标': '导出时间', '数值': getExportDateText() },
    { '指标': '参与人数', '数值': actualSubmissionCount.value },
    { '指标': '完成率', '数值': `${actualSubmissionCount.value > 0 ? (questionStats.value?.completion_rate ?? 100) : 0}%` },
    { '指标': '题目数', '数值': questionStats.value?.questions.length || 0 },
    { '指标': '平均分', '数值': (questionStats.value?.average_score ?? averageScore.value) || '' },
    { '指标': '平均用时', '数值': questionStats.value?.average_duration_minutes ? `${questionStats.value.average_duration_minutes}分钟` : '' },
    { '指标': '趋势范围', '数值': trendRangeLabel.value },
  ]
}

const getStatsTrendRows = () => {
  return trendSeries.value.map(day => ({
    '日期': day.date,
    '显示日期': formatTrendDate(day.date),
    '提交数': day.count
  }))
}

const getStatsGradeRows = () => {
  return [
    { grade: 'A', label: '优秀' },
    { grade: 'B', label: '良好' },
    { grade: 'C', label: '及格' },
    { grade: 'D', label: '待提升' }
  ].map(item => {
    const count = gradeDistribution.value[item.grade as keyof typeof gradeDistribution] || 0
    const percentage = completedSubmissions.value.length > 0
      ? Math.round(count / completedSubmissions.value.length * 100)
      : 0
    return {
      '等级': item.grade,
      '说明': item.label,
      '人数': count,
      '占比': `${percentage}%`
    }
  })
}

const getStatsTextRows = () => {
  const rows: Array<Record<string, string | number>> = []
  questionStats.value?.questions
    .filter(q => isTextQuestion(q.type))
    .forEach(q => {
      getTextTags(q).forEach(item => {
        rows.push({
          '题号': `Q${q.index}`,
          '题目': q.text || '',
          '类型': '关键词标签',
          '内容': item.text || '',
          '次数': item.count || 0
        })
      })
      if (getTextEmptyCount(q) > 0) {
        rows.push({
          '题号': `Q${q.index}`,
          '题目': q.text || '',
          '类型': '无/没有意见',
          '内容': '无/没有意见',
          '次数': getTextEmptyCount(q)
        })
      }
      getTextLongAnswers(q).forEach(item => {
        rows.push({
          '题号': `Q${q.index}`,
          '题目': q.text || '',
          '类型': '代表性回答',
          '内容': item.text || '',
          '次数': item.count || 0
        })
      })
    })
  return rows
}

const exportStatsAsExcel = () => {
  const workbook = XLSX.utils.book_new()
  XLSX.utils.book_append_sheet(workbook, XLSX.utils.json_to_sheet(getStatsOverviewRows()), '统计概览')
  XLSX.utils.book_append_sheet(workbook, XLSX.utils.json_to_sheet(getStatsTrendRows()), '提交趋势')

  if (isScored.value) {
    XLSX.utils.book_append_sheet(workbook, XLSX.utils.json_to_sheet(getStatsGradeRows()), '得分分布')
  }

  const questionRows = buildQuestionStatsRows()
  if (questionRows.length > 0) {
    XLSX.utils.book_append_sheet(workbook, XLSX.utils.json_to_sheet(questionRows), '题目统计')
  }

  const textRows = getStatsTextRows()
  if (textRows.length > 0) {
    XLSX.utils.book_append_sheet(workbook, XLSX.utils.json_to_sheet(textRows), '文本题汇总')
  }

  const excelBuffer = XLSX.write(workbook, {
    bookType: 'xlsx',
    type: 'array'
  })
  downloadBlob(
    new Blob([excelBuffer], {
      type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    }),
    `${getStatsExportBaseName()}.xlsx`
  )
}

const renderQuestionChartImage = async (question: QuestionStat) => {
  if (!question.options.length) return ''

  const width = 460
  const height = Math.max(220, getQuestionChartHeight(question))
  const host = document.createElement('div')
  host.style.position = 'fixed'
  host.style.left = '-12000px'
  host.style.top = '0'
  host.style.width = `${width}px`
  host.style.height = `${height}px`
  host.style.pointerEvents = 'none'
  host.style.contain = 'layout paint style'
  host.style.background = '#ffffff'
  document.body.appendChild(host)

  let chart: ECharts | null = null
  try {
    chart = init(host, 'light', {
      renderer: 'canvas',
      width,
      height,
    })
    chart.setOption({
      ...getQuestionVisualOption(question),
      animation: false,
    } as EChartsOption, questionChartSetOptionOpts)
    await delay(80)
    return chart.getDataURL({
      type: 'png',
      pixelRatio: 2,
      backgroundColor: '#ffffff',
    })
  } finally {
    disposeChartSafely(chart)
    host.remove()
  }
}

const prepareStatsExportChartImages = async () => {
  const questions = questionStats.value?.questions || []
  const imageMap: Record<string, string> = {}

  for (const question of questions) {
    if (isTextQuestion(question.type) || question.options.length === 0) continue
    const key = getQuestionExportChartKey(question)
    try {
      imageMap[key] = await renderQuestionChartImage(question)
    } catch (error) {
      console.warn(`生成题目 Q${question.index} 导出图表失败:`, error)
    }
  }

  statsExportChartImages.value = imageMap
}

const prepareStatsExportReport = async () => {
  await prepareStatsExportChartImages()
  renderStatsExportReport.value = true
  await nextTick()
  await delay(120)
  const element = statsExportReportRef.value
  if (!element) throw new Error('找不到统计报告导出节点')
  return element
}

const cleanupStatsExportReport = async () => {
  renderStatsExportReport.value = false
  statsExportChartImages.value = {}
  await nextTick()
}

type StatsExportSliceRange = {
  offsetY: number
  height: number
}

const getElementRelativeBounds = (root: HTMLElement, target: HTMLElement) => {
  const rootRect = root.getBoundingClientRect()
  const targetRect = target.getBoundingClientRect()
  return {
    top: Math.max(0, Math.floor(targetRect.top - rootRect.top)),
    bottom: Math.max(0, Math.ceil(targetRect.bottom - rootRect.top))
  }
}

const getStatsExportSliceRanges = (
  element: HTMLElement,
  totalHeight: number,
  preferredSliceHeight: number
): StatsExportSliceRange[] => {
  const safeBreakpoints = new Set<number>([0, totalHeight])
  const breakableSelectors = [
    '.stats-export-hero',
    '.stats-export-section',
    '.stats-export-question-card',
    '.stats-export-question-head',
    '.stats-export-question-body',
    '.stats-export-detail-box',
    '.stats-export-chart-box',
    '.stats-export-static-row',
    '.stats-export-text-list .text-answer-item'
  ]

  breakableSelectors.forEach(selector => {
    element.querySelectorAll<HTMLElement>(selector).forEach(node => {
      const bounds = getElementRelativeBounds(element, node)
      if (bounds.top > 0 && bounds.top < totalHeight) safeBreakpoints.add(bounds.top)
      if (bounds.bottom > 0 && bounds.bottom < totalHeight) safeBreakpoints.add(bounds.bottom)
    })
  })

  const sortedBreakpoints = Array.from(safeBreakpoints).sort((a, b) => a - b)
  const ranges: StatsExportSliceRange[] = []
  const minUsefulSliceHeight = Math.min(720, Math.max(360, preferredSliceHeight * 0.35))
  let offsetY = 0

  while (offsetY < totalHeight) {
    const targetEnd = Math.min(totalHeight, offsetY + preferredSliceHeight)
    if (targetEnd >= totalHeight) {
      ranges.push({ offsetY, height: totalHeight - offsetY })
      break
    }

    const candidates = sortedBreakpoints.filter(point =>
      point > offsetY + minUsefulSliceHeight && point <= targetEnd
    )
    let endY = candidates.length > 0 ? candidates[candidates.length - 1] : targetEnd

    if (endY <= offsetY) {
      endY = targetEnd
    }

    ranges.push({ offsetY, height: endY - offsetY })
    offsetY = endY
  }

  return ranges.filter(range => range.height > 0)
}

const renderElementSliceToPng = async (
  element: HTMLElement,
  offsetY: number,
  sliceHeight: number,
  width: number
) => {
  const domtoimage = (await import('dom-to-image-more')).default
  const wrapper = document.createElement('div')
  const clone = element.cloneNode(true) as HTMLElement
  const sourceCanvases = Array.from(element.querySelectorAll('canvas'))
  const clonedCanvases = Array.from(clone.querySelectorAll('canvas'))

  // cloneNode 不会复制 canvas 位图；导出切片用静态图片替换，避免移动原始 DOM 造成页面抖动。
  sourceCanvases.forEach((sourceCanvas, index) => {
    const clonedCanvas = clonedCanvases[index]
    if (!clonedCanvas) return

    try {
      const image = document.createElement('img')
      image.src = sourceCanvas.toDataURL('image/png')
      image.width = sourceCanvas.width
      image.height = sourceCanvas.height
      image.style.width = sourceCanvas.style.width || `${sourceCanvas.clientWidth}px`
      image.style.height = sourceCanvas.style.height || `${sourceCanvas.clientHeight}px`
      image.style.maxWidth = '100%'
      image.style.display = 'block'
      clonedCanvas.replaceWith(image)
    } catch (error) {
      console.warn('复制统计图表画布失败，保留克隆画布:', error)
    }
  })

  wrapper.style.position = 'fixed'
  wrapper.style.left = '-12000px'
  wrapper.style.top = '0'
  wrapper.style.width = `${width}px`
  wrapper.style.height = `${sliceHeight}px`
  wrapper.style.overflow = 'hidden'
  wrapper.style.background = '#f8fafc'
  wrapper.style.pointerEvents = 'none'
  wrapper.style.contain = 'layout paint style'

  clone.style.position = 'relative'
  clone.style.top = `-${offsetY}px`
  clone.style.left = '0'
  clone.style.width = `${width}px`
  clone.style.margin = '0'
  clone.style.boxShadow = 'none'

  wrapper.appendChild(clone)
  document.body.appendChild(wrapper)

  try {
    return await domtoimage.toPng(wrapper, {
      width,
      height: sliceHeight,
      quality: 1,
      bgcolor: '#f8fafc',
    })
  } finally {
    wrapper.remove()
  }
}

const exportStatsAsPng = async () => {
  const element = await prepareStatsExportReport()
  const width = Math.ceil(element.scrollWidth || element.offsetWidth)
  const totalHeight = Math.ceil(element.scrollHeight || element.offsetHeight)
  const safeSliceHeight = 5200
  const ranges = getStatsExportSliceRanges(element, totalHeight, safeSliceHeight)
  const totalPages = ranges.length
  const baseName = getStatsExportBaseName()

  for (let pageIndex = 0; pageIndex < totalPages; pageIndex++) {
    const range = ranges[pageIndex]
    const dataUrl = await renderElementSliceToPng(element, range.offsetY, range.height, width)
    const suffix = totalPages > 1 ? `-${pad2(pageIndex + 1)}` : ''
    downloadHref(dataUrl, `${baseName}${suffix}.png`)
    await delay(160)
  }
}

const exportStatsAsPdf = async () => {
  const { jsPDF } = await import('jspdf')
  const element = await prepareStatsExportReport()
  const width = Math.ceil(element.scrollWidth || element.offsetWidth)
  const totalHeight = Math.ceil(element.scrollHeight || element.offsetHeight)

  const pdf = new jsPDF({
    orientation: 'portrait',
    unit: 'mm',
    format: 'a4'
  })
  const margin = 10
  const pageWidth = 210
  const pageHeight = 297
  const contentWidth = pageWidth - margin * 2
  const contentHeight = pageHeight - margin * 2
  const sliceHeightPx = Math.max(900, Math.floor(width * contentHeight / contentWidth))
  const ranges = getStatsExportSliceRanges(element, totalHeight, sliceHeightPx)

  for (let pageIndex = 0; pageIndex < ranges.length; pageIndex++) {
    const range = ranges[pageIndex]
    const dataUrl = await renderElementSliceToPng(element, range.offsetY, range.height, width)
    if (pageIndex > 0) pdf.addPage()
    const imageHeight = (range.height * contentWidth) / width
    pdf.addImage(dataUrl, 'PNG', margin, margin, contentWidth, imageHeight)
  }

  pdf.save(`${getStatsExportBaseName()}.pdf`)
}

const executeStatsExport = async () => {
  statsExportLoading.value = true

  try {
    if (!questionStats.value && props.questionnaire?.id) {
      await loadQuestionStats()
    }

    if (!hasStatsExportData()) {
      showStatsExportMessage('暂无可导出的统计数据', 'error')
      return
    }

    if (statsExportFormat.value === 'excel') {
      exportStatsAsExcel()
    } else if (statsExportFormat.value === 'png') {
      await exportStatsAsPng()
    } else {
      await exportStatsAsPdf()
    }

    showStatsExportModal.value = false
    showStatsExportMessage('统计报告导出成功，文件已下载')
  } catch (error) {
    console.error('统计报告导出失败:', error)
    showStatsExportMessage('统计报告导出失败，请重试', 'error')
  } finally {
    await cleanupStatsExportReport()
    statsExportLoading.value = false
  }
}
</script>

<template>
  <div class="drawer-overlay" @click="close">
    <div class="drawer-panel" :class="{ 'is-exporting-stats': statsExportLoading }" @click.stop>
      <!-- 抽屉头部 -->
      <div class="drawer-header">
        <div class="drawer-title">
          <button class="btn-back" @click="close">
            <i class="ri-arrow-left-line"></i>
          </button>
          <h2>{{ questionnaire?.name || '问卷详情' }}</h2>
        </div>
        <div class="drawer-actions">
          <button class="btn-close" @click="close">
            <i class="ri-close-line"></i>
          </button>
        </div>
      </div>

      <!-- Tab 切换 -->
      <div class="drawer-tabs">
        <button 
          :class="['tab-btn', { active: activeTab === 'submissions' }]"
          @click="activeTab = 'submissions'"
        >
          <i class="ri-file-list-3-line"></i>
          答题记录
          <span class="tab-count">{{ submissions.length }}</span>
        </button>
        <button 
          :class="['tab-btn', { active: activeTab === 'statistics' }]"
          @click="activeTab = 'statistics'"
        >
          <i class="ri-bar-chart-grouped-line"></i>
          问卷统计
        </button>
      </div>

      <!-- 抽屉内容 -->
      <div class="drawer-content">
        <!-- 提交记录 Tab -->
        <div v-if="activeTab === 'submissions'" class="tab-submissions">
          <!-- 空状态 -->
          <div v-if="submissions.length === 0" class="empty-state">
            <i class="ri-inbox-line"></i>
            <p>暂无答题记录</p>
            <span>分发问卷后，答题记录将在这里显示</span>
          </div>

          <!-- 分组视图 -->
          <div v-else class="grouped-view">
            <!-- V45: 年份/月份筛选 + 控制栏 -->
            <div class="grouped-controls">
              <!-- 日期筛选 -->
              <div class="date-filters">
                <select v-model="filterYear" class="date-select">
                  <option :value="null">全部年份</option>
                  <option v-for="year in yearOptions" :key="year" :value="year">{{ year }}年</option>
                </select>
                <select v-model="filterMonth" class="date-select">
                  <option :value="null">全部月份</option>
                  <option v-for="month in monthOptions" :key="month" :value="month">{{ month }}月</option>
                </select>
              </div>
              <div class="controls-divider"></div>
              <button class="btn-toggle-all" @click="toggleAllCandidates">
                <i :class="areVisibleGroupsExpanded ? 'ri-contract-up-down-line' : 'ri-expand-up-down-line'"></i>
                {{ areVisibleGroupsExpanded ? '全部收起' : '全部展开' }}
              </button>
              <button class="btn-export" @click="openExportModal">
                <i class="ri-download-line"></i>
                导出数据
              </button>
              <!-- ⭐ V44: 批量删除按钮 -->
              <button 
                :class="['btn-batch-select', { active: isSelectMode }]" 
                @click="toggleSelectMode"
              >
                <i :class="isSelectMode ? 'ri-close-line' : 'ri-checkbox-multiple-line'"></i>
                {{ isSelectMode ? '取消选择' : '批量删除' }}
              </button>
            </div>
            
            <!-- ⭐ V44: 批量操作栏 -->
            <div v-if="isSelectMode" class="batch-action-bar">
              <div class="batch-left">
                <label class="select-all-checkbox">
                  <input 
                    type="checkbox" 
                    :checked="selectedSubmissions.size === submissions.length && submissions.length > 0"
                    @change="toggleSelectAll"
                  />
                  <span>全选</span>
                </label>
                <span class="selected-count">已选择 {{ selectedSubmissions.size }} 条</span>
              </div>
              <div class="batch-right">
                <button 
                  class="btn-batch-delete" 
                  :disabled="selectedSubmissions.size === 0"
                  @click="openBatchDeleteModal"
                >
                  <i class="ri-delete-bin-line"></i>
                  删除选中 ({{ selectedSubmissions.size }})
                </button>
              </div>
            </div>
            
            <!-- 候选人分组卡片 -->
            <div class="candidate-groups">
              <div 
                v-for="group in paginatedGroupedSubmissions" 
                :key="getGroupKey(group)"
                class="candidate-group-card"
                :class="{ expanded: expandedCandidates.has(getGroupKey(group)) }"
              >
                <!-- 分组头部 V42: 调整布局，标签放名字旁边 -->
                <div 
                  class="group-header"
                  @click="toggleCandidateExpand(getGroupKey(group))"
                >
                  <!-- ⭐ V44: 选择模式下显示复选框 -->
                  <input 
                    v-if="isSelectMode"
                    type="checkbox" 
                    class="group-checkbox"
                    :checked="group.submissions.every(s => selectedSubmissions.has(s.id))"
                    @click.stop
                    @change="group.submissions.forEach(s => toggleSubmissionSelect(s.id))"
                  />
                  <div class="group-main">
                    <span class="group-avatar">{{ getGroupInitial(group) }}</span>
                    <div class="group-info">
                      <div class="group-name-row">
                        <span class="group-name">{{ getGroupDisplayName(group) }}</span>
                        <span class="group-phone">{{ group.phone }}</span>
                      </div>
                      <div class="group-stats">
                        <span class="stat-badge total">
                          <i class="ri-file-list-3-line"></i>
                          {{ group.totalSubmissions }}条记录
                        </span>
                        <span class="stat-badge completed" v-if="group.completedCount > 0">
                          <i class="ri-checkbox-circle-fill"></i>
                          {{ group.completedCount }}已完成
                        </span>
                        <span class="stat-badge pending" v-if="getGroupPendingCount(group) > 0">
                          <i class="ri-time-fill"></i>
                          {{ getGroupPendingCount(group) }}未完成
                        </span>
                        <span class="stat-badge latest" v-if="group.latestSubmission">
                          <i class="ri-time-line"></i>
                          {{ formatShortDate(group.latestSubmission.submitted_at) }}
                        </span>
                      </div>
                    </div>
                  </div>
                  <i :class="['expand-icon', expandedCandidates.has(getGroupKey(group)) ? 'ri-arrow-up-s-line' : 'ri-arrow-down-s-line']"></i>
                </div>
                
                <!-- 展开的提交列表 -->
                <div v-if="expandedCandidates.has(getGroupKey(group))" class="group-submissions">
                  <div 
                    v-for="(sub, idx) in getGroupSubmissions(group)" 
                    :key="sub.id"
                    class="submission-item"
                    :class="{ selected: selectedSubmission?.id === sub.id }"
                  >
                    <div class="submission-order">
                      #{{ (getGroupPage(group) - 1) * groupPageSize + idx + 1 }}
                    </div>
                    <div class="submission-info">
                      <span class="submission-time">
                        {{ sub.submitted_at ? formatDate(sub.submitted_at) : '进行中' }}
                      </span>
                    </div>
                    <div class="submission-result">
                      <span v-if="sub.total_score !== null && sub.total_score !== undefined" class="score">{{ sub.total_score }}分</span>
                      <span v-if="sub.grade" class="grade" :class="`grade-${sub.grade.toLowerCase()}`">{{ sub.grade }}</span>
                      <span :class="['status-mini', sub.status === 'completed' ? 'completed' : 'progress']">
                        {{ sub.status === 'completed' ? '已完成' : '进行中' }}
                      </span>
                    </div>
                    <div class="submission-actions">
                      <!-- V42: 移除查看详情按钮，人员画像中已有问卷数据展示 -->
                      <button class="btn-mini delete" title="删除" @click.stop="handleDeleteSubmission(sub)">
                        <i class="ri-delete-bin-line"></i>
                      </button>
                    </div>
                  </div>

                  <div v-if="getGroupTotalPages(group) > 1" class="group-pagination">
                    <button
                      class="page-btn"
                      :disabled="getGroupPage(group) <= 1"
                      @click="changeGroupPage(group, getGroupPage(group) - 1)"
                    >
                      <i class="ri-arrow-left-s-line"></i>
                      上一页
                    </button>
                    <span class="page-info">
                      {{ getGroupPage(group) }} / {{ getGroupTotalPages(group) }}
                    </span>
                    <button
                      class="page-btn"
                      :disabled="getGroupPage(group) >= getGroupTotalPages(group)"
                      @click="changeGroupPage(group, getGroupPage(group) + 1)"
                    >
                      下一页
                      <i class="ri-arrow-right-s-line"></i>
                    </button>
                </div>
              </div>
              </div>
            </div>
            <div v-if="groupListTotalPages > 1" class="group-list-pagination">
              <button
                class="page-btn"
                :disabled="groupListPage === 1"
                @click="changeGroupListPage(groupListPage - 1)"
                title="上一页"
              >
                <i class="ri-arrow-left-s-line"></i>
              </button>
              <span class="page-info">
                {{ groupListPage }} / {{ groupListTotalPages }} (共 {{ groupedSubmissions.length }} 人)
              </span>
              <button
                class="page-btn"
                :disabled="groupListPage >= groupListTotalPages"
                @click="changeGroupListPage(groupListPage + 1)"
                title="下一页"
              >
                <i class="ri-arrow-right-s-line"></i>
              </button>
            </div>
          </div>
        </div>

        <!-- 问卷统计 Tab - V42 全新设计 -->
        <div v-if="activeTab === 'statistics'" class="tab-statistics">
          <!-- 加载状态 -->
          <div v-if="statsLoading" class="stats-loading">
            <i class="ri-loader-4-line spinning"></i>
            <span>加载统计数据中...</span>
          </div>

          <!-- 错误状态 -->
          <div v-else-if="statsError" class="stats-error">
            <i class="ri-error-warning-line"></i>
            <span>{{ statsError }}</span>
            <button @click="loadQuestionStats">重试</button>
          </div>

          <!-- 统计内容 -->
          <template v-else>
            <div class="statistics-toolbar">
              <div class="statistics-toolbar-text">
                <h3>问卷统计</h3>
                <p>导出完整可视化统计报告，包含全部题目分析</p>
              </div>
              <button
                class="btn-stats-export"
                :disabled="statsLoading || statsExportLoading"
                @click="openStatsExportModal"
              >
                <i class="ri-download-cloud-2-line"></i>
                导出统计
              </button>
            </div>

            <!-- V45: 核心指标卡片 - 修复无数据时显示问题 -->
            <div class="stats-overview">
              <div class="stat-card">
                <div class="stat-icon participants">
                  <i class="ri-group-line"></i>
                </div>
                <div class="stat-data">
                  <!-- V46: 使用 actualSubmissionCount 确保显示正确 -->
                  <span class="stat-value">{{ actualSubmissionCount }}</span>
                  <span class="stat-label">参与人数</span>
                </div>
              </div>
              <div class="stat-card">
                <div class="stat-icon completion">
                  <i class="ri-checkbox-circle-line"></i>
                </div>
                <div class="stat-data">
                  <!-- V46: 修复完成率显示 -->
                  <span class="stat-value">{{ actualSubmissionCount > 0 ? (questionStats?.completion_rate ?? 100) : 0 }}%</span>
                  <span class="stat-label">完成率</span>
                </div>
              </div>
              <!-- V43: 评分问卷显示优良率，调查问卷显示题目数 -->
              <div class="stat-card" v-if="isScored">
                <div class="stat-icon highlight">
                  <i class="ri-star-line"></i>
                </div>
                <div class="stat-data">
                  <span class="stat-value">{{ highScoreRate }}%</span>
                  <span class="stat-label">优良率</span>
                </div>
              </div>
              <div class="stat-card" v-else>
                <div class="stat-icon questions">
                  <i class="ri-questionnaire-line"></i>
                </div>
                <div class="stat-data">
                  <span class="stat-value">{{ questionStats?.questions?.length || 0 }}</span>
                  <span class="stat-label">题目数</span>
                </div>
              </div>
              <div class="stat-card" v-if="questionStats?.average_duration_minutes">
                <div class="stat-icon duration">
                  <i class="ri-time-line"></i>
                </div>
                <div class="stat-data">
                  <span class="stat-value">{{ questionStats.average_duration_minutes }}<small>分钟</small></span>
                  <span class="stat-label">平均用时</span>
                </div>
              </div>
            </div>

            <!-- V45: 无数据时显示空状态提示 -->
            <div v-if="!hasSubmissions" class="stats-empty-state">
              <div class="empty-icon">
                <i class="ri-bar-chart-line"></i>
              </div>
              <h4>暂无统计数据</h4>
              <p>分发问卷并收集回复后，统计数据将在这里显示</p>
            </div>

            <!-- V43: 得分分布（优化布局，修复换行问题） -->
            <div v-if="isScored && completedSubmissions.length > 0" class="grade-distribution">
              <h4><i class="ri-bar-chart-grouped-line"></i> 得分分布</h4>
              <div class="grade-bars">
                <div 
                  v-for="gradeInfo in [
                    { grade: 'A', label: '优秀', color: '#10b981' },
                    { grade: 'B', label: '良好', color: '#3b82f6' },
                    { grade: 'C', label: '及格', color: '#f59e0b' },
                    { grade: 'D', label: '待提升', color: '#ef4444' }
                  ]" 
                  :key="gradeInfo.grade"
                  class="grade-bar"
                >
                  <div class="grade-label-wrap" :style="{ color: gradeInfo.color }">
                    <span class="grade-letter">{{ gradeInfo.grade }}</span>
                    <span class="grade-text">{{ gradeInfo.label }}</span>
                  </div>
                  <div class="grade-track">
                    <div 
                      class="grade-fill"
                      :class="`grade-${gradeInfo.grade.toLowerCase()}`"
                      :style="{
                        width: completedSubmissions.length > 0
                          ? (gradeDistribution[gradeInfo.grade as keyof typeof gradeDistribution] / completedSubmissions.length * 100) + '%'
                          : '0%'
                      }"
                    ></div>
                  </div>
                  <span class="grade-count">
                    {{ completedSubmissions.length > 0 ? Math.round(gradeDistribution[gradeInfo.grade as keyof typeof gradeDistribution] / completedSubmissions.length * 100) : 0 }}%
                    ({{ gradeDistribution[gradeInfo.grade as keyof typeof gradeDistribution] }}人)
                  </span>
                </div>
              </div>
            </div>

            <!-- V43: 提交趋势（优化样式） -->
            <div v-if="questionStats?.daily_trend && questionStats.daily_trend.length > 0" class="submission-trend">
              <div class="trend-header">
                <h4><i class="ri-calendar-line"></i> 提交趋势</h4>
                <div class="trend-range">
                  <button
                    class="range-btn"
                    :class="{ active: trendRange === 'week' }"
                    @click="trendRange = 'week'"
                  >
                    本周
                  </button>
                  <button
                    class="range-btn"
                    :class="{ active: trendRange === 'month' }"
                    @click="trendRange = 'month'"
                  >
                    近一个月
                  </button>
                </div>
              </div>
              <div class="trend-chart-v43">
                <div class="trend-line-container" ref="trendContainerRef">
                  <!-- 背景网格 -->
                  <div class="trend-grid">
                    <div class="grid-line" v-for="i in 4" :key="i"></div>
                  </div>
                  <div
                    v-if="trendTooltip.visible"
                    class="trend-tooltip"
                    :style="{ left: `${trendTooltip.x}px`, top: `${trendTooltip.y}px` }"
                  >
                    {{ trendTooltip.text }}
                  </div>
                  <!-- 数据点和连线 -->
                  <svg
                    class="trend-svg"
                    :viewBox="`0 0 ${trendChartWidth} ${trendSvgHeight}`"
                    preserveAspectRatio="none"
                  >
                    <defs>
                      <linearGradient id="areaGradient" x1="0%" y1="0%" x2="0%" y2="100%">
                        <stop offset="0%" style="stop-color: #7c3aed; stop-opacity: 0.3" />
                        <stop offset="100%" style="stop-color: #7c3aed; stop-opacity: 0.02" />
                      </linearGradient>
                    </defs>
                    <!-- 面积填充 -->
                    <path 
                      :d="trendAreaPath" 
                      fill="url(#areaGradient)"
                    />
                    <!-- 折线 -->
                    <path 
                      :d="trendLinePath" 
                      fill="none" 
                      stroke="#7c3aed" 
                      stroke-width="2.5"
                      stroke-linecap="round"
                      stroke-linejoin="round"
                    />
                    <!-- 数据点 -->
                  <g
                      v-for="(point, idx) in trendPoints" 
                      :key="idx"
                    @mouseenter="showTrendTooltip($event, point)"
                    @mousemove="moveTrendTooltip"
                    @mouseleave="hideTrendTooltip"
                  >
                    <circle 
                      :cx="point.x" 
                      :cy="point.y" 
                      r="4"
                      fill="white"
                      stroke="#7c3aed"
                      stroke-width="2"
                    />
                  </g>
                  <g class="trend-axis-labels">
                    <text
                      v-for="(point, idx) in trendLabelPoints"
                      :key="`label-${idx}`"
                      :x="point.x"
                      :y="trendLabelY"
                      :text-anchor="point.anchor"
                      class="trend-axis-label"
                    >
                      {{ formatTrendDate(point.date) }}
                    </text>
                  </g>
                  </svg>
                </div>
              </div>
            </div>

            <!-- V43: 题目分析（带分页，每页10条） -->
            <div v-if="questionStats?.questions && questionStats.questions.length > 0" class="question-analysis">
              <div class="question-analysis-header">
                <h4><i class="ri-file-list-3-line"></i> 题目分析</h4>
                <span class="question-total">共 {{ questionStats.questions.length }} 题</span>
              </div>
              <div class="question-list">
                <div 
                  v-for="q in paginatedQuestions" 
                  :key="q.id"
                  class="question-stat-card"
                >
                  <div class="question-header">
                    <span class="question-index">Q{{ q.index }}</span>
                    <span class="question-text">{{ q.text }}</span>
                    <div class="question-type-group">
                      <span class="question-type-badge" :class="`type-${q.type}`">
                        {{ getQuestionTypeLabel(q.type) }}
                      </span>
                      <span
                        v-if="isSingleChoiceQuestion(q.type) && q.options.length > 0"
                        class="question-type-toggle"
                      >
                        <button
                          type="button"
                          class="toggle-btn"
                          :class="{ active: getQuestionChartMode(q) === 'pie' }"
                          @click="setQuestionChartMode(q, 'pie')"
                        >
                          环形图
                        </button>
                        <button
                          type="button"
                          class="toggle-btn"
                          :class="{ active: getQuestionChartMode(q) === 'bar' }"
                          @click="setQuestionChartMode(q, 'bar')"
                        >
                          条形图
                        </button>
                      </span>
                    </div>
                  </div>
                  
                  <div class="question-stat-body" :class="{ 'is-text': isTextQuestion(q.type) }">
                    <!-- 选择题/量表题选项分布 -->
                    <template v-if="!isTextQuestion(q.type)">
                      <div class="question-chart-panel">
                        <div class="chart-mode-label">{{ getQuestionVisualLabel(q) }}</div>
                        <div v-if="q.options.length > 0" class="option-chart">
                          <div class="option-chart-body">
                            <EChartContainer
                              :option="getQuestionVisualOption(q)"
                              theme="light"
                              :set-option-opts="questionChartSetOptionOpts"
                              :style="{ height: `${getQuestionChartHeight(q)}px` }"
                            />
                          </div>
                          <div v-if="getQuestionVisualMode(q) === 'pie'" class="chart-legend-list">
                            <div
                              v-for="(opt, optIndex) in q.options"
                              :key="`legend-${q.id}-${opt.index ?? opt.text}`"
                              class="chart-legend-item"
                            >
                              <span class="chart-legend-dot" :style="{ background: getQuestionOptionColor(optIndex) }"></span>
                              <span class="chart-legend-text">{{ opt.text }}</span>
                              <span class="chart-legend-value">{{ opt.count }}人</span>
                            </div>
                          </div>
                        </div>
                        <div v-else class="empty-option-chart">
                          暂无统计数据
                        </div>
                      </div>

                      <div class="question-detail-panel">
                        <div class="detail-panel-title">
                          <span>选项明细</span>
                          <div class="detail-panel-actions">
                            <em>{{ getQuestionResponseText(q) }}</em>
                            <div class="option-sort-toggle" aria-label="选项明细排序">
                              <button
                                type="button"
                                :class="{ active: getOptionSortMode(q) === 'default' }"
                                @click="setOptionSortMode(q, 'default')"
                              >
                                默认
                              </button>
                              <button
                                type="button"
                                :class="{ active: getOptionSortMode(q) === 'desc' }"
                                @click="setOptionSortMode(q, 'desc')"
                              >
                                降序
                              </button>
                              <button
                                type="button"
                                :class="{ active: getOptionSortMode(q) === 'asc' }"
                                @click="setOptionSortMode(q, 'asc')"
                              >
                                升序
                              </button>
                            </div>
                          </div>
                        </div>
                        <div class="option-detail-list">
                          <div class="option-detail-row" v-for="opt in getSortedQuestionOptions(q)" :key="opt.index ?? opt.text">
                            <div class="option-detail-head">
                              <span class="option-text">{{ opt.text }}</span>
                              <span class="option-stats">{{ opt.count }}人 · {{ normalizePercentage(opt.percentage) }}%</span>
                            </div>
                            <div class="option-track">
                              <div class="option-fill" :style="{ width: `${normalizePercentage(opt.percentage)}%` }"></div>
                            </div>
                          </div>
                        </div>
                      </div>
                    </template>

                    <!-- 文本题答案展示 -->
                    <template v-else>
                      <div class="text-insight-panel">
                        <div class="text-answer-count">共收到 {{ q.total_answers }} 条回答</div>
                        <div v-if="hasTextSummary(q)" class="text-answer-summary">
                          <div
                            v-if="getTextTags(q).length > 0 || getTextEmptyCount(q) > 0"
                            class="text-answer-tags"
                          >
                            <span
                              v-for="(tag, idx) in getTextTags(q)"
                              :key="`tag-${q.id}-${idx}`"
                              class="text-tag"
                            >
                              {{ tag.text }} <em>×{{ tag.count }}</em>
                            </span>
                            <span v-if="getTextEmptyCount(q) > 0" class="text-tag muted">
                              无/没有意见 <em>×{{ getTextEmptyCount(q) }}</em>
                            </span>
                          </div>
                        </div>
                        <div v-else class="empty-option-chart">
                          暂无关键词汇总
                        </div>
                      </div>

                      <div class="text-answers-panel">
                        <div class="detail-panel-title">
                          <span>代表性回答</span>
                          <em>{{ getTextTotalPages(q) > 1 ? `${getTextPage(q)} / ${getTextTotalPages(q)}` : '全部' }}</em>
                        </div>
                        <div v-if="hasTextSummary(q) && getTextLongAnswers(q).length > 0" class="text-answer-samples">
                          <div
                            v-for="(ans, idx) in getTextLongAnswerPage(q)"
                            :key="`ans-${q.id}-${idx}`"
                            class="text-answer-item"
                          >
                            "{{ ans.text }}"
                            <span class="text-answer-count-badge">×{{ ans.count }}</span>
                          </div>
                          <div v-if="getTextTotalPages(q) > 1" class="text-answer-pagination">
                            <button
                              class="page-btn"
                              :disabled="getTextPage(q) === 1"
                              @click="setTextPage(q, getTextPage(q) - 1)"
                            >
                              <i class="ri-arrow-left-s-line"></i>
                            </button>
                            <span class="page-info">{{ getTextPage(q) }} / {{ getTextTotalPages(q) }}</span>
                            <button
                              class="page-btn"
                              :disabled="getTextPage(q) === getTextTotalPages(q)"
                              @click="setTextPage(q, getTextPage(q) + 1)"
                            >
                              <i class="ri-arrow-right-s-line"></i>
                            </button>
                          </div>
                        </div>
                        <div v-else-if="q.options.length > 0" class="text-answer-samples">
                          <div v-for="(ans, idx) in q.options.slice(0, 5)" :key="idx" class="text-answer-item">
                            "{{ ans.text }}"
                          </div>
                          <div v-if="q.options.length > 5" class="text-answer-more">
                            还有 {{ q.options.length - 5 }} 条回答...
                          </div>
                        </div>
                        <div v-else class="empty-option-chart">
                          暂无文本回答
                        </div>
                      </div>
                    </template>
                  </div>
                </div>
              </div>
              <!-- V43: 分页控件 -->
              <div v-if="questionTotalPages > 1" class="question-pagination">
                <button 
                  class="page-btn" 
                  :disabled="questionCurrentPage === 1"
                  @click="questionCurrentPage--"
                >
                  <i class="ri-arrow-left-s-line"></i>
                </button>
                <span class="page-info">{{ questionCurrentPage }} / {{ questionTotalPages }}</span>
                <button 
                  class="page-btn" 
                  :disabled="questionCurrentPage === questionTotalPages"
                  @click="questionCurrentPage++"
                >
                  <i class="ri-arrow-right-s-line"></i>
                </button>
              </div>
            </div>
          </template>
        </div>
      </div>
    </div>
  </div>

  <!-- 问卷统计导出专用报告：使用完整数据，不受页面分页影响 -->
  <div v-if="renderStatsExportReport" class="stats-export-stage" aria-hidden="true">
    <article ref="statsExportReportRef" class="stats-export-report">
      <section class="stats-export-hero">
        <div>
          <span class="stats-export-kicker">TalentLens 问卷统计报告</span>
          <h1>{{ questionnaire?.name || questionStats?.questionnaire_name || '问卷统计' }}</h1>
          <p>导出时间：{{ getExportDateText() }} · 趋势范围：{{ trendRangeLabel }}</p>
        </div>
        <div class="stats-export-logo">
          <i class="ri-bar-chart-grouped-line"></i>
        </div>
      </section>

      <section class="stats-export-section">
        <div class="stats-export-section-title">
          <h2>核心概览</h2>
          <span>{{ actualSubmissionCount }} 份提交</span>
        </div>
        <div class="stats-export-overview">
          <div class="stats-export-metric">
            <span>参与人数</span>
            <strong>{{ actualSubmissionCount }}</strong>
          </div>
          <div class="stats-export-metric">
            <span>完成率</span>
            <strong>{{ actualSubmissionCount > 0 ? (questionStats?.completion_rate ?? 100) : 0 }}%</strong>
          </div>
          <div class="stats-export-metric">
            <span>{{ isScored ? '优良率' : '题目数' }}</span>
            <strong>{{ isScored ? `${highScoreRate}%` : (questionStats?.questions?.length || 0) }}</strong>
          </div>
          <div class="stats-export-metric">
            <span>平均用时</span>
            <strong>{{ questionStats?.average_duration_minutes ? `${questionStats.average_duration_minutes}分钟` : '-' }}</strong>
          </div>
        </div>
      </section>

      <section v-if="isScored && completedSubmissions.length > 0" class="stats-export-section">
        <div class="stats-export-section-title">
          <h2>得分分布</h2>
          <span>按等级汇总</span>
        </div>
        <div class="stats-export-grade-list">
          <div
            v-for="gradeInfo in [
              { grade: 'A', label: '优秀', color: '#10b981' },
              { grade: 'B', label: '良好', color: '#3b82f6' },
              { grade: 'C', label: '及格', color: '#f59e0b' },
              { grade: 'D', label: '待提升', color: '#ef4444' }
            ]"
            :key="`export-grade-${gradeInfo.grade}`"
            class="stats-export-grade-row"
          >
            <div class="stats-export-grade-label" :style="{ color: gradeInfo.color }">
              <strong>{{ gradeInfo.grade }}</strong>
              <span>{{ gradeInfo.label }}</span>
            </div>
            <div class="stats-export-grade-track">
              <div
                class="stats-export-grade-fill"
                :style="{
                  width: completedSubmissions.length > 0
                    ? `${gradeDistribution[gradeInfo.grade as keyof typeof gradeDistribution] / completedSubmissions.length * 100}%`
                    : '0%',
                  background: gradeInfo.color
                }"
              ></div>
            </div>
            <div class="stats-export-grade-count">
              {{ gradeDistribution[gradeInfo.grade as keyof typeof gradeDistribution] }}人
            </div>
          </div>
        </div>
      </section>

      <section v-if="trendSeries.length > 0" class="stats-export-section">
        <div class="stats-export-section-title">
          <h2>提交趋势</h2>
          <span>{{ trendRangeLabel }}</span>
        </div>
        <div class="stats-export-trend">
          <div
            v-for="day in trendSeries"
            :key="`export-trend-${day.date}`"
            class="stats-export-trend-item"
          >
            <div class="stats-export-trend-bar-wrap">
              <div
                class="stats-export-trend-bar"
                :style="{ height: getTrendBarHeight(day.count) }"
              ></div>
            </div>
            <strong>{{ day.count }}</strong>
            <span>{{ formatTrendDate(day.date) }}</span>
          </div>
        </div>
      </section>

      <section v-if="questionStats?.questions && questionStats.questions.length > 0" class="stats-export-section">
        <div class="stats-export-section-title">
          <h2>题目分析</h2>
          <span>共 {{ questionStats.questions.length }} 题，已导出全部题目</span>
        </div>

        <div class="stats-export-question-list">
          <div
            v-for="q in questionStats.questions"
            :key="`export-question-${q.id}`"
            class="stats-export-question-card"
          >
            <div class="stats-export-question-head">
              <span class="question-index">Q{{ q.index }}</span>
              <div>
                <h3>{{ q.text }}</h3>
                <p>{{ getQuestionTypeLabel(q.type) }} · {{ getQuestionResponseText(q) }}</p>
              </div>
            </div>

            <div class="stats-export-question-body" :class="{ 'is-text': isTextQuestion(q.type) }">
              <template v-if="!isTextQuestion(q.type)">
                <div class="stats-export-chart-box">
                  <div class="chart-mode-label">{{ getQuestionVisualLabel(q) }}</div>
                  <div v-if="q.options.length > 0 && statsExportChartImages[getQuestionExportChartKey(q)]" class="stats-export-chart-image-wrap">
                    <img
                      class="stats-export-chart-image"
                      :src="statsExportChartImages[getQuestionExportChartKey(q)]"
                      :alt="`Q${q.index} ${getQuestionVisualLabel(q)}`"
                    />
                  </div>
                  <div v-else-if="q.options.length > 0" class="stats-export-static-chart">
                    <div
                      v-for="(opt, optIndex) in q.options"
                      :key="`export-static-${q.id}-${opt.index ?? opt.text}`"
                      class="stats-export-static-row"
                    >
                      <div class="stats-export-static-head">
                        <span class="stats-export-static-label">
                          <i :style="{ background: getQuestionOptionColor(optIndex) }"></i>
                          {{ opt.text }}
                        </span>
                        <strong>{{ opt.count }}人 · {{ normalizePercentage(opt.percentage) }}%</strong>
                      </div>
                      <div class="stats-export-static-track">
                        <div
                          class="stats-export-static-fill"
                          :style="{
                            width: `${getQuestionExportOptionWidth(q, opt)}%`,
                            background: getQuestionOptionColor(optIndex)
                          }"
                        ></div>
                      </div>
                    </div>
                  </div>
                  <div v-if="q.options.length > 0 && getQuestionVisualMode(q) === 'pie'" class="stats-export-chart-legend-list">
                    <div
                      v-for="(opt, optIndex) in q.options"
                      :key="`export-legend-${q.id}-${opt.index ?? opt.text}`"
                      class="stats-export-chart-legend-item"
                    >
                      <span class="chart-legend-dot" :style="{ background: getQuestionOptionColor(optIndex) }"></span>
                      <span class="chart-legend-text">{{ opt.text }}</span>
                      <span class="chart-legend-value">{{ opt.count }}人 · {{ normalizePercentage(opt.percentage) }}%</span>
                    </div>
                  </div>
                  <div v-if="q.options.length === 0" class="empty-option-chart">暂无统计数据</div>
                </div>

                <div class="stats-export-detail-box">
                  <div class="detail-panel-title">
                    <span>选项明细</span>
                    <em>{{ getQuestionResponseText(q) }}</em>
                  </div>
                  <div class="option-detail-list">
                    <div class="option-detail-row" v-for="opt in getSortedQuestionOptions(q)" :key="`export-opt-${q.id}-${opt.index ?? opt.text}`">
                      <div class="option-detail-head">
                        <span class="option-text">{{ opt.text }}</span>
                        <span class="option-stats">{{ opt.count }}人 · {{ normalizePercentage(opt.percentage) }}%</span>
                      </div>
                      <div class="option-track">
                        <div class="option-fill" :style="{ width: `${normalizePercentage(opt.percentage)}%` }"></div>
                      </div>
                    </div>
                  </div>
                </div>
              </template>

              <template v-else>
                <div class="stats-export-detail-box">
                  <div class="detail-panel-title">
                    <span>关键词汇总</span>
                    <em>{{ q.total_answers }} 条回答</em>
                  </div>
                  <div v-if="getTextTags(q).length > 0 || getTextEmptyCount(q) > 0" class="text-answer-tags">
                    <span
                      v-for="(tag, idx) in getTextTags(q)"
                      :key="`export-tag-${q.id}-${idx}`"
                      class="text-tag"
                    >
                      {{ tag.text }} <em>×{{ tag.count }}</em>
                    </span>
                    <span v-if="getTextEmptyCount(q) > 0" class="text-tag muted">
                      无/没有意见 <em>×{{ getTextEmptyCount(q) }}</em>
                    </span>
                  </div>
                  <div v-else class="empty-option-chart">暂无关键词汇总</div>
                </div>

                <div class="stats-export-detail-box">
                  <div class="detail-panel-title">
                    <span>代表性回答</span>
                    <em>全部聚合回答</em>
                  </div>
                  <div v-if="getTextLongAnswers(q).length > 0" class="stats-export-text-list">
                    <div
                      v-for="(ans, idx) in getTextLongAnswers(q)"
                      :key="`export-answer-${q.id}-${idx}`"
                      class="text-answer-item"
                    >
                      "{{ ans.text }}"
                      <span class="text-answer-count-badge">×{{ ans.count }}</span>
                    </div>
                  </div>
                  <div v-else class="empty-option-chart">暂无文本回答</div>
                </div>
              </template>
            </div>
          </div>
        </div>
      </section>
    </article>
  </div>

  <!-- 问卷统计导出弹窗 -->
  <Teleport to="body">
    <Transition name="modal">
      <div v-if="showStatsExportModal" class="modal-overlay" @click="closeStatsExportModal">
        <div class="modal-dialog export-modal stats-export-modal" @click.stop>
          <div class="modal-header">
            <h3><i class="ri-download-cloud-2-line"></i> 导出统计报告</h3>
            <button class="btn-close-modal" :disabled="statsExportLoading" @click="closeStatsExportModal">
              <i class="ri-close-line"></i>
            </button>
          </div>
          <div class="modal-body export-body">
            <p class="export-info">
              <i class="ri-bar-chart-grouped-line"></i>
              将导出 <strong>{{ questionStats?.questions?.length || 0 }}</strong> 道题目的完整统计报告
            </p>
            <div class="export-format-group">
              <label class="format-label">选择导出格式：</label>
              <div class="format-options stats-format-options">
                <label class="format-option recommended" :class="{ active: statsExportFormat === 'pdf' }">
                  <input type="radio" v-model="statsExportFormat" value="pdf" />
                  <i class="ri-file-pdf-line"></i>
                  <span>PDF 报告</span>
                  <small>推荐，自动分页</small>
                </label>
                <label class="format-option" :class="{ active: statsExportFormat === 'png' }">
                  <input type="radio" v-model="statsExportFormat" value="png" />
                  <i class="ri-image-2-line"></i>
                  <span>PNG 图片</span>
                  <small>长内容自动拆图</small>
                </label>
                <label class="format-option" :class="{ active: statsExportFormat === 'excel' }">
                  <input type="radio" v-model="statsExportFormat" value="excel" />
                  <i class="ri-file-excel-2-line"></i>
                  <span>Excel 表格</span>
                  <small>用于二次分析</small>
                </label>
              </div>
            </div>
          </div>
          <div class="modal-footer">
            <button class="btn-cancel" :disabled="statsExportLoading" @click="closeStatsExportModal">取消</button>
            <button class="btn-primary" @click="executeStatsExport" :disabled="statsExportLoading">
              <i v-if="statsExportLoading" class="ri-time-line"></i>
              <i v-else class="ri-download-line"></i>
              {{ statsExportLoading ? '正在生成...' : '确认导出' }}
            </button>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>

  <!-- V42: 导出弹窗 -->
  <Teleport to="body">
    <Transition name="modal">
      <div v-if="showExportModal" class="modal-overlay" @click="closeExportModal">
        <div class="modal-dialog export-modal" @click.stop>
          <div class="modal-header">
            <h3><i class="ri-download-line"></i> 导出数据</h3>
            <button class="btn-close-modal" @click="closeExportModal">
              <i class="ri-close-line"></i>
            </button>
          </div>
          <div class="modal-body export-body">
            <p class="export-info">
              <i class="ri-file-list-3-line"></i>
              将导出 <strong>{{ submissions.length }}</strong> 条提交记录
            </p>
            <div class="export-format-group">
              <label class="format-label">选择导出格式：</label>
              <div class="format-options">
                <label class="format-option" :class="{ active: exportFormat === 'csv' }">
                  <input type="radio" v-model="exportFormat" value="csv" />
                  <i class="ri-file-text-line"></i>
                  <span>CSV 文件</span>
                  <small>通用格式，可用Excel打开</small>
                </label>
                <label class="format-option" :class="{ active: exportFormat === 'excel' }">
                  <input type="radio" v-model="exportFormat" value="excel" />
                  <i class="ri-file-excel-2-line"></i>
                  <span>Excel 文件</span>
                  <small>带格式的表格文件</small>
                </label>
              </div>
            </div>
          </div>
          <div class="modal-footer">
            <button class="btn-cancel" @click="closeExportModal">取消</button>
            <button class="btn-primary" @click="executeExport" :disabled="exportLoading">
              <i v-if="exportLoading" class="ri-loader-4-line spinning"></i>
              <i v-else class="ri-download-line"></i>
              {{ exportLoading ? '导出中...' : '确认导出' }}
            </button>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>

  <!-- V42: 导出成功提示 -->
  <Teleport to="body">
    <Transition name="toast">
      <div v-if="showExportSuccessToast" class="toast-success">
        <i class="ri-checkbox-circle-fill"></i>
        <span>{{ submissions.length > 0 ? '导出成功！文件已下载' : '暂无数据可导出' }}</span>
      </div>
    </Transition>
  </Teleport>

  <Teleport to="body">
    <Transition name="toast">
      <div v-if="showStatsExportToast" class="toast-success" :class="statsExportToastType">
        <i :class="statsExportToastType === 'success' ? 'ri-checkbox-circle-fill' : 'ri-error-warning-fill'"></i>
        <span>{{ statsExportToastMessage }}</span>
      </div>
    </Transition>
  </Teleport>
  
  <!-- ⭐ V44: 批量删除确认弹窗 -->
  <Teleport to="body">
    <Transition name="modal">
      <div v-if="showBatchDeleteModal" class="modal-overlay" @click="showBatchDeleteModal = false">
        <div class="modal-dialog confirm-modal batch-delete-modal" @click.stop>
          <div class="modal-header">
            <h3><i class="ri-delete-bin-line"></i> 批量删除确认</h3>
          </div>
          <div class="modal-body confirm-body">
            <p>确定要删除选中的 <strong>{{ selectedSubmissions.size }}</strong> 条提交记录吗？</p>
            <div class="batch-delete-preview">
              <div v-for="sub in submissions.filter(s => selectedSubmissions.has(s.id)).slice(0, 5)" :key="sub.id" class="preview-item">
                <span class="preview-name">{{ sub.candidate_name }}</span>
                <span class="preview-time">{{ formatDate(sub.submitted_at) }}</span>
              </div>
              <div v-if="selectedSubmissions.size > 5" class="preview-more">
                ...还有 {{ selectedSubmissions.size - 5 }} 条记录
              </div>
            </div>
            <p class="confirm-warning">
              <i class="ri-error-warning-line"></i>
              此操作不可恢复，请谨慎操作！
            </p>
          </div>
          <div class="modal-footer">
            <button class="btn-cancel" @click="showBatchDeleteModal = false">取消</button>
            <button class="btn-danger" @click="confirmBatchDelete">
              <i class="ri-delete-bin-line"></i>
              确认删除 ({{ selectedSubmissions.size }})
            </button>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
@import './styles/questionnaire-detail-drawer.css';
</style>
