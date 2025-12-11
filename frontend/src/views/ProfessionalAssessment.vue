<script setup lang="ts">
/**
 * 专业测评页面
 * 
 * 功能：
 * 1. 显示专业测评问卷（MBTI/DISC/EPQ）
 * 2. 测评管理（分发、查看链接）
 * 3. 提交记录查看（列表视图/分组视图）
 * 4. 测评报告查看
 * 5. 数据导出
 */
import { onMounted, ref, computed, defineAsyncComponent, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import QuestionnaireCard from '../components/QuestionnaireCard.vue'
// 使用异步组件加载弹窗组件，提升首屏加载性能
const DistributeModal = defineAsyncComponent(() => import('../components/DistributeModal.vue'))
const ViewLinksPanel = defineAsyncComponent(() => import('../components/ViewLinksPanel.vue'))
const SubmissionRecordsTab = defineAsyncComponent(() => import('../components/SubmissionRecordsTab.vue'))
import QuestionEditDialog, { type EditorQuestion } from '../components/QuestionEditDialog.vue'
import CandidatePreviewPanel from '../components/CandidatePreviewPanel.vue'
import {
  fetchQuestionnaires,
  fetchAssessments,
  fetchSubmissions,
  fetchQuestionnaireDetail,
  deleteSubmission,
  deleteQuestionnaire,
  updateQuestionnaire,
  type Questionnaire,
  type Assessment,
  type Submission,
} from '../api/assessments'
import { PRESET_QUESTIONS, type PresetQuestion } from '../data/preset-questions'

// ===== 路由 =====
const route = useRoute()
const router = useRouter()

// ===== 状态 =====
type TabKey = 'manage' | 'records'
// 从URL query参数初始化Tab状态，默认为'manage'
const activeTab = ref<TabKey>((route.query.tab as TabKey) || 'manage')
const loading = ref(false)

// 监听Tab变化，同步到URL query参数
watch(activeTab, (newTab) => {
  router.replace({ query: { ...route.query, tab: newTab } })
})
const questionnaires = ref<Questionnaire[]>([])
const assessments = ref<Assessment[]>([])
const submissions = ref<Submission[]>([])

// ===== 提交记录相关状态（已移至 SubmissionRecordsTab 组件内部） =====

// ===== 分发弹窗 =====
const showDistributeModal = ref(false)
const selectedQuestionnaireForDistribute = ref<Questionnaire | null>(null)

// ===== 查看链接面板 =====
const showViewLinksPanel = ref(false)
const viewLinksQuestionnaire = ref<Questionnaire | null>(null)

// ===== 提交详情（已移至 SubmissionRecordsTab 组件内部） =====

// ===== 编辑问卷弹窗 =====
const showEditQuestionnaireModal = ref(false)
const selectedQuestionnaire = ref<Questionnaire | null>(null)
const editQuestionnaireForm = ref({
  name: '',
  type: '',
  description: '',
  estimated_minutes: 0,
})

// ===== 题目编辑 =====
const editorQuestions = ref<EditorQuestion[]>([])
const showQuestionEditDialog = ref(false)
const editingQuestionIndex = ref<number | null>(null)
const editingQuestion = ref<EditorQuestion | null>(null)
const questionsLoading = ref(false)
const editStep = ref<'info' | 'questions'>('info')

// 控件库配置
const questionControls = [
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

// 获取全局索引
const getGlobalIndex = (localIndex: number) => {
  return (questionsCurrentPage.value - 1) * questionsPageSize.value + localIndex
}

// 获取题型名称
const getQuestionTypeName = (type: string) => {
  const ctrl = questionControls.find(c => c.type === type)
  return ctrl?.label || type
}

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

// ===== 删除问卷确认 =====
const showDeleteQuestionnaireModal = ref(false)
const deleteTargetQuestionnaire = ref<Questionnaire | null>(null)

// ===== 切换状态确认 =====
const showToggleStatusConfirm = ref(false)
const toggleTargetQuestionnaire = ref<Questionnaire | null>(null)

// ===== 消息提示 =====
const message = ref({ show: false, text: '', type: 'info' as 'success' | 'error' | 'warning' | 'info' })

const showMessage = (text: string, type: 'success' | 'error' | 'warning' | 'info' = 'info') => {
  message.value = { show: true, text, type }
  setTimeout(() => {
    message.value.show = false
  }, 3000)
}

// ===== 方法 =====
const loadData = async () => {
  loading.value = true
  try {
    // 只加载专业测评问卷
    const [qRes, aRes, sRes] = await Promise.all([
      fetchQuestionnaires({ category: 'professional' }),
      fetchAssessments(),
      fetchSubmissions({ category: 'professional' }),
    ])
    
    questionnaires.value = qRes.items || []
    assessments.value = aRes.items || []
    submissions.value = sRes.items || []
  } catch (error) {
    console.error('加载数据失败:', error)
  } finally {
    loading.value = false
  }
}

// 打开分发弹窗
const handleDistribute = (q: Questionnaire) => {
  selectedQuestionnaireForDistribute.value = q
  showDistributeModal.value = true
}

// 打开查看链接面板
const handleViewLinks = (q: Questionnaire) => {
  viewLinksQuestionnaire.value = q
  showViewLinksPanel.value = true
}

// 分发成功回调
const handleDistributeSuccess = () => {
  showDistributeModal.value = false
  loadData()
}

// 从链接面板创建新链接
const handleCreateNewLink = () => {
  showViewLinksPanel.value = false
  if (viewLinksQuestionnaire.value) {
    handleDistribute(viewLinksQuestionnaire.value)
  }
}

// 处理来自 SubmissionRecordsTab 组件的删除事件
const handleDeleteSubmissionFromTab = async (submission: Submission) => {
  try {
    await deleteSubmission(submission.id)
    // V45: 删除成功后重新加载数据
    await loadData()
  } catch (error) {
    console.error('删除失败:', error)
    alert('删除失败，请重试')
  }
}

// ⭐ V44: 处理批量删除事件
const handleBatchDeleteSubmissions = async (toDelete: Submission[]) => {
  try {
    // 逐个删除
    for (const submission of toDelete) {
      await deleteSubmission(submission.id)
    }
    console.log(`✅ 批量删除成功: ${toDelete.length} 条记录`)
    // V45: 删除成功后重新加载数据
    await loadData()
  } catch (error) {
    console.error('批量删除失败:', error)
    alert('批量删除失败，请重试')
  }
}

// ===== 编辑问卷 =====
const handleEditQuestionnaire = async (q: Questionnaire) => {
  selectedQuestionnaire.value = q
  editQuestionnaireForm.value = {
    name: q.name,
    type: q.type,
    description: (q as any).description || '',
    estimated_minutes: q.estimated_minutes,
  }
  editStep.value = 'info'
  editorQuestions.value = []
  showEditQuestionnaireModal.value = true
  
  // 加载题目数据
  await loadQuestionnaireQuestions(q.id)
}

// 加载问卷题目
const loadQuestionnaireQuestions = async (id: number) => {
  questionsLoading.value = true
  try {
    // 首先判断是否是内置的专业测评问卷
    const questionnaire = selectedQuestionnaire.value
    if (questionnaire) {
      // 根据问卷类型或名称判断是哪种专业测评
      const qName = questionnaire.name.toUpperCase()
      const qType = questionnaire.type?.toUpperCase() || ''
      
      let presetKey: string | null = null
      if (qName.includes('EPQ') || qType.includes('EPQ')) {
        presetKey = 'EPQ'
      } else if (qName.includes('DISC') || qType.includes('DISC')) {
        presetKey = 'DISC'
      } else if (qName.includes('MBTI') || qType.includes('MBTI')) {
        presetKey = 'MBTI'
      }
      
      // 如果是内置专业测评，从预设题目加载
      if (presetKey && PRESET_QUESTIONS[presetKey]) {
        const presetQuestions = PRESET_QUESTIONS[presetKey]
        editorQuestions.value = presetQuestions.map((pq: PresetQuestion, idx: number) => {
          // 根据题目类型构建选项
          let options: { label: string; value: string; score: number }[] = []
          
          if (pq.type === 'yesno') {
            // 是非题：是/否 选项
            options = [
              { label: '是', value: 'yes', score: pq.positive ? 1 : 0 },
              { label: '否', value: 'no', score: pq.positive ? 0 : 1 },
            ]
          } else if (pq.type === 'choice' && pq.optionA && pq.optionB) {
            // 二选一题（MBTI 风格）
            options = [
              { label: pq.optionA, value: 'A', score: 1 },
              { label: pq.optionB, value: 'B', score: 0 },
            ]
          } else if (pq.options) {
            // 普通选择题
            options = pq.options.map(opt => ({
              label: opt.label,
              value: opt.value,
              score: 0,
            }))
          }
          
          return {
            id: pq.id,
            type: pq.type === 'yesno' ? 'yesno' : (pq.type === 'choice' ? 'radio' : pq.type),
            text: pq.text,
            required: pq.required,
            options,
            dimension: pq.dimension,
            positive: pq.positive,
            scale: pq.scale,
            optionA: pq.optionA,
            optionB: pq.optionB,
            scoreA: pq.optionA ? 1 : undefined,
            scoreB: pq.optionB ? 0 : undefined,
          }
        })
        questionsLoading.value = false
        return
      }
    }
    
    // 非内置问卷，尝试从 API 加载
    const detail = await fetchQuestionnaireDetail(id)
    if (detail.questions_data?.questions) {
      editorQuestions.value = detail.questions_data.questions.map((q: any, idx: number) => ({
        id: q.id || `q_${idx}`,
        type: q.type || 'radio',
        text: q.text || q.question || '',
        required: q.required !== false,
        options: q.options?.map((opt: any) => ({
          label: typeof opt === 'string' ? opt : opt.label,
          value: typeof opt === 'string' ? opt : opt.value,
          score: opt.score || opt.dimension_value || 0,
        })) || [],
        scale: q.scale,
        optionA: q.optionA,
        optionB: q.optionB,
        scoreA: q.scoreA,
        scoreB: q.scoreB,
      }))
    }
  } catch (error) {
    console.error('加载题目失败:', error)
  } finally {
    questionsLoading.value = false
  }
}

// 切换到题目编辑步骤
const goToQuestionsStep = () => {
  editStep.value = 'questions'
}

// 返回基本信息步骤
const goToInfoStep = () => {
  editStep.value = 'info'
}

// 添加新题目
const handleAddQuestion = () => {
  editingQuestionIndex.value = null
  editingQuestion.value = null
  showQuestionEditDialog.value = true
}

// 编辑题目
const handleEditQuestion = (index: number) => {
  editingQuestionIndex.value = index
  editingQuestion.value = editorQuestions.value[index]
  showQuestionEditDialog.value = true
}

// 保存题目
const handleSaveQuestion = (question: EditorQuestion) => {
  if (editingQuestionIndex.value !== null) {
    // 编辑现有题目
    editorQuestions.value[editingQuestionIndex.value] = question
  } else {
    // 添加新题目
    editorQuestions.value.push(question)
  }
  showQuestionEditDialog.value = false
  editingQuestionIndex.value = null
  editingQuestion.value = null
}

// 删除题目
const handleDeleteQuestion = (index: number) => {
  if (confirm('确定要删除这道题目吗？')) {
    editorQuestions.value.splice(index, 1)
  }
}

// 移动题目
const moveQuestion = (index: number, direction: 'up' | 'down') => {
  const newIndex = direction === 'up' ? index - 1 : index + 1
  if (newIndex < 0 || newIndex >= editorQuestions.value.length) return
  
  const temp = editorQuestions.value[index]
  editorQuestions.value[index] = editorQuestions.value[newIndex]
  editorQuestions.value[newIndex] = temp
}

const handleSaveQuestionnaire = async () => {
  if (!selectedQuestionnaire.value) return
  
  try {
    loading.value = true
    
    // 构建更新数据
    const updateData: any = {
      ...editQuestionnaireForm.value,
      questions_count: editorQuestions.value.length,
    }
    
    // 如果有题目编辑，也更新题目数据
    if (editorQuestions.value.length > 0) {
      updateData.questions_data = {
        questions: editorQuestions.value.map((q, idx) => ({
          id: q.id,
          type: q.type,
          text: q.text,
          order: idx + 1,
          required: q.required,
          options: q.options,
          scale: q.scale,
          optionA: q.optionA,
          optionB: q.optionB,
          scoreA: q.scoreA,
          scoreB: q.scoreB,
        }))
      }
    }
    
    await updateQuestionnaire(selectedQuestionnaire.value.id, updateData)
    showEditQuestionnaireModal.value = false
    alert('问卷信息已更新')
    loadData()
  } catch (error) {
    console.error('更新问卷失败:', error)
    alert('更新问卷失败，请重试')
  } finally {
    loading.value = false
  }
}

// ===== 删除问卷 =====
const handleDeleteQuestionnaire = (questionnaireOrId: Questionnaire | number) => {
  // 兼容传入对象或ID
  const q = typeof questionnaireOrId === 'number' 
    ? questionnaires.value.find(item => item.id === questionnaireOrId)
    : questionnaireOrId
  
  if (q) {
    deleteTargetQuestionnaire.value = q
    showDeleteQuestionnaireModal.value = true
  }
}

const confirmDeleteQuestionnaire = async () => {
  if (!deleteTargetQuestionnaire.value) return
  
  try {
    loading.value = true
    await deleteQuestionnaire(deleteTargetQuestionnaire.value.id)
    questionnaires.value = questionnaires.value.filter(q => q.id !== deleteTargetQuestionnaire.value!.id)
    showDeleteQuestionnaireModal.value = false
    deleteTargetQuestionnaire.value = null
    alert('问卷删除成功')
  } catch (error) {
    console.error('删除问卷失败:', error)
    alert('删除问卷失败，请重试')
  } finally {
    loading.value = false
  }
}

// ===== 切换问卷状态 =====
const handleToggleStatus = (q: Questionnaire) => {
  toggleTargetQuestionnaire.value = q
  showToggleStatusConfirm.value = true
}

const cancelToggleStatus = () => {
  showToggleStatusConfirm.value = false
  toggleTargetQuestionnaire.value = null
}

const executeToggleStatus = async () => {
  if (!toggleTargetQuestionnaire.value) return

  const q = toggleTargetQuestionnaire.value
  const newStatus = q.status === 'active' ? 'inactive' : 'active'
  const actionText = newStatus === 'active' ? '启用' : '停用'

  try {
    // 调用API更新后端状态
    await updateQuestionnaire(q.id, { status: newStatus })

    // 更新本地状态
    const index = questionnaires.value.findIndex(item => item.id === q.id)
    if (index !== -1) {
      questionnaires.value[index] = { ...questionnaires.value[index], status: newStatus }
    }
    showMessage(`问卷已${actionText}`, 'success')
    loadData() // 重新加载数据以刷新UI
  } catch (error) {
    console.error('更新问卷状态失败:', error)
    showMessage(`${actionText}问卷失败，请重试`, 'error')
  } finally {
    cancelToggleStatus()
  }
}

// 导出PDF报告
const handleExportPDF = async (submission: Submission) => {
  try {
    const { exportReport } = await import('../utils/exportReport')
    const result = await exportReport(submission, 'pdf')
    showMessage(result.message, result.success ? 'success' : 'error')
  } catch (error) {
    console.error('导出PDF报告失败:', error)
    showMessage('导出报告失败，请重试', 'error')
  }
}

// ===== 以下函数已移至 SubmissionRecordsTab 组件内部 =====
// exportRecords, toggleCandidateExpand, toggleAllCandidates, formatDate, getStatusLabel

// ===== 生命周期 =====
onMounted(() => {
  loadData()
})
</script>

<template>
  <div class="assessment-page">
    <!-- 页面头部 -->
    <div class="page-header">
      <div class="header-icon">
        <i class="ri-file-list-3-line"></i>
      </div>
      <div class="header-content">
        <h1>专业测评</h1>
      </div>
    </div>


    <!-- 标签页切换 -->
    <div class="tabs-container">
      <button 
        :class="['tab-btn', { active: activeTab === 'manage' }]"
        @click="activeTab = 'manage'"
      >
        <i class="ri-settings-3-line"></i>
        测评管理
      </button>
      <button 
        :class="['tab-btn', { active: activeTab === 'records' }]"
        @click="activeTab = 'records'"
      >
        <i class="ri-file-list-2-line"></i>
        提交记录
      </button>
    </div>

    <!-- 测评管理 Tab -->
    <div v-if="activeTab === 'manage'" class="content-section">
      <div class="section-header">
        <h2>专业测评库</h2>
      </div>

      <div v-if="loading" class="loading-state">
        <i class="ri-loader-4-line spin"></i>
        <span>加载中...</span>
      </div>

      <div v-else-if="questionnaires.length === 0" class="empty-state">
        <i class="ri-file-list-3-line"></i>
        <p>暂无专业测评问卷</p>
      </div>

      <div v-else class="questionnaire-grid">
        <QuestionnaireCard
          v-for="q in questionnaires"
          :key="q.id"
          :questionnaire="q"
          category="professional"
          @distribute="handleDistribute"
          @view-links="handleViewLinks"
          @edit="handleEditQuestionnaire"
          @delete="handleDeleteQuestionnaire"
          @toggle-status="handleToggleStatus"
        />
      </div>
    </div>

    <!-- 提交记录 Tab - 使用独立组件 -->
    <div v-if="activeTab === 'records'" class="content-section records-section">
      <SubmissionRecordsTab
        :submissions="submissions"
        :questionnaires="questionnaires"
        :loading="loading"
        @delete="handleDeleteSubmissionFromTab"
        @delete-batch="handleBatchDeleteSubmissions"
        @export-pdf="handleExportPDF"
        @refresh="loadData"
            />
          </div>

    <!-- 分发弹窗组件 -->
    <DistributeModal
      v-if="showDistributeModal"
      :questionnaire="selectedQuestionnaireForDistribute"
      @close="showDistributeModal = false"
      @success="handleDistributeSuccess"
    />

    <!-- 查看链接面板组件 -->
    <ViewLinksPanel
      v-if="showViewLinksPanel"
      :questionnaire="viewLinksQuestionnaire"
      @close="showViewLinksPanel = false"
      @create-new="handleCreateNewLink"
    />

    <!-- 提交详情弹窗已移至 SubmissionRecordsTab 组件内部 -->

    <!-- 编辑问卷弹窗 - 使用与问卷中心一样的三列布局 -->
    <div v-if="showEditQuestionnaireModal" class="modal-overlay editor-modal-overlay" @click="showEditQuestionnaireModal = false">
      <div class="modal-dialog editor-modal-dialog" @click.stop>
        <!-- 顶部标题栏 -->
        <div class="editor-modal-header">
          <div class="editor-header-left">
            <h3><i class="ri-edit-line"></i> 编辑问卷</h3>
            <div class="editor-step-tabs">
            <button 
                :class="['step-tab', { active: editStep === 'info' }]"
                @click="editStep = 'info'"
            >
                <i class="ri-file-info-line"></i>
                基本信息
            </button>
              <span class="step-arrow"><i class="ri-arrow-right-s-line"></i></span>
            <button 
                :class="['step-tab', { active: editStep === 'questions' }]"
                @click="editStep = 'questions'"
            >
                <i class="ri-list-settings-line"></i>
                题目编辑
            </button>
          </div>
        </div>
          <button class="btn-close-editor" @click="showEditQuestionnaireModal = false">
            <i class="ri-close-line"></i>
          </button>
        </div>
        
        <!-- Step 1: 基本信息 -->
        <div v-if="editStep === 'info'" class="editor-step-content info-step">
          <div class="info-form-container">
            <div class="form-group">
              <label class="form-label">问卷名称 <span class="required">*</span></label>
              <input 
                type="text" 
                class="form-input" 
                v-model="editQuestionnaireForm.name" 
                placeholder="请输入问卷名称" 
              />
      </div>

            <div class="form-group">
              <label class="form-label">预计时长</label>
              <div class="input-with-suffix">
                <input 
                  type="number" 
                  class="form-input" 
                  v-model.number="editQuestionnaireForm.estimated_minutes" 
                  min="1" 
                  max="120" 
                />
                <span class="input-suffix">分钟</span>
        </div>
        </div>
            
            <div class="form-group">
              <label class="form-label">问卷描述</label>
              <textarea 
                class="form-textarea" 
                rows="3" 
                v-model="editQuestionnaireForm.description" 
                placeholder="请输入问卷描述（选填）"
              ></textarea>
        </div>
          </div>
          
          <div class="info-tip">
            <i class="ri-lightbulb-line"></i>
            <span>请在下一步中编辑题目</span>
        </div>
      </div>

        <!-- Step 2: 题目编辑 - 三列布局 -->
        <div v-if="editStep === 'questions'" class="editor-step-content questions-step">
          <div class="editor-layout-3col">
            <!-- 左侧：控件库 -->
            <div class="controls-library-panel">
              <div class="panel-header">
                <h4><i class="ri-apps-line"></i> 控件库</h4>
                </div>
              <div class="controls-list">
                <div 
                  v-for="ctrl in questionControls" 
                  :key="ctrl.type"
                  class="control-item"
                  draggable="true"
                  @click="addQuestionFromControl(ctrl.type as EditorQuestion['type'])"
                  @dragstart="handleControlDragStart($event, ctrl.type)"
                  @dragend="handleControlDragEnd"
                  :title="`点击或拖拽添加${ctrl.label}`"
                >
                  <i :class="ctrl.icon"></i>
                  <span>{{ ctrl.label }}</span>
                </div>
      </div>
        </div>
        
            <!-- 中间：题目列表 -->
            <div 
              class="questions-list-panel"
              @dragover.prevent="handleListDragOver"
              @drop="handleListDrop"
              @dragleave="isDragOver = false"
              :class="{ 'drag-over': isDragOver }"
          >
              <div class="panel-header">
                <h4><i class="ri-list-ordered"></i> 题目列表</h4>
                <span class="question-count">{{ editorQuestions.length }} 道题</span>
                </div>
              
              <div class="questions-list-scroll">
                <div v-if="questionsLoading" class="questions-loading">
                  <i class="ri-loader-4-line spin"></i>
                  <span>加载题目中...</span>
              </div>
                
                <div v-else-if="editorQuestions.length === 0" class="empty-questions">
                  <i class="ri-file-add-line"></i>
                  <p>暂无题目</p>
                  <p class="text-muted">从左侧拖拽控件添加题目</p>
            </div>
            
                <div 
                  v-for="(q, localIndex) in paginatedQuestions" 
                  :key="q.id || localIndex" 
                  class="question-list-item"
              >
                  <div class="question-drag-handle">
                    <i class="ri-draggable"></i>
                </div>
                  <div class="question-item-content">
                    <div class="question-item-header">
                      <span class="question-number">{{ getGlobalIndex(localIndex) + 1 }}</span>
                      <span class="question-type-badge" :class="q.type">{{ getQuestionTypeName(q.type) }}</span>
                      <span v-if="q.required" class="required-badge">必答</span>
                      <span v-if="q.dimension" class="dimension-badge">{{ q.dimension }}</span>
                </div>
                    <p class="question-text-preview">{{ q.text || '未填写题目内容' }}</p>
                    <!-- 选项内容展示 -->
                    <div v-if="q.type === 'choice' && (q.optionA || q.optionB)" class="question-options-preview">
                      <div class="option-preview-item">
                        <span class="option-letter">A</span>
                        <span class="option-text">{{ q.optionA || '选项A' }}</span>
                      </div>
                      <div class="option-preview-item">
                        <span class="option-letter">B</span>
                        <span class="option-text">{{ q.optionB || '选项B' }}</span>
                      </div>
                    </div>
                    <div v-else-if="q.type === 'yesno'" class="question-options-preview">
                      <div class="option-preview-item">
                        <span class="option-letter yes">是</span>
                      </div>
                      <div class="option-preview-item">
                        <span class="option-letter no">否</span>
                      </div>
                    </div>
                    <div v-else-if="(q.type === 'radio' || q.type === 'checkbox') && q.options?.length" class="question-options-preview">
                      <div v-for="(opt, optIdx) in q.options.slice(0, 4)" :key="optIdx" class="option-preview-item">
                        <span class="option-letter">{{ String.fromCharCode(65 + optIdx) }}</span>
                        <span class="option-text">{{ opt.label }}</span>
                      </div>
                      <div v-if="q.options.length > 4" class="option-preview-more">
                        +{{ q.options.length - 4 }} 个选项
                      </div>
                    </div>
                  </div>
                  <div class="question-item-actions">
                    <button class="btn-icon-small" @click="moveQuestion(getGlobalIndex(localIndex), 'up')" :disabled="getGlobalIndex(localIndex) === 0" title="上移">
                      <i class="ri-arrow-up-s-line"></i>
                  </button>
                    <button class="btn-icon-small" @click="moveQuestion(getGlobalIndex(localIndex), 'down')" :disabled="getGlobalIndex(localIndex) === editorQuestions.length - 1" title="下移">
                      <i class="ri-arrow-down-s-line"></i>
                    </button>
                    <button class="btn-icon-small" @click="handleEditQuestion(getGlobalIndex(localIndex))" title="编辑">
                      <i class="ri-edit-line"></i>
                    </button>
                    <button class="btn-icon-small btn-danger" @click="handleDeleteQuestion(getGlobalIndex(localIndex))" title="删除">
                    <i class="ri-delete-bin-line"></i>
                  </button>
                </div>
              </div>
            </div>
              
              <!-- 分页控件 -->
              <div v-if="editorQuestions.length > questionsPageSize" class="questions-pagination">
                <button 
                  class="pagination-btn" 
                  :disabled="questionsCurrentPage === 1"
                  @click="questionsCurrentPage--"
                >
                  <i class="ri-arrow-left-s-line"></i>
                </button>
                
                <div class="pagination-pages">
                  <template v-for="(page, idx) in visiblePages" :key="idx">
                    <span v-if="page === '...'" class="pagination-ellipsis">...</span>
                    <button 
                      v-else
                      class="pagination-page-btn"
                      :class="{ active: questionsCurrentPage === page }"
                      @click="goToPage(page as number)"
                    >
                      {{ page }}
                    </button>
                  </template>
          </div>
          
                <button 
                  class="pagination-btn" 
                  :disabled="questionsCurrentPage >= totalPages"
                  @click="questionsCurrentPage++"
                >
                  <i class="ri-arrow-right-s-line"></i>
                </button>
                
                <span class="pagination-info">共 {{ editorQuestions.length }} 题</span>
          </div>
              
              <button class="btn-add-question-panel" @click="handleAddQuestion">
                <i class="ri-add-line"></i>
                添加题目
              </button>
        </div>
            
            <!-- 右侧：实时预览 -->
            <CandidatePreviewPanel :questions="editorQuestions" />
      </div>
    </div>

        <!-- 底部 -->
        <div class="editor-modal-footer">
          <div class="footer-left">
            <span v-if="editStep === 'questions'" class="questions-summary">
              <i class="ri-file-list-3-line"></i>
              共 {{ editorQuestions.length }} 道题目
            </span>
          </div>
          <div class="footer-right">
            <button v-if="editStep === 'info'" class="btn-cancel" @click="showEditQuestionnaireModal = false">取消</button>
            <button v-if="editStep === 'questions'" class="btn-secondary" @click="editStep = 'info'">
              <i class="ri-arrow-left-line"></i>
              上一步
            </button>
            <button v-if="editStep === 'info'" class="btn-primary" @click="editStep = 'questions'">
              下一步
              <i class="ri-arrow-right-line"></i>
            </button>
            <button v-if="editStep === 'questions'" class="btn-primary" @click="handleSaveQuestionnaire" :disabled="loading">
              <i v-if="loading" class="ri-loader-4-line spin"></i>
              <i v-else class="ri-check-line"></i>
              {{ loading ? '保存中...' : '保存问卷' }}
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- 题目编辑弹窗 -->
    <QuestionEditDialog
      v-if="showQuestionEditDialog"
      :question="editingQuestion"
      :is-edit="editingQuestionIndex !== null"
      :assessment-type="editQuestionnaireForm.type?.toUpperCase() as 'MBTI' | 'DISC' | 'EPQ' | null"
      @close="showQuestionEditDialog = false"
      @save="handleSaveQuestion"
    />

    <!-- 删除问卷确认弹窗 -->
    <div v-if="showDeleteQuestionnaireModal" class="modal-overlay" @click="showDeleteQuestionnaireModal = false">
      <div class="modal-dialog confirm-modal" @click.stop>
        <div class="modal-header">
          <h3>确认删除问卷</h3>
        </div>
        <div class="modal-body confirm-body">
          <p>确定要删除问卷 <strong>{{ deleteTargetQuestionnaire?.name }}</strong> 吗？</p>
          <p class="confirm-warning">
            <i class="ri-error-warning-line"></i>
            此操作不可恢复，相关的分发链接和提交记录也将被删除
          </p>
        </div>
        <div class="modal-footer">
          <button class="btn-cancel" @click="showDeleteQuestionnaireModal = false">取消</button>
          <button class="btn-danger" @click="confirmDeleteQuestionnaire" :disabled="loading">
            {{ loading ? '删除中...' : '确认删除' }}
          </button>
        </div>
      </div>
    </div>

    <!-- 状态切换确认弹窗 -->
    <div v-if="showToggleStatusConfirm" class="modal-overlay" @click="cancelToggleStatus">
      <div class="modal-dialog confirm-modal" @click.stop>
        <div class="modal-icon" :class="toggleTargetQuestionnaire?.status === 'active' ? 'warning' : 'success'">
          <i :class="toggleTargetQuestionnaire?.status === 'active' ? 'ri-pause-circle-line' : 'ri-play-circle-line'"></i>
        </div>
        <h3 v-if="toggleTargetQuestionnaire?.status === 'active'">停用问卷</h3>
        <h3 v-else>启用问卷</h3>
        <p v-if="toggleTargetQuestionnaire?.status === 'active'">确定要停用问卷「{{ toggleTargetQuestionnaire?.name }}」吗？</p>
        <p v-else>确定要启用问卷「{{ toggleTargetQuestionnaire?.name }}」吗？</p>
        <p class="confirm-warning" v-if="toggleTargetQuestionnaire?.status === 'active'">
          <i class="ri-information-line"></i>
          停用后，该问卷将无法被分发，已分发的链接仍可继续使用。
        </p>
        <p class="confirm-warning success" v-else>
          <i class="ri-information-line"></i>
          启用后，该问卷将可以被分发。
        </p>
        <div class="modal-footer centered">
          <button class="btn-cancel" @click="cancelToggleStatus">取消</button>
          <button 
            :class="toggleTargetQuestionnaire?.status === 'active' ? 'btn-warning' : 'btn-primary'" 
            @click="executeToggleStatus"
            :disabled="loading"
          >
            <span v-if="toggleTargetQuestionnaire?.status === 'active'">确认停用</span>
            <span v-else>确认启用</span>
          </button>
        </div>
      </div>
    </div>

    <!-- 消息提示 -->
    <Transition name="message">
      <div v-if="message.show" :class="['message-toast', message.type]">
        <i :class="[
          message.type === 'success' ? 'ri-check-line' :
          message.type === 'error' ? 'ri-close-line' :
          message.type === 'warning' ? 'ri-alert-line' : 'ri-information-line'
        ]"></i>
        <span>{{ message.text }}</span>
      </div>
    </Transition>
  </div>
</template>

<style scoped>
@import './styles/professional-assessment.css';
</style>
