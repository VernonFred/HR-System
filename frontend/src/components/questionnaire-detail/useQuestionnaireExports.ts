import { nextTick, ref, type ComputedRef, type Ref } from 'vue'
import { type EChartsOption, type SetOptionOpts } from 'echarts/core'
import type { Questionnaire, QuestionStat, Submission } from '../../api/assessments'
import { type QuestionnaireQuestionStats } from '../../api/assessments'
import { isTextQuestionType as isTextQuestion } from '../../utils/questionnaireQuestionTypes'
import { exportQuestionnaireSubmissions } from './questionnaireSubmissionExportRunner'
import { exportStatsAsExcel } from './questionnaireStatsExcelExport'
import { delay, downloadBlob, downloadHref, pad2, sanitizeFileName } from './questionnaireExportFiles'
import { renderQuestionChartImage } from './questionnaireChartImageExport'

type GradeDistribution = { A: number; B: number; C: number; D: number }

type TrendDay = { date: string; count: number }

type UseQuestionnaireExportsOptions = {
  questionnaire: ComputedRef<Questionnaire | null>
  submissions: ComputedRef<Submission[]>
  questionStats: Ref<QuestionnaireQuestionStats | null>
  loadQuestionStats: () => Promise<void>
  formatDate: (dateStr: string | null | undefined) => string
  getStatusLabel: (status: string) => string
  actualSubmissionCount: ComputedRef<number>
  averageScore: ComputedRef<number>
  completedSubmissions: ComputedRef<Submission[]>
  gradeDistribution: ComputedRef<GradeDistribution>
  isScored: ComputedRef<boolean>
  trendRangeLabel: ComputedRef<string>
  trendSeries: ComputedRef<TrendDay[]>
  formatTrendDate: (date: string) => string
  getTextTags: (question: QuestionStat) => Array<{ text: string; count: number }>
  getTextLongAnswers: (question: QuestionStat) => Array<{ text: string; count: number }>
  getTextEmptyCount: (question: QuestionStat) => number
  questionChartSetOptionOpts: SetOptionOpts
  getQuestionChartHeight: (question: QuestionStat) => number
  getQuestionVisualOption: (question: QuestionStat) => EChartsOption
  getQuestionExportChartKey: (question: QuestionStat) => string
}

export function useQuestionnaireExports(options: UseQuestionnaireExportsOptions) {
  const {
    questionnaire,
    submissions,
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
  } = options

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
  const statsExportReportRef = ref<{ getElement: () => HTMLElement | null } | null>(null)
  const statsExportChartImages = ref<Record<string, string>>({})
  const showStatsExportToast = ref(false)
  const statsExportToastMessage = ref('')
  const statsExportToastType = ref<'success' | 'error'>('success')

  const openExportModal = () => {
    if (submissions.value.length === 0) {
      showExportSuccessToast.value = true
      setTimeout(() => { showExportSuccessToast.value = false }, 2000)
      return
    }
    showExportModal.value = true
  }

  const closeExportModal = () => {
    showExportModal.value = false
  }

  const executeExport = async () => {
    exportLoading.value = true

    try {
      if (!questionStats.value && questionnaire.value?.id) {
        await loadQuestionStats()
      }

      await exportQuestionnaireSubmissions({
        format: exportFormat.value,
        questionnaire: questionnaire.value,
        submissions: submissions.value,
        questionStats: questionStats.value,
        formatDate,
        getStatusLabel,
      })

      showExportModal.value = false
      showExportSuccessToast.value = true
      setTimeout(() => { showExportSuccessToast.value = false }, 3000)
    } catch (error) {
      console.error('导出失败:', error)
      alert('导出失败，请检查网络连接或稍后重试')
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
    if (!questionStats.value && questionnaire.value?.id) {
      await loadQuestionStats()
    }

    if (!hasStatsExportData()) {
      showStatsExportMessage('暂无可导出的统计数据', 'error')
      return
    }

    showStatsExportModal.value = true
  }

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

  const getStatsExportBaseName = () => {
    return sanitizeFileName(`${questionnaire.value?.name || '问卷'}_统计报告_${getExportDateKey()}`)
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

  const runStatsExcelExport = () => {
    exportStatsAsExcel({
      questionnaire: questionnaire.value,
      questionStats: questionStats.value,
      exportDateText: getExportDateText(),
      actualSubmissionCount: actualSubmissionCount.value,
      averageScore: averageScore.value,
      gradeDistribution: gradeDistribution.value,
      completedSubmissions: completedSubmissions.value,
      isScored: isScored.value,
      trendRangeLabel: trendRangeLabel.value,
      trendSeries: trendSeries.value,
      formatTrendDate,
      getTextTags,
      getTextLongAnswers,
      getTextEmptyCount,
      baseName: getStatsExportBaseName(),
      downloadBlob,
    })
  }

  const prepareStatsExportChartImages = async () => {
    const questions = questionStats.value?.questions || []
    const imageMap: Record<string, string> = {}

    for (const question of questions) {
      if (isTextQuestion(question.type) || question.options.length === 0) continue
      const key = getQuestionExportChartKey(question)
      try {
        imageMap[key] = await renderQuestionChartImage(question, {
          questionChartSetOptionOpts,
          getQuestionChartHeight,
          getQuestionVisualOption,
        })
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
    const element = statsExportReportRef.value?.getElement()
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
      if (!questionStats.value && questionnaire.value?.id) {
        await loadQuestionStats()
      }

      if (!hasStatsExportData()) {
        showStatsExportMessage('暂无可导出的统计数据', 'error')
        return
      }

      if (statsExportFormat.value === 'excel') {
        runStatsExcelExport()
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

  return {
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
  }
}
