import { computed, onBeforeUnmount, onMounted, ref, watch, type ComputedRef, type Ref } from 'vue'
import type { QuestionnaireQuestionStats, Submission } from '../../api/assessments'

type TrendRange = 'week' | 'month'

type TrendDay = {
  date: string
  count: number
}

const pad2 = (value: number | string) => String(value).padStart(2, '0')
const toDateKey = (date: Date) =>
  `${date.getFullYear()}-${pad2(date.getMonth() + 1)}-${pad2(date.getDate())}`

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

const formatTrendDate = (dateStr: string) => {
  if (!dateStr) return ''
  if (dateStr.includes('/')) return dateStr
  if (/^\d{4}-\d{2}-\d{2}$/.test(dateStr)) {
    const [, month, day] = dateStr.split('-')
    return `${Number(month)}/${day}`
  }
  const date = new Date(dateStr)
  if (Number.isNaN(date.getTime())) return dateStr
  return `${date.getMonth() + 1}/${String(date.getDate()).padStart(2, '0')}`
}

export function useTrendChart(options: {
  trendRange: Ref<TrendRange>
  questionStats: Ref<QuestionnaireQuestionStats | null>
  completedSubmissions: ComputedRef<Submission[]>
}) {
  const { trendRange, questionStats, completedSubmissions } = options
  const trendChartWidth = ref(600)
  const trendChartHeight = 100
  const trendChartPaddingX = 0
  const trendChartPaddingY = 10
  const trendLabelOffset = 18
  const trendSvgHeight = trendChartHeight + trendLabelOffset
  const trendBaselineY = trendChartHeight - trendChartPaddingY
  const trendLabelY = trendChartHeight + 12
  const trendContainerRef = ref<HTMLElement | null>(null)
  const trendResizeObserver = ref<ResizeObserver | null>(null)
  const trendTooltip = ref({ visible: false, x: 0, y: 0, text: '' })

  const getRangeDays = () => {
    const today = new Date()
    return trendRange.value === 'month' ? buildMonthDays(today) : buildWeekDays(today)
  }

  const buildTrendSeriesFromApi = (): TrendDay[] => {
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
        count: map.get(key) || 0,
      }
    })
  }

  const buildTrendSeriesFromSubmissions = (): TrendDay[] => {
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
        count: map.get(key) || 0,
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
  const maxTrendCount = computed(() => Math.max(1, ...trendSeries.value.map(day => day.count)))

  const getTrendBarHeight = (count: number) => {
    if (count <= 0) return '6%'
    return `${Math.max(8, Math.round((count / maxTrendCount.value) * 100))}%`
  }

  const trendPoints = computed(() => {
    if (trendSeries.value.length === 0) return []
    const data = trendSeries.value
    const maxCount = Math.max(...data.map(d => d.count), 1)

    return data.map((d, i) => ({
      x: trendChartPaddingX + (i / (data.length - 1 || 1)) * (trendChartWidth.value - trendChartPaddingX * 2),
      y: trendChartHeight - trendChartPaddingY - (d.count / maxCount) * (trendChartHeight - trendChartPaddingY * 2),
      count: d.count,
      date: d.date,
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
      anchor: idx === 0 ? 'start' : (idx === labelPoints.length - 1 ? 'end' : 'middle'),
    }))
  })

  const updateTrendWidth = () => {
    const width = trendContainerRef.value?.clientWidth || 0
    if (width > 0) {
      trendChartWidth.value = width
    }
  }

  const ensureResizeObserver = () => {
    if (typeof ResizeObserver === 'undefined') return
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
  }

  onMounted(() => {
    updateTrendWidth()
    if (typeof ResizeObserver !== 'undefined' && trendContainerRef.value) {
      ensureResizeObserver()
      trendResizeObserver.value?.observe(trendContainerRef.value)
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
      ensureResizeObserver()
      trendResizeObserver.value?.observe(el)
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
      `${i === 0 ? 'M' : 'L'} ${p.x} ${p.y}`,
    ).join(' ')
  })

  const trendAreaPath = computed(() => {
    if (trendPoints.value.length === 0) return ''
    const points = trendPoints.value
    const firstX = points[0]?.x || 0
    const lastX = points[points.length - 1]?.x || trendChartWidth.value
    return `${trendLinePath.value} L ${lastX} ${trendBaselineY} L ${firstX} ${trendBaselineY} Z`
  })

  return {
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
  }
}
