import type {
  AnswerExportOption,
  AnswerExportQuestion,
  AnswerExportSubmission,
  Questionnaire,
  QuestionnaireAnswerExportData,
  QuestionStat,
  Submission,
} from '../api/assessments'
import type { QuestionnaireQuestionStats } from '../api/assessments'
import { getQuestionTypeText, isTextQuestionType } from './questionnaireQuestionTypes'

type FormatDate = (value?: string | null) => string
type GetStatusLabel = (status: string) => string

export const buildSubmissionRows = (
  submissions: Submission[],
  questionnaire: Questionnaire | null,
  formatDate: FormatDate,
  getStatusLabel: GetStatusLabel
): Array<Record<string, string | number>> => {
  return submissions.map(record => ({
    '姓名': record.candidate_name || '',
    '联系方式': record.candidate_phone || '',
    '问卷': questionnaire?.name || '',
    '得分': record.total_score !== null && record.total_score !== undefined ? record.total_score : '',
    '等级': record.grade || '',
    '状态': getStatusLabel(record.status),
    '提交时间': formatDate(record.submitted_at),
  }))
}

export const buildQuestionStatsRows = (
  questionStats: QuestionnaireQuestionStats | null,
): Array<Record<string, string | number>> => {
  const rows: Array<Record<string, string | number>> = []
  if (!questionStats?.questions?.length) return rows

  questionStats.questions.forEach((question: QuestionStat) => {
    const questionLabel = `Q${question.index}`
    const questionType = getQuestionTypeText(question.type)

    if (question.options?.length) {
      question.options.forEach((option) => {
        rows.push({
          '题号': questionLabel,
          '题目': question.text || '',
          '题型': questionType,
          '选项/答案': option.text || '',
          '人数': option.count ?? 0,
          '占比': `${option.percentage ?? 0}%`,
        })
      })
      return
    }

    const tags = question.text_summary?.tags || []
    const longAnswers = question.text_summary?.long_answers || []
    if (tags.length || longAnswers.length) {
      tags.forEach((item) => {
        rows.push({
          '题号': questionLabel,
          '题目': question.text || '',
          '题型': questionType,
          '选项/答案': `[标签] ${item.text || ''}`,
          '人数': item.count ?? 0,
          '占比': '',
        })
      })
      longAnswers.forEach((item) => {
        rows.push({
          '题号': questionLabel,
          '题目': question.text || '',
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
      '题目': question.text || '',
      '题型': questionType,
      '选项/答案': '(无选项统计)',
      '人数': question.total_answers ?? 0,
      '占比': '',
    })
  })

  return rows
}

const getExportOptionDisplayText = (option: AnswerExportOption, fallbackIndex: number): string => {
  const value = option.text ?? option.label ?? option.value ?? option.index ?? fallbackIndex + 1
  return String(value)
}

const buildExportOptionLabelMap = (question: AnswerExportQuestion): Map<string, string> => {
  const map = new Map<string, string>()
  ;(question.options || []).forEach((option, optionIndex) => {
    const displayText = getExportOptionDisplayText(option, optionIndex)
    const keys = [option.value, option.label, option.text, option.index]

    keys.forEach(key => {
      if (key !== undefined && key !== null && String(key) !== '') {
        const normalizedKey = String(key)
        if (!map.has(normalizedKey)) {
          map.set(normalizedKey, displayText)
        }
      }
    })
  })
  return map
}

const resolveExportAnswerValue = (
  answers: Record<string, any> | undefined,
  question: AnswerExportQuestion
) => {
  const source = answers || {}
  const candidateKeys = [
    question.id,
    String(question.id),
    question.index,
    String(question.index),
    question.index - 1,
    String(question.index - 1),
  ]

  for (const key of candidateKeys) {
    const normalizedKey = String(key)
    if (Object.prototype.hasOwnProperty.call(source, normalizedKey)) {
      return source[normalizedKey]
    }
  }

  return undefined
}

const getExportCustomAnswerTexts = (
  answers: Record<string, any> | undefined,
  question: AnswerExportQuestion
): string[] => {
  const source = answers || {}
  const prefix = `${question.id}_custom`
  return Object.entries(source)
    .filter(([key, value]) =>
      key.startsWith(prefix) &&
      value !== undefined &&
      value !== null &&
      String(value).trim() !== ''
    )
    .map(([, value]) => `其他：${String(value).trim()}`)
}

const formatExportSingleAnswer = (
  value: any,
  optionLabelMap: Map<string, string>
): string => {
  if (value === undefined || value === null || value === '') return ''

  if (typeof value === 'object' && !Array.isArray(value)) {
    const nestedValue = value.value ?? value.label ?? value.text ?? value.answer
    return formatExportSingleAnswer(nestedValue, optionLabelMap)
  }

  const raw = String(value)
  return optionLabelMap.get(raw) || raw
}

export const formatExportAnswerParts = (
  answer: any,
  question: AnswerExportQuestion,
  answers?: Record<string, any>
): string[] => {
  const optionLabelMap = buildExportOptionLabelMap(question)
  const baseParts = Array.isArray(answer)
    ? answer.map(item => formatExportSingleAnswer(item, optionLabelMap))
    : [formatExportSingleAnswer(answer, optionLabelMap)]

  return [...baseParts, ...getExportCustomAnswerTexts(answers, question)]
    .map(item => String(item || '').trim())
    .filter(Boolean)
}

const formatExportAnswerText = (
  submission: AnswerExportSubmission,
  question: AnswerExportQuestion
): string => {
  const answer = resolveExportAnswerValue(submission.answers, question)
  return formatExportAnswerParts(answer, question, submission.answers).join('、')
}

const isExportTextQuestion = (question: AnswerExportQuestion): boolean => {
  return isTextQuestionType(question.type || '')
}

export const buildAnswerDetailRows = (
  exportData: QuestionnaireAnswerExportData,
  formatDate: FormatDate,
  getStatusLabel: GetStatusLabel,
): Array<Record<string, string | number>> => {
  return exportData.submissions.map(submission => {
    const row: Record<string, string | number> = {
      '编号': submission.code || '',
      '姓名': submission.candidate_name || '',
      '手机号': submission.candidate_phone || '',
      '邮箱': submission.candidate_email || '',
      '性别': submission.gender || '',
      '岗位': submission.target_position || '',
      '状态': getStatusLabel(submission.status),
      '提交时间': formatDate(submission.submitted_at || ''),
    }

    exportData.questions.forEach(question => {
      row[`Q${question.index}：${question.text}`] = formatExportAnswerText(submission, question)
    })

    return row
  })
}

export const buildOptionPersonRows = (
  exportData: QuestionnaireAnswerExportData,
  formatDate: FormatDate,
): Array<Record<string, string | number>> => {
  const rows: Array<Record<string, string | number>> = []

  exportData.submissions.forEach(submission => {
    exportData.questions.forEach(question => {
      if (isExportTextQuestion(question)) return

      const answer = resolveExportAnswerValue(submission.answers, question)
      const selectedOptions = formatExportAnswerParts(answer, question, submission.answers)
      selectedOptions.forEach(optionText => {
        rows.push({
          '题号': `Q${question.index}`,
          '题目': question.text || '',
          '题型': getQuestionTypeText(question.type || ''),
          '选项': optionText,
          '编号': submission.code || '',
          '姓名': submission.candidate_name || '',
          '手机号': submission.candidate_phone || '',
          '提交时间': formatDate(submission.submitted_at || ''),
        })
      })
    })
  })

  return rows
}
