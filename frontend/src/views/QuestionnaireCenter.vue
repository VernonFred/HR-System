<script setup lang="ts">
/**
 * 问卷中心 - 主页面
 *
 * 功能：
 * 1. 显示自定义问卷列表（评分问卷 + 调查问卷）
 * 2. 创建/编辑/删除问卷
 * 3. 点击问卷卡片打开详情抽屉（提交记录 + 统计）
 * 4. 分发问卷
 */
import { ref, computed, onMounted, watch, defineAsyncComponent } from 'vue'
import { useRoute } from 'vue-router'
import QuestionnaireCard from '../components/QuestionnaireCard.vue'
// 使用异步组件加载弹窗组件，提升首屏加载性能
const QuestionnaireDetailDrawer = defineAsyncComponent(() => import('../components/QuestionnaireDetailDrawer.vue'))
const QuestionnaireEditorModal = defineAsyncComponent(() => import('../components/QuestionnaireEditorModal.vue'))
const DistributeModal = defineAsyncComponent(() => import('../components/DistributeModal.vue'))
const ViewLinksPanel = defineAsyncComponent(() => import('../components/ViewLinksPanel.vue'))
import {
  fetchQuestionnaires,
  fetchAssessments,
  fetchSubmissions,
  copyQuestionnaire,
  deleteQuestionnaire,
  deleteSubmission,  // ⭐ V44: 导入删除提交记录API
  importQuestionnaire,
  type Questionnaire,
  type Assessment,
  type Submission,
  type QuestionnaireImportResponse,
} from '../api/assessments'

// ===== 路由 =====
const route = useRoute()

// ===== 状态 =====
const loading = ref(false)
const questionnaires = ref<Questionnaire[]>([])
const assessments = ref<Assessment[]>([])
const submissions = ref<Submission[]>([])

// ===== 详情抽屉 =====
const showDetailDrawer = ref(false)
const selectedQuestionnaire = ref<Questionnaire | null>(null)
const selectedQuestionnaireSubmissions = ref<Submission[]>([])

const openDetailDrawer = async (q: Questionnaire) => {
  selectedQuestionnaire.value = q
  selectedQuestionnaireSubmissions.value = []
  showDetailDrawer.value = true
  try {
    const response = await fetchSubmissions({ questionnaire_id: q.id, limit: 1000 })
    if (selectedQuestionnaire.value?.id === q.id) {
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

// ⭐ V44: 删除单条提交记录
const handleDeleteSubmission = async (submission: Submission) => {
  try {
    await deleteSubmission(submission.id)
    showMessage('删除成功', 'success')
    // V45: 删除成功后重新加载数据
    await loadData()
    if (selectedQuestionnaire.value) {
      const response = await fetchSubmissions({ questionnaire_id: selectedQuestionnaire.value.id, limit: 1000 })
      selectedQuestionnaireSubmissions.value = response.items || []
    }
  } catch (error) {
    console.error('删除失败:', error)
    showMessage('删除失败，请重试', 'error')
  }
}

// ⭐ V44: 批量删除提交记录
const handleBatchDeleteSubmissions = async (toDelete: Submission[]) => {
  try {
    for (const submission of toDelete) {
      await deleteSubmission(submission.id)
    }
    showMessage(`成功删除 ${toDelete.length} 条记录`, 'success')
    // V45: 删除成功后重新加载数据
    await loadData()
    if (selectedQuestionnaire.value) {
      const response = await fetchSubmissions({ questionnaire_id: selectedQuestionnaire.value.id, limit: 1000 })
      selectedQuestionnaireSubmissions.value = response.items || []
    }
  } catch (error) {
    console.error('批量删除失败:', error)
    showMessage('批量删除失败，请重试', 'error')
  }
}

// ===== 编辑器弹窗 =====
const showEditorModal = ref(false)
const editingQuestionnaire = ref<Questionnaire | null>(null)

const openCreateModal = () => {
  editingQuestionnaire.value = null
  importedQuestions.value = null  // 清除导入的题目
  showEditorModal.value = true
}

// ===== V43: 导入问卷 =====
const showImportModal = ref(false)
const importLoading = ref(false)
const importError = ref<string | null>(null)
const importedQuestions = ref<QuestionnaireImportResponse | null>(null)
const importFileInput = ref<HTMLInputElement | null>(null)

// V45: AI智能解析开关
const useAIImport = ref(true)

const openImportModal = () => {
  showImportModal.value = true
  importError.value = null
  useAIImport.value = true  // 默认开启AI解析
}

const closeImportModal = () => {
  showImportModal.value = false
  importError.value = null
}

const triggerFileSelect = () => {
  importFileInput.value?.click()
}

const handleImportFile = async (event: Event) => {
  const target = event.target as HTMLInputElement
  const file = target.files?.[0]
  if (!file) return

  importLoading.value = true
  importError.value = null

  try {
    // V45: 传递AI解析开关
    const result = await importQuestionnaire(file, useAIImport.value)
    importedQuestions.value = result

    // 关闭导入弹窗，打开编辑器弹窗
    closeImportModal()
    editingQuestionnaire.value = null
    showEditorModal.value = true

    showMessage(result.message || `成功解析 ${result.questions.length} 道题目`, 'success')
  } catch (err: any) {
    importError.value = err.message || '导入失败'
    showMessage(importError.value, 'error')
  } finally {
    importLoading.value = false
    // 清空文件输入
    if (target) target.value = ''
  }
}

const openEditModal = (q: Questionnaire) => {
  editingQuestionnaire.value = q
  showEditorModal.value = true
}

const closeEditorModal = () => {
  showEditorModal.value = false
  editingQuestionnaire.value = null
}

const handleEditorSave = () => {
  const wasEditing = !!editingQuestionnaire.value
  closeEditorModal()
  loadData()
  if (wasEditing) {
    showMessage('问卷内容已更新，现有链接会自动使用最新内容，无需重新分发', 'success')
  }
}

// ===== 分发弹窗 =====
const showDistributeModal = ref(false)
const distributeQuestionnaire = ref<Questionnaire | null>(null)
const distributeAssessment = ref<Assessment | null>(null)
const distributeMode = ref<'create' | 'edit' | 'clone'>('create')

const openDistributeModal = (
  q: Questionnaire,
  assessment: Assessment | null = null,
  mode: 'create' | 'edit' | 'clone' = assessment ? 'edit' : 'create'
) => {
  distributeQuestionnaire.value = q
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

const handleDistributeSuccess = () => {
  closeDistributeModal()
  loadData()
}

// ===== 查看链接面板 =====
const showViewLinksPanel = ref(false)
const viewLinksQuestionnaire = ref<Questionnaire | null>(null)

const openViewLinksPanel = (q: Questionnaire) => {
  viewLinksQuestionnaire.value = q
  showViewLinksPanel.value = true
}

const closeViewLinksPanel = () => {
  showViewLinksPanel.value = false
  viewLinksQuestionnaire.value = null
}

const handleCreateNewLink = () => {
  if (viewLinksQuestionnaire.value) {
    closeViewLinksPanel()
    openDistributeModal(viewLinksQuestionnaire.value)
  }
}

const handleEditDistribution = (assessment: Assessment) => {
  const questionnaire = questionnaires.value.find((q) => q.id === assessment.questionnaire_id)
  if (!questionnaire) {
    showMessage('未找到该链接对应的问卷', 'error')
    return
  }
  closeViewLinksPanel()
  openDistributeModal(questionnaire, assessment, 'edit')
}

const handleCloneDistribution = (assessment: Assessment) => {
  const questionnaire = questionnaires.value.find((q) => q.id === assessment.questionnaire_id)
  if (!questionnaire) {
    showMessage('未找到该链接对应的问卷', 'error')
    return
  }
  closeViewLinksPanel()
  openDistributeModal(questionnaire, assessment, 'clone')
}

// ===== 切换问卷状态 =====
const showToggleStatusConfirm = ref(false)
const toggleStatusTarget = ref<Questionnaire | null>(null)

const openToggleStatusConfirm = (q: Questionnaire) => {
  toggleStatusTarget.value = q
  showToggleStatusConfirm.value = true
}

const cancelToggleStatus = () => {
  showToggleStatusConfirm.value = false
  toggleStatusTarget.value = null
}

const executeToggleStatus = () => {
  if (!toggleStatusTarget.value) return

  const q = toggleStatusTarget.value
  const newStatus = q.status === 'active' ? 'inactive' : 'active'
  const actionText = newStatus === 'active' ? '启用' : '停用'

  // 更新本地状态
  const index = questionnaires.value.findIndex(item => item.id === q.id)
  if (index !== -1) {
    questionnaires.value[index] = { ...questionnaires.value[index], status: newStatus }
  }

  showMessage(`问卷已${actionText}`, 'success')
  cancelToggleStatus()
}

// ===== 删除确认 =====
const showDeleteConfirm = ref(false)
const deleteTarget = ref<Questionnaire | null>(null)

const confirmDelete = (q: Questionnaire) => {
  deleteTarget.value = q
  showDeleteConfirm.value = true
}

const handleCopyQuestionnaire = async (q: Questionnaire) => {
  try {
    const copied = await copyQuestionnaire(q.id)
    showMessage(`已复制问卷：${copied.name}`, 'success')
    await loadData()
  } catch (error) {
    console.error('复制问卷失败:', error)
    showMessage('复制问卷失败，请重试', 'error')
  }
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
    loadData()
  } catch (error) {
    showMessage('删除失败，请重试', 'error')
  } finally {
    cancelDelete()
  }
}

// ===== 消息提示 =====
const message = ref({ show: false, text: '', type: 'info' as 'success' | 'error' | 'warning' | 'info' })

const showMessage = (text: string, type: 'success' | 'error' | 'warning' | 'info' = 'info') => {
  message.value = { show: true, text, type }
  setTimeout(() => {
    message.value.show = false
  }, 3000)
}

// ===== 数据加载 =====
const loadData = async () => {
  loading.value = true
  try {
    // 加载自定义问卷（scored + survey）
    const [scoredRes, surveyRes, assessRes, subRes] = await Promise.all([
      fetchQuestionnaires({ category: 'scored' }),
      fetchQuestionnaires({ category: 'survey' }),
      fetchAssessments(),
      fetchSubmissions({ category: 'custom' }),
    ])

    questionnaires.value = [
      ...(scoredRes.items || []),
      ...(surveyRes.items || [])
    ]
    assessments.value = assessRes.items || []
    submissions.value = subRes.items || []
  } catch (error) {
    console.error('加载数据失败:', error)
    showMessage('加载数据失败', 'error')
  } finally {
    loading.value = false
  }
}

// ===== 生命周期 =====
onMounted(() => {
  loadData()
})
</script>

<template src="./QuestionnaireCenter.template.html"></template>

<style scoped>
@import './styles/questionnaire-center.css';
</style>
