<script setup lang="ts">
/**
 * 问卷编辑器弹窗
 *
 * 功能：
 * 1. 创建新问卷
 * 2. 编辑现有问卷
 * 3. 题目管理（添加/编辑/删除/排序）
 * 4. 评分配置
 * 5. 候选人视角预览
 */
import { ref, computed, onMounted, watch } from 'vue'
import { useAuthStore } from '../stores/auth'
import CandidatePreviewPanel from './CandidatePreviewPanel.vue'
import QuestionEditDialog, { type EditorQuestion } from './QuestionEditDialog.vue'
import QuestionnaireLibraryManager from './QuestionnaireLibraryManager.vue'
import QuestionnaireTagPicker from './QuestionnaireTagPicker.vue'
import { createDefaultQuestionnaireForm, mapImportedQuestionType, questionControls } from './questionnaireEditorConfig'
import {
  buildScoringDisplayConfig,
  createDefaultDisplayConfig,
  createDefaultGradeConfig,
  normalizeGradeConfig,
  type ScoringDisplayPreset,
} from '../utils/scoringDisplayConfig'
import {
  createQuestionnaire,
  updateQuestionnaire,
  fetchQuestionnaireDetail,
  fetchQuestionnaireLibraryCategories,
  fetchQuestionnaireTags,
  type Questionnaire,
  type QuestionnaireCreate,
  type QuestionnaireDetail,
  type QuestionnaireImportResponse,
  type QuestionnaireLibraryCategorySummary,
  type QuestionnaireTagSummary,
} from '../api/assessments'

// ===== Props =====
const props = defineProps<{
  questionnaire: Questionnaire | null
  importedData?: QuestionnaireImportResponse | null  // V43: 导入的问卷数据
}>()

// ===== Emits =====
const emit = defineEmits<{
  (e: 'close'): void
  (e: 'save'): void
}>()

// ===== 状态 =====
const isEdit = computed(() => !!props.questionnaire)
const loading = ref(false)
const editorStep = ref<'info' | 'questions'>('info')
const authStore = useAuthStore()
const questionsMeta = ref<Record<string, any>>({})
const libraryCategories = ref<QuestionnaireLibraryCategorySummary[]>([])
const libraryTags = ref<QuestionnaireTagSummary[]>([])
const libraryCategoryId = ref<number | null>(null)
const selectedTagIds = ref<number[]>([])
const originalLibraryCategoryId = ref<number | null>(null)
const originalTagIds = ref<number[]>([])
const originalTechnicalCategory = ref<string | null>(null)
const libraryLoading = ref(false)
const libraryError = ref('')
const showLibraryManager = ref(false)

const form = ref(createDefaultQuestionnaireForm())

const scoringEnabled = ref(true)

const displayPresetOptions: Array<{
  preset: ScoringDisplayPreset
  title: string
  icon: string
}> = [
  { preset: 'survey_feedback', title: '课程/服务反馈', icon: 'ri-feedback-line' },
  { preset: 'assessment_rating', title: '人员测评', icon: 'ri-user-star-line' },
  { preset: 'exam_score', title: '考试成绩', icon: 'ri-file-list-2-line' },
  { preset: 'custom', title: '自定义', icon: 'ri-edit-2-line' },
]

const setScoringEnabled = (enabled: boolean) => {
  scoringEnabled.value = enabled
  form.value.category = enabled ? 'scored' : 'survey'
  if (!enabled || !form.value.purpose) {
    form.value.purpose = 'survey'
  }
}

const getPurposeForPreset = (preset: ScoringDisplayPreset) => {
  if (preset === 'assessment_rating') return 'assessment'
  if (preset === 'exam_score') return 'exam'
  return 'survey'
}

const setDisplayPreset = (preset: ScoringDisplayPreset) => {
  form.value.displayConfig = {
    ...createDefaultDisplayConfig(getPurposeForPreset(preset)),
    preset,
  }
  if (preset !== 'custom') {
    form.value.purpose = getPurposeForPreset(preset)
    form.value.gradeConfig = createDefaultGradeConfig(form.value.purpose)
  }
}

const buildScoringConfig = () => {
  const totalScore = form.value.simpleScoring.totalScore
  const passingScore = form.value.simpleScoring.passingScore
  const grades = form.value.gradeConfig.map(item => ({
    name: item.grade,
    label: item.label,
    min_score: item.minScore,
    max_score: item.maxScore,
  }))

  if (!scoringEnabled.value) {
    return {
      enabled: false,
      total_score: totalScore,
      passing_score: passingScore,
      grades: [],
      displayConfig: form.value.displayConfig,
    }
  }

  return {
    enabled: true,
    method: 'auto',
    total_score: totalScore,
    passing_score: passingScore,
    grades,
    displayConfig: form.value.displayConfig,
    totalScore,
    passingScore,
    gradeConfig: form.value.gradeConfig,
  }
}

const applyScoringConfig = (scoringConfig: any) => {
  const totalScore = scoringConfig?.total_score ?? scoringConfig?.totalScore
  const passingScore = scoringConfig?.passing_score ?? scoringConfig?.passingScore
  const gradeConfig = normalizeGradeConfig(scoringConfig, form.value.purpose).map((item, index) => ({
    grade: item.grade ?? item.name ?? String.fromCharCode(65 + index),
    label: item.label ?? '',
    minScore: item.minScore ?? item.min_score,
    maxScore: item.maxScore ?? item.max_score,
  }))
  if (totalScore != null) form.value.simpleScoring.totalScore = totalScore
  if (passingScore != null) form.value.simpleScoring.passingScore = passingScore
  if (Array.isArray(gradeConfig) && gradeConfig.length > 0) {
    form.value.gradeConfig = gradeConfig
  }
  form.value.displayConfig = buildScoringDisplayConfig({
    purpose: form.value.purpose,
    scoringConfig,
  })
}

// 题目列表
const editorQuestions = ref<EditorQuestion[]>([])

// 分页状态
const questionsPageSize = ref(6)  // 每页显示数量
const questionsCurrentPage = ref(1)  // 当前页码

// 拖拽状态
const isDragOver = ref(false)

// 添加/编辑题目弹窗
const showAddQuestionModal = ref(false)
const editingQuestionIndex = ref<number | null>(null)
const editingQuestion = ref<EditorQuestion | null>(null)

// 删除题目确认弹窗
const showDeleteQuestionModal = ref(false)
const deleteQuestionIndex = ref<number | null>(null)

// 预览状态
const previewIndex = ref(0)
const previewAnswer = ref('')
const previewAnswerMulti = ref<string[]>([])
const previewScaleValue = ref<number | null>(null)
const previewYesno = ref('')
const previewChoice = ref('')

// ===== 计算属性 =====
const selectedLibraryCategory = computed(() => (
  libraryCategories.value.find(category => category.id === libraryCategoryId.value) || null
))

const selectableLibraryCategories = computed(() => libraryCategories.value.filter(category => (
  (category.is_active && !category.is_system)
    || (isEdit.value && category.id === originalLibraryCategoryId.value)
)))

const hasValidLibraryCategory = computed(() => {
  const category = selectedLibraryCategory.value
  if (!category) return false
  if (category.is_active && !category.is_system) return true
  return isEdit.value && category.id === originalLibraryCategoryId.value
})

const canGoNext = computed(() => (
  form.value.name.trim() !== '' && hasValidLibraryCategory.value
))

// 分页计算
const paginatedQuestions = computed(() => {
  const start = (questionsCurrentPage.value - 1) * questionsPageSize.value
  const end = start + questionsPageSize.value
  return editorQuestions.value.slice(start, end)
})

const totalPages = computed(() => {
  return Math.ceil(editorQuestions.value.length / questionsPageSize.value) || 1
})

// 智能分页：当页数多时折叠显示
const visiblePages = computed(() => {
  const total = totalPages.value
  const current = questionsCurrentPage.value

  if (total <= 7) {
    // 页数少于7，全部显示
    return Array.from({ length: total }, (_, i) => i + 1)
  }

  const pages: (number | string)[] = []

  // 始终显示第一页
  pages.push(1)

  if (current > 3) {
    pages.push('...')
  }

  // 显示当前页附近的页码
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

  // 始终显示最后一页
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

// 监听题目数量变化，自动调整当前页
watch(() => editorQuestions.value.length, (newLength) => {
  const maxPage = Math.ceil(newLength / questionsPageSize.value) || 1
  if (questionsCurrentPage.value > maxPage) {
    questionsCurrentPage.value = maxPage
  }
})

// ===== 方法 =====
const close = () => {
  emit('close')
}

const goToInfoStep = () => {
  editorStep.value = 'info'
}

const goToQuestionsStep = () => {
  if (!canGoNext.value) return
  editorStep.value = 'questions'
}

const mergeLibraryCategory = (category?: QuestionnaireLibraryCategorySummary | null) => {
  if (!category || libraryCategories.value.some(item => item.id === category.id)) return
  libraryCategories.value.push(category)
}

const mergeLibraryTags = (tags: QuestionnaireTagSummary[] = []) => {
  const knownIds = new Set(libraryTags.value.map(tag => tag.id))
  libraryTags.value.push(...tags.filter(tag => !knownIds.has(tag.id)))
}

const loadQuestionnaireLibraryOptions = async () => {
  libraryLoading.value = true
  libraryError.value = ''
  try {
    const [categories, tags] = await Promise.all([
      fetchQuestionnaireLibraryCategories(),
      fetchQuestionnaireTags(),
    ])
    libraryCategories.value = [...categories].sort((a, b) => a.sort_order - b.sort_order || a.id - b.id)
    libraryTags.value = tags
  } catch (error) {
    console.error('加载问卷分类失败:', error)
    libraryError.value = '分类与标签加载失败，请重试'
  } finally {
    libraryLoading.value = false
  }
}

const handleLibraryChanged = async () => {
  const currentCategory = selectedLibraryCategory.value
  const currentTags = selectedTagIds.value
    .map(tagId => libraryTags.value.find(tag => tag.id === tagId))
    .filter((tag): tag is QuestionnaireTagSummary => !!tag)
  await loadQuestionnaireLibraryOptions()
  mergeLibraryCategory(currentCategory)
  mergeLibraryTags(currentTags)
}

const handleTagCreated = (tag: QuestionnaireTagSummary) => {
  mergeLibraryTags([tag])
}

// 获取题型名称
const getQuestionTypeName = (type: string) => {
  const ctrl = questionControls.find(c => c.type === type)
  return ctrl?.label || type
}

// 获取全局索引（基于分页）
const getGlobalIndex = (localIndex: number) => {
  return (questionsCurrentPage.value - 1) * questionsPageSize.value + localIndex
}

// 生成唯一ID
const generateId = () => {
  return `q_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
}

// 从控件添加题目
const addQuestionFromDrag = (rawType: string) => {
  const type = rawType as EditorQuestion['type']
  const question: EditorQuestion = {
    id: generateId(),
    type,
    text: `请输入${getQuestionTypeName(type)}内容`,
    required: true,
  }

  if (type === 'radio' || type === 'checkbox') {
    question.options = [
      { label: '选项1', value: 'opt1' },
      { label: '选项2', value: 'opt2' },
      ]
      if (type === 'checkbox') {
        question.selectionRule = 'none'
        question.minSelections = null
        question.maxSelections = null
      }
  } else if (type === 'scale') {
    question.scale = { min: 1, max: 5, minLabel: '非常不满意', maxLabel: '非常满意' }
  } else if (type === 'choice') {
    question.optionA = '选项A'
    question.optionB = '选项B'
  }

  editorQuestions.value.push(question)
  previewIndex.value = editorQuestions.value.length - 1
}

// 打开添加题目弹窗
const openAddQuestionModal = () => {
  editingQuestionIndex.value = null
  editingQuestion.value = null
  showAddQuestionModal.value = true
}

// 打开编辑题目弹窗
const openEditQuestionModal = (index: number) => {
  editingQuestionIndex.value = index
  editingQuestion.value = editorQuestions.value[index]
  showAddQuestionModal.value = true
}

// 保存题目（从子组件接收）
const handleSaveQuestion = (question: EditorQuestion) => {
  if (editingQuestionIndex.value !== null) {
    editorQuestions.value[editingQuestionIndex.value] = question
  } else {
    editorQuestions.value.push(question)
  }
  showAddQuestionModal.value = false
}

// 打开删除题目确认弹窗
const openDeleteQuestionModal = (index: number) => {
  deleteQuestionIndex.value = index
  showDeleteQuestionModal.value = true
}

// 确认删除题目
const confirmDeleteQuestion = () => {
  if (deleteQuestionIndex.value !== null) {
    editorQuestions.value.splice(deleteQuestionIndex.value, 1)
    if (previewIndex.value >= editorQuestions.value.length) {
      previewIndex.value = Math.max(0, editorQuestions.value.length - 1)
    }
  }
  showDeleteQuestionModal.value = false
  deleteQuestionIndex.value = null
}

// 取消删除题目
const cancelDeleteQuestion = () => {
  showDeleteQuestionModal.value = false
  deleteQuestionIndex.value = null
}

// 移动题目
const moveQuestion = (index: number, direction: 'up' | 'down') => {
  const newIndex = direction === 'up' ? index - 1 : index + 1
  if (newIndex < 0 || newIndex >= editorQuestions.value.length) return

  const temp = editorQuestions.value[index]
  editorQuestions.value[index] = editorQuestions.value[newIndex]
  editorQuestions.value[newIndex] = temp
}


// 拖拽处理
const handleControlDragStart = (e: DragEvent, type: string) => {
  if (e.dataTransfer) {
    e.dataTransfer.setData('questionType', type)
  }
}

const handleControlDragEnd = () => {
  isDragOver.value = false
}

const handleListDragOver = (e: DragEvent) => {
  isDragOver.value = true
}

const handleListDrop = (e: DragEvent) => {
  isDragOver.value = false
  if (e.dataTransfer) {
    const type = e.dataTransfer.getData('questionType') as EditorQuestion['type']
    if (type) {
      addQuestionFromDrag(type)
    }
  }
}

// 保存问卷
const save = async () => {
  if (!form.value.name.trim()) {
    alert('请输入问卷名称')
    return
  }
  if (!hasValidLibraryCategory.value) {
    alert('请选择有效的问卷主分类')
    editorStep.value = 'info'
    return
  }
  if (selectedTagIds.value.length > 10) {
    alert('每份问卷最多选择 10 个标签')
    editorStep.value = 'info'
    return
  }

  loading.value = true
  try {
    // 构建问卷数据
    const questionsData = editorQuestions.value.map((q, idx) => ({
      id: q.id,
      type: q.type,
      text: q.text,
      required: q.required,
      order: idx + 1,
      // 🟢 确保选项数据包含 allow_custom 字段（后端使用蛇形命名）
      options: q.options?.map(opt => ({
        ...opt,
        allow_custom: opt.allowCustom,  // 转换为蛇形命名
      })),
      selectionRule: q.type === 'checkbox' && q.selectionRule && q.selectionRule !== 'none' ? q.selectionRule : undefined,
      minSelections: q.type === 'checkbox' ? (q.minSelections ?? undefined) : undefined,
      maxSelections: q.type === 'checkbox' ? (q.maxSelections ?? undefined) : undefined,
      scale: q.scale,
      optionA: q.optionA,
      optionB: q.optionB,
      scoreA: q.scoreA,
      scoreB: q.scoreB,
    }))

    // 是否启用评分配置
    const category = scoringEnabled.value ? 'scored' : 'survey'
    const customType = scoringEnabled.value ? 'scored' : 'non_scored'
    const scoringConfig = buildScoringConfig()

    const data: QuestionnaireCreate = {
      name: form.value.name,
      type: form.value.type,
      category: category,
      description: form.value.description,
      questions_count: editorQuestions.value.length,
      estimated_minutes: form.value.estimated_minutes,
      questions_data: {
        questions: questionsData,
        meta: {
          ...questionsMeta.value,
          creator: form.value.creator,
        },
      },
      scoring_rules: {},
      custom_type: customType,
      scoring_config: scoringConfig,
      purpose: form.value.purpose || 'survey',
      library_category_id: libraryCategoryId.value || undefined,
      tag_ids: selectedTagIds.value,
    }

    if (isEdit.value && props.questionnaire) {
      const updateData = { ...data }
      if (category === originalTechnicalCategory.value) {
        delete updateData.category
      }
      if (libraryCategoryId.value === originalLibraryCategoryId.value) {
        delete updateData.library_category_id
      }
      const tagIdsChanged = selectedTagIds.value.length !== originalTagIds.value.length
        || selectedTagIds.value.some(tagId => !originalTagIds.value.includes(tagId))
      if (!tagIdsChanged) delete updateData.tag_ids
      await updateQuestionnaire(props.questionnaire.id, updateData)
    } else {
      await createQuestionnaire(data)
    }

    emit('save')
  } catch (error) {
    console.error('保存失败:', error)
    alert('保存失败，请重试')
  } finally {
    loading.value = false
  }
}

// ===== 生命周期 =====
onMounted(async () => {
  await loadQuestionnaireLibraryOptions()
  if (!form.value.creator) {
    form.value.creator = authStore.username || 'Admin'
  }
  // V43: 处理导入的问卷数据
  if (props.importedData && props.importedData.questions.length > 0) {
    const { metadata, questions } = props.importedData

    // 填充元数据
    form.value.name = metadata.name || '导入的问卷'
    form.value.description = metadata.description || ''
    form.value.estimated_minutes = metadata.estimated_minutes || 15
    if (metadata.creator) {
      form.value.creator = metadata.creator
    }
    questionsMeta.value = { ...(metadata || {}) }

    // 转换题目格式 - V45: 修复选项格式转换
    editorQuestions.value = questions.map((q, idx) => {
      const mappedType = mapImportedQuestionType(q.type)

      // 转换选项格式：导入的是 { id, text, score }，编辑器需要 { value, label, score }
      const mappedOptions = q.options?.map((opt, optIdx) => ({
        value: opt.id || String.fromCharCode(65 + optIdx), // A, B, C, D...
        label: opt.text,
        score: opt.score || 0,
        allowCustom: opt.allow_custom,  // 🟢 保留自定义输入标记
        placeholder: opt.placeholder,    // 🟢 保留占位符
      })) || []

      return {
        id: q.id || generateId(),
        type: mappedType as EditorQuestion['type'],
        text: q.text,
        required: q.required !== false,
        options: mappedOptions,
        selectionRule: mappedType === 'checkbox' ? (q.selectionRule ?? q.selection_rule ?? undefined) : undefined,
        minSelections: mappedType === 'checkbox' ? (q.minSelections ?? q.min_selections ?? null) : undefined,
        maxSelections: mappedType === 'checkbox' ? (q.maxSelections ?? q.max_selections ?? null) : undefined,
        // 量表题配置
        scale: mappedType === 'scale' ? { min: 1, max: 5, minLabel: '非常不满意', maxLabel: '非常满意' } : undefined,
      }
    })

    // 如果有评分题，自动切换到评分问卷模式
    const hasScoring = questions.some(q =>
      q.options?.some(opt => opt.score > 0) || q.type === 'rating'
    )
    setScoringEnabled(hasScoring)

    // 导入问卷仍需先选择业务主分类。
    editorStep.value = 'info'

    console.log('✅ 导入问卷数据已加载:', editorQuestions.value.length, '道题目')
    return
  }

  if (props.questionnaire) {
    // 编辑模式：加载问卷详情
    form.value.name = props.questionnaire.name
    form.value.type = props.questionnaire.type || 'CUSTOM'
    form.value.category = props.questionnaire.category || 'survey'
    originalTechnicalCategory.value = form.value.category
    form.value.purpose = props.questionnaire.purpose || 'survey'
    form.value.description = (props.questionnaire as any).description || ''
    form.value.estimated_minutes = props.questionnaire.estimated_minutes || 10
    mergeLibraryCategory(props.questionnaire.library_category)
    mergeLibraryTags(props.questionnaire.tags || [])
    libraryCategoryId.value = props.questionnaire.library_category?.id || null
    selectedTagIds.value = (props.questionnaire.tags || []).map(tag => tag.id)
    originalLibraryCategoryId.value = libraryCategoryId.value
    originalTagIds.value = [...selectedTagIds.value]

    // 加载详细数据
    try {
      const detail = await fetchQuestionnaireDetail(props.questionnaire.id)
      originalTechnicalCategory.value = detail.category || originalTechnicalCategory.value
      mergeLibraryCategory(detail.library_category)
      mergeLibraryTags(detail.tags || [])
      libraryCategoryId.value = detail.library_category?.id || libraryCategoryId.value
      selectedTagIds.value = (detail.tags || []).map(tag => tag.id)
      originalLibraryCategoryId.value = libraryCategoryId.value
      originalTagIds.value = [...selectedTagIds.value]
      if (detail.questions_data?.questions) {
        editorQuestions.value = detail.questions_data.questions.map((q: any) => ({
          id: q.id || generateId(),
          type: q.type,
          text: q.text,
          required: q.required !== false,
          options: q.options,
          selectionRule: q.type === 'checkbox' ? (q.selectionRule ?? q.selection_rule ?? undefined) : undefined,
          minSelections: q.type === 'checkbox' ? (q.minSelections ?? q.min_selections ?? null) : undefined,
          maxSelections: q.type === 'checkbox' ? (q.maxSelections ?? q.max_selections ?? null) : undefined,
          scale: q.scale,
          optionA: q.optionA,
          optionB: q.optionB,
          scoreA: q.scoreA,
          scoreB: q.scoreB,
        }))
      }

      if (detail.questions_data?.meta) {
        questionsMeta.value = { ...detail.questions_data.meta }
        if (detail.questions_data.meta.creator) {
          form.value.creator = detail.questions_data.meta.creator
        }
      }

      const scored = detail.category === 'scored' || (detail as any).custom_type === 'scored'
      setScoringEnabled(scored)

      // 加载评分配置
      const scoringConfig = (detail as any).scoring_config
      if (scored && scoringConfig) {
        applyScoringConfig(scoringConfig)
      }
    } catch (error) {
      console.error('加载问卷详情失败:', error)
    }
  }
})

// 监听预览索引变化，重置预览状态
watch(previewIndex, () => {
  previewAnswer.value = ''
  previewAnswerMulti.value = []
  previewScaleValue.value = null
  previewYesno.value = ''
  previewChoice.value = ''
})
</script>

<template src="./QuestionnaireEditorModal.template.html"></template>

<style scoped>
@import './styles/questionnaire-editor-modal.css';
</style>
