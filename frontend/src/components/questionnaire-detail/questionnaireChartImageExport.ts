import { init, type ECharts, type EChartsOption, type SetOptionOpts } from 'echarts/core'
import type { QuestionStat } from '../../api/assessments'
import { delay } from './questionnaireExportFiles'

interface RenderQuestionChartImageOptions {
  questionChartSetOptionOpts: SetOptionOpts
  getQuestionChartHeight: (question: QuestionStat) => number
  getQuestionVisualOption: (question: QuestionStat) => EChartsOption
}

const disposeChartSafely = (chart: ECharts | null) => {
  if (!chart) return
  try {
    chart.dispose()
  } catch (error) {
    console.warn('销毁统计导出图表失败:', error)
  }
}

export async function renderQuestionChartImage(
  question: QuestionStat,
  options: RenderQuestionChartImageOptions,
) {
  if (!question.options.length) return ''

  const width = 460
  const height = Math.max(220, options.getQuestionChartHeight(question))
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
    chart = init(host, 'light', { renderer: 'canvas', width, height })
    chart.setOption({
      ...options.getQuestionVisualOption(question),
      animation: false,
    } as EChartsOption, options.questionChartSetOptionOpts)
    await delay(80)
    return chart.getDataURL({ type: 'png', pixelRatio: 2, backgroundColor: '#ffffff' })
  } finally {
    disposeChartSafely(chart)
    host.remove()
  }
}
