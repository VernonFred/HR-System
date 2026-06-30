import { ref } from 'vue'
import type { QuestionStat, TextAnswerGroup, TextSummary } from '../../api/assessments'

export function useQuestionTextAnswers(pageSize = 10) {
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

  const getTextTotalPages = (question: QuestionStat): number => {
    const total = getTextLongAnswers(question).length
    return Math.max(1, Math.ceil(total / pageSize))
  }

  const setTextPage = (question: QuestionStat, page: number) => {
    const totalPages = getTextTotalPages(question)
    const nextPage = Math.min(Math.max(page, 1), totalPages)
    textAnswerPageMap.value = {
      ...textAnswerPageMap.value,
      [question.id]: nextPage,
    }
  }

  const getTextLongAnswerPage = (question: QuestionStat): TextAnswerGroup[] => {
    const page = getTextPage(question)
    const start = (page - 1) * pageSize
    return getTextLongAnswers(question).slice(start, start + pageSize)
  }

  const hasTextSummary = (question: QuestionStat): boolean => {
    const summary = getTextSummary(question)
    return Boolean(
      (summary.tags && summary.tags.length > 0) ||
      (summary.long_answers && summary.long_answers.length > 0) ||
      (summary.empty_count && summary.empty_count > 0),
    )
  }

  const resetTextPages = () => {
    textAnswerPageMap.value = {}
  }

  return {
    getTextSummary,
    getTextTags,
    getTextLongAnswers,
    getTextEmptyCount,
    getTextPage,
    setTextPage,
    getTextTotalPages,
    getTextLongAnswerPage,
    hasTextSummary,
    resetTextPages,
  }
}
