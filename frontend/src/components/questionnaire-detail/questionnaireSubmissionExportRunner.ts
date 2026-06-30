import * as XLSX from 'xlsx'
import type { Questionnaire, Submission } from '../../api/assessments'
import { fetchQuestionnaireAnswerExport, type QuestionnaireQuestionStats } from '../../api/assessments'
import {
  buildAnswerDetailRows,
  buildOptionPersonRows,
  buildQuestionStatsRows,
  buildSubmissionRows,
} from '../../utils/questionnaireSubmissionExport'

interface ExportQuestionnaireSubmissionsOptions {
  format: 'csv' | 'excel'
  questionnaire: Questionnaire | null
  submissions: Submission[]
  questionStats: QuestionnaireQuestionStats | null
  formatDate: (dateStr: string | null | undefined) => string
  getStatusLabel: (status: string) => string
}

export async function exportQuestionnaireSubmissions(options: ExportQuestionnaireSubmissionsOptions) {
  const { format, questionnaire, submissions, questionStats, formatDate, getStatusLabel } = options
  const data = buildSubmissionRows(submissions, questionnaire, formatDate, getStatusLabel)
  const headers = Object.keys(data[0] || {})
  const questionStatsRows = buildQuestionStatsRows(questionStats)
  const questionStatsHeaders = Object.keys(questionStatsRows[0] || {})
  const dateStr = new Date().toISOString().slice(0, 10)
  const fileName = `${questionnaire?.name || '问卷'}_提交记录_${dateStr}`

  if (format === 'csv') {
    const lines = [
      headers.join(','),
      ...data.map(row => headers.map(h => `"${(row as any)[h] || ''}"`).join(',')),
    ]

    if (questionStatsRows.length > 0) {
      lines.push('')
      lines.push('题目统计数据')
      lines.push(questionStatsHeaders.join(','))
      lines.push(
        ...questionStatsRows.map(row => questionStatsHeaders.map(h => `"${(row as any)[h] || ''}"`).join(',')),
      )
    }

    const blob = new Blob(['\uFEFF' + lines.join('\n')], { type: 'text/csv;charset=utf-8;' })
    const link = document.createElement('a')
    link.href = URL.createObjectURL(blob)
    link.download = `${fileName}.csv`
    link.click()
    return
  }

  const workbook = XLSX.utils.book_new()
  XLSX.utils.book_append_sheet(workbook, XLSX.utils.json_to_sheet(data), '提交明细')

  if (questionStatsRows.length > 0) {
    XLSX.utils.book_append_sheet(workbook, XLSX.utils.json_to_sheet(questionStatsRows), '题目统计')
  }

  if (questionnaire?.id) {
    const answerExportData = await fetchQuestionnaireAnswerExport(questionnaire.id)
    const answerDetailRows = buildAnswerDetailRows(answerExportData, formatDate, getStatusLabel)
    const optionPersonRows = buildOptionPersonRows(answerExportData, formatDate)

    if (answerDetailRows.length > 0) {
      XLSX.utils.book_append_sheet(workbook, XLSX.utils.json_to_sheet(answerDetailRows), '答题明细')
    }
    if (optionPersonRows.length > 0) {
      XLSX.utils.book_append_sheet(workbook, XLSX.utils.json_to_sheet(optionPersonRows), '选项人员明细')
    }
  }

  const excelBuffer = XLSX.write(workbook, {
    bookType: 'xlsx',
    type: 'array',
  })
  const blob = new Blob([excelBuffer], {
    type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
  })
  const link = document.createElement('a')
  link.href = URL.createObjectURL(blob)
  link.download = `${fileName}.xlsx`
  link.click()
}
