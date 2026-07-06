import type { EditorQuestion } from './QuestionEditDialog.vue'

export const questionControls: Array<{ type: EditorQuestion['type']; label: string; icon: string }> = [
  { type: 'radio', label: '单选题', icon: 'ri-radio-button-line' },
  { type: 'checkbox', label: '多选题', icon: 'ri-checkbox-line' },
  { type: 'text', label: '单行文本', icon: 'ri-input-field' },
  { type: 'textarea', label: '多行文本', icon: 'ri-text' },
  { type: 'scale', label: '量表题', icon: 'ri-equalizer-line' },
  { type: 'yesno', label: '是非题', icon: 'ri-question-answer-line' },
  { type: 'choice', label: '二选一', icon: 'ri-arrow-left-right-line' },
]

export const createDefaultQuestionnaireForm = () => ({
  name: '',
  creator: '',
  type: 'CUSTOM',
  category: 'scored',
  description: '',
  estimated_minutes: 10,
  purpose: 'survey' as 'survey' | 'assessment',
  simpleScoring: {
    totalScore: 100,
    passingScore: 60,
  },
  gradeConfig: [
    { grade: 'A', label: '优秀', minScore: 90, maxScore: 100 },
    { grade: 'B', label: '良好', minScore: 75, maxScore: 89 },
    { grade: 'C', label: '中等', minScore: 60, maxScore: 74 },
    { grade: 'D', label: '待提升', minScore: 0, maxScore: 59 },
  ],
})

export const mapImportedQuestionType = (importType: string): string => {
  const typeMap: Record<string, string> = {
    single: 'radio',
    multiple: 'checkbox',
    text: 'text',
    textarea: 'textarea',
    rating: 'scale',
  }
  return typeMap[importType] || 'radio'
}
