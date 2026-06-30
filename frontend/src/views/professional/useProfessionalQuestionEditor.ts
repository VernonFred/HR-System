import { computed, ref } from 'vue'
import type { EditorQuestion } from '../../components/QuestionEditDialog.vue'

export function useProfessionalQuestionEditor(editQuestionnaireForm: { value: { type?: string } }) {
  // ===== 题目编辑 =====
  const editorQuestions = ref<EditorQuestion[]>([])
  const showQuestionEditDialog = ref(false)
  const editingQuestionIndex = ref<number | null>(null)
  const editingQuestion = ref<EditorQuestion | null>(null)
  const questionsLoading = ref(false)
  const editStep = ref<'info' | 'questions'>('info')

  // 控件库配置
  const questionControls: Array<{ type: EditorQuestion['type']; label: string; icon: string }> = [
    { type: 'radio', label: '单选题', icon: 'ri-radio-button-line' },
    { type: 'checkbox', label: '多选题', icon: 'ri-checkbox-line' },
    { type: 'text', label: '单行文本', icon: 'ri-input-field' },
    { type: 'textarea', label: '多行文本', icon: 'ri-text' },
    { type: 'scale', label: '量表题', icon: 'ri-equalizer-line' },
    { type: 'yesno', label: '是非题', icon: 'ri-question-answer-line' },
    { type: 'choice', label: '二选一', icon: 'ri-arrow-left-right-line' },
  ]

  // 分页状态
  const questionsPageSize = ref(6)
  const questionsCurrentPage = ref(1)

  // 拖拽状态
  const isDragOver = ref(false)

  // 分页计算
  const paginatedQuestions = computed(() => {
    const start = (questionsCurrentPage.value - 1) * questionsPageSize.value
    const end = start + questionsPageSize.value
    return editorQuestions.value.slice(start, end)
  })

  const totalPages = computed(() => {
    return Math.ceil(editorQuestions.value.length / questionsPageSize.value) || 1
  })

  // 智能分页
  const visiblePages = computed(() => {
    const total = totalPages.value
    const current = questionsCurrentPage.value

    if (total <= 7) {
      return Array.from({ length: total }, (_, i) => i + 1)
    }

    const pages: (number | string)[] = []
    pages.push(1)

    if (current > 3) {
      pages.push('...')
    }

    const start = Math.max(2, current - 1)
    const end = Math.min(total - 1, current + 1)

    for (let i = start; i <= end; i++) {
      if (!pages.includes(i)) {
        pages.push(i)
      }
    }

    if (current < total - 2) {
      pages.push('...')
    }

    if (!pages.includes(total)) {
      pages.push(total)
    }

    return pages
  })

  // 分页操作
  const goToPage = (page: number) => {
    if (page >= 1 && page <= totalPages.value) {
      questionsCurrentPage.value = page
    }
  }

  const goToVisiblePage = (page: number | string) => {
    if (typeof page === 'number') {
      goToPage(page)
    }
  }

  // 获取全局索引
  const getGlobalIndex = (localIndex: number) => {
    return (questionsCurrentPage.value - 1) * questionsPageSize.value + localIndex
  }

  // 获取题型名称
  const getQuestionTypeName = (type: string) => {
    const ctrl = questionControls.find(c => c.type === type)
    return ctrl?.label || type
  }

  const editAssessmentType = computed<'MBTI' | 'DISC' | 'EPQ' | null>(() => {
    const type = editQuestionnaireForm.value.type?.toUpperCase()
    return type === 'MBTI' || type === 'DISC' || type === 'EPQ' ? type : null
  })

  // 生成唯一ID
  const generateQuestionId = () => {
    return `q_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
  }

  // 从控件添加题目
  const addQuestionFromControl = (type: EditorQuestion['type']) => {
    const question: EditorQuestion = {
      id: generateQuestionId(),
      type,
      text: `请输入${getQuestionTypeName(type)}内容`,
      required: true,
    }

    if (type === 'radio' || type === 'checkbox') {
      question.options = [
        { label: '选项1', score: 0 },
        { label: '选项2', score: 0 },
      ]
    } else if (type === 'choice') {
      question.optionA = '选项A'
      question.optionB = '选项B'
    }

    editorQuestions.value.push(question)
    // 跳转到最后一页
    questionsCurrentPage.value = totalPages.value
  }

  // 拖拽处理
  const handleControlDragStart = (event: DragEvent, type: string) => {
    event.dataTransfer?.setData('questionType', type)
  }

  const handleControlDragEnd = () => {
    isDragOver.value = false
  }

  const handleListDragOver = () => {
    isDragOver.value = true
  }

  const handleListDrop = (event: DragEvent) => {
    isDragOver.value = false
    const type = event.dataTransfer?.getData('questionType')
    if (type) {
      addQuestionFromControl(type as EditorQuestion['type'])
    }
  }


  return {
    editorQuestions, showQuestionEditDialog, editingQuestionIndex, editingQuestion, questionsLoading, editStep, questionControls, questionsPageSize, questionsCurrentPage, isDragOver, paginatedQuestions, totalPages, visiblePages, goToPage, goToVisiblePage, getGlobalIndex, getQuestionTypeName, editAssessmentType, generateQuestionId, addQuestionFromControl, handleControlDragStart, handleControlDragEnd, handleListDragOver, handleListDrop
  }
}
