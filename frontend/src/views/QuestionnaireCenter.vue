<script setup lang="ts">
import {
  computed,
  defineAsyncComponent,
  onMounted,
  onUnmounted,
  ref,
  watch,
} from 'vue'
import QuestionnaireCard from '../components/QuestionnaireCard.vue'
import { useAuthStore } from '../stores/auth'
import {
  bulkUpdateQuestionnaireLibraryCategory,
  copyQuestionnaire,
  deleteQuestionnaire,
  deleteSubmission,
  fetchQuestionnaireCreatorOptions,
  fetchQuestionnaireLibraryCategories,
  fetchQuestionnaires,
  fetchQuestionnaireTags,
  fetchSubmissions,
  importQuestionnaire,
  updateQuestionnaire,
  type Assessment,
  type Questionnaire,
  type QuestionnaireImportResponse,
  type QuestionnaireLibraryCategory,
  type QuestionnaireTag,
  type Submission,
} from '../api/assessments'
import {
  buildQuestionnaireLibraryQuery,
  getPaginationItems,
  hasActiveQuestionnaireLibraryFilters,
  normalizeQuestionnaireLibraryPage,
  type QuestionnaireLibrarySort,
  type QuestionnaireLibraryStatusFilter,
  type QuestionnaireLibraryTypeFilter,
} from '../utils/questionnaireLibrary'

const QuestionnaireDetailDrawer = defineAsyncComponent(() => import('../components/QuestionnaireDetailDrawer.vue'))
const QuestionnaireEditorModal = defineAsyncComponent(() => import('../components/QuestionnaireEditorModal.vue'))
const QuestionnaireLibraryManager = defineAsyncComponent(() => import('../components/QuestionnaireLibraryManager.vue'))
const DistributeModal = defineAsyncComponent(() => import('../components/DistributeModal.vue'))
const ViewLinksPanel = defineAsyncComponent(() => import('../components/ViewLinksPanel.vue'))

const authStore = useAuthStore()
const pageSize = 12

const loading = ref(false)
const questionnaires = ref<Questionnaire[]>([])
const total = ref(0)
const categories = ref<QuestionnaireLibraryCategory[]>([])
const tags = ref<QuestionnaireTag[]>([])
const creatorOptions = ref<string[]>([])
const currentPage = ref(1)
const activeCategoryId = ref<number | null>(null)
const selectedTagIds = ref<number[]>([])
const creatorFilter = ref('')
const statusFilter = ref<QuestionnaireLibraryStatusFilter>('all')
const customTypeFilter = ref<QuestionnaireLibraryTypeFilter>('all')
const sortFilter = ref<QuestionnaireLibrarySort>('updated_desc')
const keyword = ref('')
const debouncedKeyword = ref('')
const categoryTabLimit = ref(6)

const message = ref({
  show: false,
  text: '',
  type: 'info' as 'success' | 'error' | 'warning' | 'info',
})

let messageTimer: ReturnType<typeof setTimeout> | undefined
const showMessage = (text: string, type: 'success' | 'error' | 'warning' | 'info' = 'info') => {
  if (messageTimer) clearTimeout(messageTimer)
  message.value = { show: true, text, type }
  messageTimer = setTimeout(() => {
    message.value.show = false
  }, 3000)
}

const activeCategories = computed(() => (
  categories.value
    .filter(category => category.is_active)
    .sort((left, right) => left.sort_order - right.sort_order || left.id - right.id)
))
const assignableCategories = computed(() => (
  activeCategories.value.filter(category => !category.is_system)
))
const activeTags = computed(() => tags.value.filter(tag => tag.is_active))
const visibleCategoryTabs = computed(() => activeCategories.value.slice(0, categoryTabLimit.value))
const overflowCategories = computed(() => activeCategories.value.slice(categoryTabLimit.value))
const activeCategoryInOverflow = computed(() => (
  overflowCategories.value.find(category => category.id === activeCategoryId.value)
))
const totalPages = computed(() => Math.max(1, Math.ceil(total.value / pageSize)))
const paginationItems = computed(() => getPaginationItems(currentPage.value, totalPages.value))
const hasActiveFilters = computed(() => hasActiveQuestionnaireLibraryFilters({
  libraryCategoryId: activeCategoryId.value,
  tagIds: selectedTagIds.value,
  creator: creatorFilter.value,
  status: statusFilter.value,
  customType: customTypeFilter.value,
  keyword: keyword.value,
  sort: sortFilter.value,
}))

const selectedQuestionnaireIds = ref<number[]>([])
const batchMode = ref(false)
const batchCategoryId = ref<number | null>(null)
const batchSaving = ref(false)
const isCurrentPageSelected = computed(() => (
  questionnaires.value.length > 0
  && questionnaires.value.every(questionnaire => selectedQuestionnaireIds.value.includes(questionnaire.id))
))

const clearSelection = () => {
  selectedQuestionnaireIds.value = []
  batchCategoryId.value = null
}

const toggleBatchMode = () => {
  batchMode.value = !batchMode.value
  clearSelection()
}

const toggleQuestionnaireSelection = (questionnaire: Questionnaire) => {
  const selected = new Set(selectedQuestionnaireIds.value)
  if (selected.has(questionnaire.id)) selected.delete(questionnaire.id)
  else selected.add(questionnaire.id)
  selectedQuestionnaireIds.value = [...selected]
}

const toggleCurrentPageSelection = () => {
  if (isCurrentPageSelected.value) {
    const currentIds = new Set(questionnaires.value.map(questionnaire => questionnaire.id))
    selectedQuestionnaireIds.value = selectedQuestionnaireIds.value.filter(id => !currentIds.has(id))
  } else {
    selectedQuestionnaireIds.value = [
      ...new Set([
        ...selectedQuestionnaireIds.value,
        ...questionnaires.value.map(questionnaire => questionnaire.id),
      ]),
    ]
  }
}

const setActiveCategory = (categoryId: number | null) => {
  activeCategoryId.value = categoryId
}

const setCurrentPage = (page: number) => {
  currentPage.value = normalizeQuestionnaireLibraryPage(page, total.value, pageSize)
}

const resetFilters = () => {
  activeCategoryId.value = null
  selectedTagIds.value = []
  creatorFilter.value = ''
  statusFilter.value = 'all'
  customTypeFilter.value = 'all'
  sortFilter.value = 'updated_desc'
  keyword.value = ''
  debouncedKeyword.value = ''
  currentPage.value = 1
  clearSelection()
}

let listRequestId = 0
const loadData = async () => {
  const requestId = ++listRequestId
  loading.value = true
  try {
    const response = await fetchQuestionnaires(buildQuestionnaireLibraryQuery({
      page: currentPage.value,
      pageSize,
      libraryCategoryId: activeCategoryId.value,
      tagIds: selectedTagIds.value,
      creator: creatorFilter.value,
      status: statusFilter.value,
      customType: customTypeFilter.value,
      keyword: debouncedKeyword.value,
      sort: sortFilter.value,
    }))
    if (requestId !== listRequestId) return

    const normalizedPage = normalizeQuestionnaireLibraryPage(currentPage.value, response.total, pageSize)
    total.value = response.total
    if (normalizedPage !== currentPage.value) {
      currentPage.value = normalizedPage
      return
    }
    questionnaires.value = response.items || []
  } catch (error) {
    if (requestId !== listRequestId) return
    console.error('加载问卷失败:', error)
    questionnaires.value = []
    total.value = 0
    showMessage('加载问卷失败', 'error')
  } finally {
    if (requestId === listRequestId) loading.value = false
  }
}

const loadLibraryMetadata = async () => {
  try {
    const [categoryData, tagData, creators] = await Promise.all([
      fetchQuestionnaireLibraryCategories(),
      fetchQuestionnaireTags(),
      fetchQuestionnaireCreatorOptions(),
    ])
    categories.value = categoryData
    tags.value = tagData
    creatorOptions.value = creators

    if (
      activeCategoryId.value !== null
      && !categoryData.some(category => category.id === activeCategoryId.value && category.is_active)
    ) {
      activeCategoryId.value = null
    }
    selectedTagIds.value = selectedTagIds.value.filter(tagId => (
      tagData.some(tag => tag.id === tagId && tag.is_active)
    ))
  } catch (error) {
    console.error('加载分类与标签失败:', error)
    showMessage('分类与标签加载失败', 'error')
  }
}

const refreshLibrary = async () => {
  await Promise.all([loadLibraryMetadata(), loadData()])
}

const applyBatchCategory = async () => {
  if (!batchCategoryId.value || !selectedQuestionnaireIds.value.length) return
  batchSaving.value = true
  try {
    const response = await bulkUpdateQuestionnaireLibraryCategory({
      questionnaire_ids: selectedQuestionnaireIds.value,
      library_category_id: batchCategoryId.value,
    })
    showMessage(`已更新 ${response.updated_count} 份问卷的主分类`, 'success')
    clearSelection()
    await refreshLibrary()
  } catch (error) {
    console.error('批量分类失败:', error)
    showMessage('批量分类失败，请重试', 'error')
  } finally {
    batchSaving.value = false
  }
}

const showLibraryManager = ref(false)
const handleLibraryMetadataChanged = async () => {
  await refreshLibrary()
}

const showDetailDrawer = ref(false)
const selectedQuestionnaire = ref<Questionnaire | null>(null)
const selectedQuestionnaireSubmissions = ref<Submission[]>([])

const openDetailDrawer = async (questionnaire: Questionnaire) => {
  selectedQuestionnaire.value = questionnaire
  selectedQuestionnaireSubmissions.value = []
  showDetailDrawer.value = true
  try {
    const response = await fetchSubmissions({ questionnaire_id: questionnaire.id, limit: 1000 })
    if (selectedQuestionnaire.value?.id === questionnaire.id) {
      selectedQuestionnaireSubmissions.value = response.items || []
    }
  } catch (error) {
    console.error('加载问卷答题记录失败:', error)
    showMessage('加载答题记录失败', 'error')
  }
}

const closeDetailDrawer = () => {
  showDetailDrawer.value = false
  selectedQuestionnaire.value = null
  selectedQuestionnaireSubmissions.value = []
}

const reloadSelectedQuestionnaireSubmissions = async () => {
  if (!selectedQuestionnaire.value) return
  const response = await fetchSubmissions({
    questionnaire_id: selectedQuestionnaire.value.id,
    limit: 1000,
  })
  selectedQuestionnaireSubmissions.value = response.items || []
}

const handleDeleteSubmission = async (submission: Submission) => {
  try {
    await deleteSubmission(submission.id)
    await reloadSelectedQuestionnaireSubmissions()
    showMessage('删除成功', 'success')
  } catch (error) {
    console.error('删除提交记录失败:', error)
    showMessage('删除失败，请重试', 'error')
  }
}

const handleBatchDeleteSubmissions = async (submissions: Submission[]) => {
  try {
    await Promise.all(submissions.map(submission => deleteSubmission(submission.id)))
    await reloadSelectedQuestionnaireSubmissions()
    showMessage(`成功删除 ${submissions.length} 条记录`, 'success')
  } catch (error) {
    console.error('批量删除提交记录失败:', error)
    showMessage('批量删除失败，请重试', 'error')
  }
}

const showEditorModal = ref(false)
const editingQuestionnaire = ref<Questionnaire | null>(null)
const importedQuestions = ref<QuestionnaireImportResponse | null>(null)

const openCreateModal = () => {
  editingQuestionnaire.value = null
  importedQuestions.value = null
  showEditorModal.value = true
}

const openEditModal = (questionnaire: Questionnaire) => {
  editingQuestionnaire.value = questionnaire
  importedQuestions.value = null
  showEditorModal.value = true
}

const closeEditorModal = () => {
  showEditorModal.value = false
  editingQuestionnaire.value = null
  importedQuestions.value = null
}

const handleEditorSave = async () => {
  const wasEditing = !!editingQuestionnaire.value
  closeEditorModal()
  await refreshLibrary()
  if (wasEditing) {
    showMessage('问卷内容已更新，现有链接会自动使用最新内容', 'success')
  }
}

const showImportModal = ref(false)
const importLoading = ref(false)
const importError = ref<string | null>(null)
const importFileInput = ref<HTMLInputElement | null>(null)
const useAIImport = ref(true)

const openImportModal = () => {
  showImportModal.value = true
  importError.value = null
  useAIImport.value = true
}

const closeImportModal = () => {
  showImportModal.value = false
  importError.value = null
}

const triggerFileSelect = () => importFileInput.value?.click()

const handleImportFile = async (event: Event) => {
  const target = event.target as HTMLInputElement
  const file = target.files?.[0]
  if (!file) return
  importLoading.value = true
  importError.value = null
  try {
    const result = await importQuestionnaire(file, useAIImport.value)
    importedQuestions.value = result
    closeImportModal()
    editingQuestionnaire.value = null
    showEditorModal.value = true
    showMessage(result.message || `成功解析 ${result.questions.length} 道题目`, 'success')
  } catch (error: any) {
    importError.value = error?.message || '导入失败'
    showMessage(importError.value || '导入失败', 'error')
  } finally {
    importLoading.value = false
    target.value = ''
  }
}

const showDistributeModal = ref(false)
const distributeQuestionnaire = ref<Questionnaire | null>(null)
const distributeAssessment = ref<Assessment | null>(null)
const distributeMode = ref<'create' | 'edit' | 'clone'>('create')

const openDistributeModal = (
  questionnaire: Questionnaire,
  assessment: Assessment | null = null,
  mode: 'create' | 'edit' | 'clone' = assessment ? 'edit' : 'create',
) => {
  distributeQuestionnaire.value = questionnaire
  distributeAssessment.value = assessment
  distributeMode.value = mode
  showDistributeModal.value = true
}

const closeDistributeModal = () => {
  showDistributeModal.value = false
  distributeQuestionnaire.value = null
  distributeAssessment.value = null
  distributeMode.value = 'create'
}

const handleDistributeSuccess = async () => {
  closeDistributeModal()
  await loadData()
}

const showViewLinksPanel = ref(false)
const viewLinksQuestionnaire = ref<Questionnaire | null>(null)

const openViewLinksPanel = (questionnaire: Questionnaire) => {
  viewLinksQuestionnaire.value = questionnaire
  showViewLinksPanel.value = true
}

const closeViewLinksPanel = () => {
  showViewLinksPanel.value = false
  viewLinksQuestionnaire.value = null
}

const handleCreateNewLink = () => {
  if (!viewLinksQuestionnaire.value) return
  const questionnaire = viewLinksQuestionnaire.value
  closeViewLinksPanel()
  openDistributeModal(questionnaire)
}

const findDistributionQuestionnaire = (assessment: Assessment) => (
  questionnaires.value.find(questionnaire => questionnaire.id === assessment.questionnaire_id)
  || (viewLinksQuestionnaire.value?.id === assessment.questionnaire_id ? viewLinksQuestionnaire.value : null)
)

const handleEditDistribution = (assessment: Assessment) => {
  const questionnaire = findDistributionQuestionnaire(assessment)
  if (!questionnaire) {
    showMessage('未找到该链接对应的问卷', 'error')
    return
  }
  closeViewLinksPanel()
  openDistributeModal(questionnaire, assessment, 'edit')
}

const handleCloneDistribution = (assessment: Assessment) => {
  const questionnaire = findDistributionQuestionnaire(assessment)
  if (!questionnaire) {
    showMessage('未找到该链接对应的问卷', 'error')
    return
  }
  closeViewLinksPanel()
  openDistributeModal(questionnaire, assessment, 'clone')
}

const showToggleStatusConfirm = ref(false)
const toggleStatusTarget = ref<Questionnaire | null>(null)
const toggleStatusSaving = ref(false)

const openToggleStatusConfirm = (questionnaire: Questionnaire) => {
  toggleStatusTarget.value = questionnaire
  showToggleStatusConfirm.value = true
}

const cancelToggleStatus = () => {
  if (toggleStatusSaving.value) return
  showToggleStatusConfirm.value = false
  toggleStatusTarget.value = null
}

const executeToggleStatus = async () => {
  if (!toggleStatusTarget.value || toggleStatusSaving.value) return
  const questionnaire = toggleStatusTarget.value
  const status = questionnaire.status === 'active' ? 'inactive' : 'active'
  toggleStatusSaving.value = true
  try {
    await updateQuestionnaire(questionnaire.id, { status })
    showMessage(`问卷已${status === 'active' ? '启用' : '停用'}`, 'success')
    showToggleStatusConfirm.value = false
    toggleStatusTarget.value = null
    await loadData()
  } catch (error) {
    console.error('更新问卷状态失败:', error)
    showMessage('状态更新失败，请重试', 'error')
  } finally {
    toggleStatusSaving.value = false
  }
}

const showDeleteConfirm = ref(false)
const deleteTarget = ref<Questionnaire | null>(null)

const confirmDelete = (questionnaire: Questionnaire) => {
  deleteTarget.value = questionnaire
  showDeleteConfirm.value = true
}

const cancelDelete = () => {
  showDeleteConfirm.value = false
  deleteTarget.value = null
}

const executeDelete = async () => {
  if (!deleteTarget.value) return
  try {
    await deleteQuestionnaire(deleteTarget.value.id)
    showMessage('问卷已删除', 'success')
    await refreshLibrary()
  } catch (error) {
    console.error('删除问卷失败:', error)
    showMessage('删除失败，请重试', 'error')
  } finally {
    cancelDelete()
  }
}

const handleCopyQuestionnaire = async (questionnaire: Questionnaire) => {
  try {
    const copied = await copyQuestionnaire(questionnaire.id)
    showMessage(`已复制问卷：${copied.name}`, 'success')
    await refreshLibrary()
  } catch (error) {
    console.error('复制问卷失败:', error)
    showMessage('复制问卷失败，请重试', 'error')
  }
}

let keywordTimer: ReturnType<typeof setTimeout> | undefined
watch(keyword, value => {
  if (keywordTimer) clearTimeout(keywordTimer)
  keywordTimer = setTimeout(() => {
    debouncedKeyword.value = value.trim()
  }, 300)
})

watch(
  [
    activeCategoryId,
    () => selectedTagIds.value.join(','),
    creatorFilter,
    statusFilter,
    customTypeFilter,
    sortFilter,
    debouncedKeyword,
  ],
  () => {
    currentPage.value = 1
    clearSelection()
  },
)

const querySignature = computed(() => JSON.stringify({
  page: currentPage.value,
  category: activeCategoryId.value,
  tags: selectedTagIds.value,
  creator: creatorFilter.value,
  status: statusFilter.value,
  customType: customTypeFilter.value,
  keyword: debouncedKeyword.value,
  sort: sortFilter.value,
}))

watch(querySignature, () => {
  clearSelection()
  loadData()
}, { immediate: true })

const updateCategoryTabLimit = () => {
  if (window.innerWidth < 600) categoryTabLimit.value = 2
  else if (window.innerWidth < 1050) categoryTabLimit.value = 3
  else if (window.innerWidth < 1450) categoryTabLimit.value = 4
  else categoryTabLimit.value = 6
}

onMounted(() => {
  updateCategoryTabLimit()
  window.addEventListener('resize', updateCategoryTabLimit)
  loadLibraryMetadata()
})

onUnmounted(() => {
  if (keywordTimer) clearTimeout(keywordTimer)
  if (messageTimer) clearTimeout(messageTimer)
  window.removeEventListener('resize', updateCategoryTabLimit)
})
</script>

<template src="./QuestionnaireCenter.template.html"></template>

<style scoped>
@import './styles/questionnaire-center.css';
</style>
