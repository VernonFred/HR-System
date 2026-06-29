export const normalizeQuestionType = (type: string | undefined | null): string => String(type || '').toLowerCase()

const QUESTION_TYPE_LABELS: Record<string, string> = {
  single: '单选',
  radio: '单选',
  single_choice: '单选',
  multiple: '多选',
  checkbox: '多选',
  multiple_choice: '多选',
  text: '文本',
  textarea: '文本',
  short_text: '文本',
  long_text: '文本',
  scale: '量表',
  rating: '评分',
  yesno: '是非',
  yes_no: '是非',
  choice: '选择',
}

export const getQuestionTypeLabel = (type: string): string => {
  return QUESTION_TYPE_LABELS[normalizeQuestionType(type)] || type
}

export const getQuestionTypeText = getQuestionTypeLabel

export const isTextQuestionType = (type: string): boolean => {
  return ['text', 'textarea', 'short_text', 'long_text'].includes(normalizeQuestionType(type))
}

export const isSingleChoiceQuestionType = (type: string): boolean => {
  return ['single', 'radio', 'single_choice', 'yesno', 'yes_no', 'choice'].includes(normalizeQuestionType(type))
}

export const isMultipleChoiceQuestionType = (type: string): boolean => {
  return ['multiple', 'checkbox', 'multiple_choice'].includes(normalizeQuestionType(type))
}

export const isScaleQuestionType = (type: string): boolean => {
  return ['scale', 'rating'].includes(normalizeQuestionType(type))
}
