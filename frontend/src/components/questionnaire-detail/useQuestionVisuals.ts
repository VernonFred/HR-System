import { ref } from 'vue'
import type { EChartsOption, SetOptionOpts } from 'echarts/core'
import type { QuestionOptionStat, QuestionStat } from '../../api/assessments'
import {
  isMultipleChoiceQuestionType as isMultipleChoiceQuestion,
  isScaleQuestionType as isScaleQuestion,
  isSingleChoiceQuestionType as isSingleChoiceQuestion,
} from '../../utils/questionnaireQuestionTypes'

type OptionSortMode = 'default' | 'asc' | 'desc'

const QUESTION_CHART_COLORS = ['#38a3d8', '#60d5d8', '#ffdc5a', '#ff9b78', '#8b5cf6', '#22c55e', '#f97316', '#64748b']

export function useQuestionVisuals() {
  const questionChartSetOptionOpts: SetOptionOpts = { notMerge: true }
  const questionChartModeMap = ref<Record<string, 'pie' | 'bar'>>({})
  const optionSortModeMap = ref<Record<string, OptionSortMode>>({})

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

  const getQuestionKey = (question: QuestionStat): string => String(question.id || question.index)

  const getQuestionChartMode = (question: QuestionStat): 'pie' | 'bar' => {
    return questionChartModeMap.value[question.id] || 'pie'
  }

  const setQuestionChartMode = (question: QuestionStat, mode: 'pie' | 'bar') => {
    questionChartModeMap.value = {
      ...questionChartModeMap.value,
      [question.id]: mode,
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

  return {
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
  }
}
