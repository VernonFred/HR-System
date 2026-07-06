import * as XLSX from 'xlsx'
import type { QuestionStat, Questionnaire, Submission } from '../../api/assessments'
import type { QuestionnaireQuestionStats } from '../../api/assessments'
import { isTextQuestionType as isTextQuestion } from '../../utils/questionnaireQuestionTypes'
import { buildQuestionStatsRows } from '../../utils/questionnaireSubmissionExport'
import type { DistributionRow, ScoringDisplayConfig } from '../../utils/scoringDisplayConfig'

type GradeDistribution = { A: number; B: number; C: number; D: number }
type TrendDay = { date: string; count: number }

interface ExportStatsAsExcelOptions {
  questionnaire: Questionnaire | null
  questionStats: QuestionnaireQuestionStats | null
  exportDateText: string
  actualSubmissionCount: number
  averageScore: number
  gradeDistribution: GradeDistribution
  scoringDisplayConfig: ScoringDisplayConfig
  distributionRows: DistributionRow[]
  completedSubmissions: Submission[]
  isScored: boolean
  trendRangeLabel: string
  trendSeries: TrendDay[]
  formatTrendDate: (date: string) => string
  getTextTags: (question: QuestionStat) => Array<{ text: string; count: number }>
  getTextLongAnswers: (question: QuestionStat) => Array<{ text: string; count: number }>
  getTextEmptyCount: (question: QuestionStat) => number
  baseName: string
  downloadBlob: (blob: Blob, fileName: string) => void
}

const getStatsOverviewRows = (options: ExportStatsAsExcelOptions) => {
  const averageScore = options.questionStats?.score_summary?.average_score
    ?? options.questionStats?.average_score
    ?? null
  const rows = [
    { '指标': '问卷名称', '数值': options.questionnaire?.name || options.questionStats?.questionnaire_name || '' },
    { '指标': '导出时间', '数值': options.exportDateText },
    { '指标': '参与人数', '数值': options.actualSubmissionCount },
    { '指标': '完成率', '数值': `${options.actualSubmissionCount > 0 ? (options.questionStats?.completion_rate ?? 100) : 0}%` },
    { '指标': '题目数', '数值': options.questionStats?.questions.length || 0 },
    { '指标': options.isScored ? options.scoringDisplayConfig.averageLabel : '平均分', '数值': averageScore ?? '' },
  ]
  const summary = options.questionStats?.score_summary
  if (options.isScored && summary) {
    rows.push(
      { '指标': `已计分${options.scoringDisplayConfig.unitLabel}`, '数值': summary.scored_submission_count },
      { '指标': options.scoringDisplayConfig.rateLabel, '数值': summary.high_score_rate != null ? `${summary.high_score_rate}%` : '' },
      { '指标': '最高分', '数值': summary.highest_score ?? '' },
      { '指标': '最低分', '数值': summary.lowest_score ?? '' },
      { '指标': '平均得分率', '数值': summary.average_percentage != null ? `${summary.average_percentage}%` : '' },
    )
  }
  rows.push(
    { '指标': '平均用时', '数值': options.questionStats?.average_duration_minutes ? `${options.questionStats.average_duration_minutes}分钟` : '' },
    { '指标': '趋势范围', '数值': options.trendRangeLabel },
  )
  return rows
}

const getStatsTrendRows = (options: ExportStatsAsExcelOptions) => {
  return options.trendSeries.map(day => ({
    '日期': day.date,
    '显示日期': options.formatTrendDate(day.date),
    '提交数': day.count,
  }))
}

const getStatsGradeRows = (options: ExportStatsAsExcelOptions) => {
  const scoredTotal = options.questionStats?.score_summary?.scored_submission_count ?? 0
  return options.distributionRows.map(item => {
    const count = options.gradeDistribution[item.grade as keyof GradeDistribution] || 0
    const percentage = scoredTotal > 0
      ? Math.round(count / scoredTotal * 100)
      : 0
    return {
      '等级': item.grade,
      '分数区间': `${item.minScore}-${item.maxScore}`,
      '说明': item.label,
      [`数量(${options.scoringDisplayConfig.unitLabel})`]: count,
      '占比': `${percentage}%`,
    }
  })
}

const getStatsTextRows = (options: ExportStatsAsExcelOptions) => {
  const rows: Array<Record<string, string | number>> = []
  options.questionStats?.questions
    .filter(q => isTextQuestion(q.type))
    .forEach(q => {
      options.getTextTags(q).forEach(item => {
        rows.push({ '题号': `Q${q.index}`, '题目': q.text || '', '类型': '关键词标签', '内容': item.text || '', '次数': item.count || 0 })
      })
      if (options.getTextEmptyCount(q) > 0) {
        rows.push({ '题号': `Q${q.index}`, '题目': q.text || '', '类型': '无/没有意见', '内容': '无/没有意见', '次数': options.getTextEmptyCount(q) })
      }
      options.getTextLongAnswers(q).forEach(item => {
        rows.push({ '题号': `Q${q.index}`, '题目': q.text || '', '类型': '代表性回答', '内容': item.text || '', '次数': item.count || 0 })
      })
    })
  return rows
}

export function exportStatsAsExcel(options: ExportStatsAsExcelOptions) {
  const workbook = XLSX.utils.book_new()
  XLSX.utils.book_append_sheet(workbook, XLSX.utils.json_to_sheet(getStatsOverviewRows(options)), '统计概览')
  XLSX.utils.book_append_sheet(workbook, XLSX.utils.json_to_sheet(getStatsTrendRows(options)), '提交趋势')

  if (options.isScored && options.questionStats?.score_summary) {
    XLSX.utils.book_append_sheet(
      workbook,
      XLSX.utils.json_to_sheet(getStatsGradeRows(options)),
      options.scoringDisplayConfig.distributionTitle.slice(0, 31),
    )
  }

  const questionRows = buildQuestionStatsRows(options.questionStats)
  if (questionRows.length > 0) {
    XLSX.utils.book_append_sheet(workbook, XLSX.utils.json_to_sheet(questionRows), '题目统计')
  }

  const textRows = getStatsTextRows(options)
  if (textRows.length > 0) {
    XLSX.utils.book_append_sheet(workbook, XLSX.utils.json_to_sheet(textRows), '文本题汇总')
  }

  const excelBuffer = XLSX.write(workbook, {
    bookType: 'xlsx',
    type: 'array',
  })
  options.downloadBlob(
    new Blob([excelBuffer], {
      type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    }),
    `${options.baseName}.xlsx`,
  )
}
