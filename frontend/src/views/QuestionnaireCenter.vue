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

const openDetailDrawer = (q: Questionnaire) => {
  selectedQuestionnaire.value = q
  showDetailDrawer.value = true
}

const closeDetailDrawer = () => {
  showDetailDrawer.value = false
  selectedQuestionnaire.value = null
}

// ⭐ V44: 删除单条提交记录
const handleDeleteSubmission = async (submission: Submission) => {
  try {
    await deleteSubmission(submission.id)
    showMessage('删除成功', 'success')
    // V45: 删除成功后重新加载数据
    await loadData()
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

<template>
  <div class="questionnaire-center">
    <!-- 页面头部 -->
    <header class="page-header">
      <div class="header-icon">
        <i class="ri-questionnaire-line"></i>
      </div>
      <div class="header-content">
        <h1>问卷中心</h1>
      </div>
    </header>


    <!-- 问卷库 -->
    <section class="questionnaire-section">
      <div class="section-header">
        <h2>问卷库</h2>
        <div class="section-actions">
          <!-- V43: 导入问卷按钮 -->
          <button class="btn-outline" @click="openImportModal">
            <i class="ri-upload-2-line"></i>
            导入问卷
          </button>
          <button class="btn-secondary" @click="openCreateModal">
            <i class="ri-add-line"></i>
            创建问卷
          </button>
        </div>
      </div>

      <!-- V43: 隐藏的文件输入 -->
      <input
        ref="importFileInput"
        type="file"
        accept=".json,.xlsx,.xls,.docx,.txt"
        style="display: none"
        @change="handleImportFile"
      />

      <!-- 加载中 -->
      <div v-if="loading" class="loading-state">
        <i class="ri-loader-4-line spin"></i>
        <span>加载中...</span>
      </div>

      <!-- 问卷列表 -->
      <div v-else-if="questionnaires.length > 0" class="questionnaires-grid">
        <QuestionnaireCard
          v-for="q in questionnaires"
          :key="q.id"
          :questionnaire="q"
          category="custom"
          @view-detail="openDetailDrawer"
          @edit="openEditModal"
          @copy="handleCopyQuestionnaire"
          @delete="confirmDelete"
          @distribute="openDistributeModal"
          @view-links="openViewLinksPanel"
          @toggle-status="openToggleStatusConfirm"
        />
      </div>

      <!-- 空状态 -->
      <div v-else class="empty-state">
        <i class="ri-file-list-line"></i>
        <p>暂无问卷</p>
        <span>点击"创建问卷"开始创建您的第一份问卷</span>
        <button class="btn-primary" @click="openCreateModal">
          <i class="ri-add-line"></i>
          创建问卷
        </button>
      </div>
    </section>

    <!-- 问卷详情抽屉 -->
    <QuestionnaireDetailDrawer
      v-if="showDetailDrawer"
      :questionnaire="selectedQuestionnaire"
      :submissions="submissions.filter(s => s.questionnaire_id === selectedQuestionnaire?.id)"
      @close="closeDetailDrawer"
      @distribute="openDistributeModal"
      @delete-submission="handleDeleteSubmission"
      @delete-batch="handleBatchDeleteSubmissions"
    />

    <!-- 问卷编辑器弹窗 -->
    <QuestionnaireEditorModal
      v-if="showEditorModal"
      :questionnaire="editingQuestionnaire"
      :imported-data="importedQuestions"
      @close="closeEditorModal"
      @save="handleEditorSave"
    />

    <!-- V43: 导入问卷弹窗 -->
    <Teleport to="body">
      <Transition name="modal">
        <div v-if="showImportModal" class="modal-overlay" @click="closeImportModal">
          <div class="import-modal" @click.stop>
            <div class="import-modal-header">
              <h3><i class="ri-upload-cloud-2-line"></i> 导入问卷</h3>
              <button class="btn-close" @click="closeImportModal">
                <i class="ri-close-line"></i>
              </button>
            </div>
            <div class="import-modal-body">
              <div class="import-dropzone" @click="triggerFileSelect">
                <div class="dropzone-icon">
                  <i class="ri-file-upload-line"></i>
                </div>
                <p class="dropzone-title">点击选择文件或拖拽到此处</p>
                <p class="dropzone-hint">支持 JSON、Excel (.xlsx)、Word (.docx)、纯文本 (.txt) 格式</p>
              </div>

              <!-- V45: AI智能解析开关 -->
              <div class="import-options">
                <label class="ai-toggle">
                  <input type="checkbox" v-model="useAIImport" />
                  <span class="toggle-slider"></span>
                  <span class="toggle-label">
                    <i class="ri-robot-line"></i>
                    AI智能解析
                  </span>
                  <span class="toggle-hint">{{ useAIImport ? '更准确识别题目类型和选项' : '使用规则匹配（更快）' }}</span>
                </label>
              </div>

              <div class="import-tips">
                <h4><i class="ri-lightbulb-line"></i> 导入说明</h4>
                <ul>
                  <li><strong>JSON格式：</strong>标准问卷结构，包含题目和选项</li>
                  <li><strong>Excel格式：</strong>每行一道题，选项用换行或分列表示</li>
                  <li><strong>Word格式：</strong>按题号格式（1. 或 Q1）识别题目</li>
                  <li><strong>纯文本：</strong>按题号和选项标记（A. B. C.）解析</li>
                </ul>
              </div>

              <div v-if="importError" class="import-error">
                <i class="ri-error-warning-line"></i>
                {{ importError }}
              </div>
            </div>
            <div class="import-modal-footer">
              <button class="btn-secondary" @click="closeImportModal">取消</button>
              <button class="btn-primary" @click="triggerFileSelect" :disabled="importLoading">
                <i v-if="importLoading" class="ri-loader-4-line spin"></i>
                <i v-else class="ri-upload-2-line"></i>
                {{ importLoading ? '解析中...' : '选择文件' }}
              </button>
            </div>
          </div>
        </div>
      </Transition>
    </Teleport>

    <!-- 分发弹窗 -->
    <DistributeModal
      v-if="showDistributeModal"
      :questionnaire="distributeQuestionnaire"
      :assessment="distributeAssessment"
      :mode="distributeMode"
      @close="closeDistributeModal"
      @success="handleDistributeSuccess"
    />

    <!-- 查看链接面板 -->
    <ViewLinksPanel
      v-if="showViewLinksPanel"
      :questionnaire="viewLinksQuestionnaire"
      @close="closeViewLinksPanel"
      @create-new="handleCreateNewLink"
      @edit="handleEditDistribution"
      @clone="handleCloneDistribution"
    />

    <!-- 删除确认弹窗 -->
    <div v-if="showDeleteConfirm" class="modal-overlay" @click="cancelDelete">
      <div class="delete-confirm-modal" @click.stop>
        <div class="modal-icon warning">
          <i class="ri-error-warning-line"></i>
        </div>
        <h3>确认删除</h3>
        <p>确定要删除问卷「{{ deleteTarget?.name }}」吗？</p>
        <p class="warning-text">此操作不可恢复，相关的提交记录也将被删除。</p>
        <div class="modal-actions">
          <button class="btn-secondary" @click="cancelDelete">取消</button>
          <button class="btn-danger" @click="executeDelete">确认删除</button>
        </div>
      </div>
    </div>

    <!-- 状态切换确认弹窗 -->
    <div v-if="showToggleStatusConfirm" class="modal-overlay" @click="cancelToggleStatus">
      <div class="status-confirm-modal" @click.stop>
        <div class="modal-icon" :class="toggleStatusTarget?.status === 'active' ? 'warning' : 'success'">
          <i :class="toggleStatusTarget?.status === 'active' ? 'ri-pause-circle-line' : 'ri-play-circle-line'"></i>
        </div>
        <h3>{{ toggleStatusTarget?.status === 'active' ? '停用问卷' : '启用问卷' }}</h3>
        <p>确定要{{ toggleStatusTarget?.status === 'active' ? '停用' : '启用' }}问卷「{{ toggleStatusTarget?.name }}」吗？</p>
        <p class="info-text" v-if="toggleStatusTarget?.status === 'active'">
          停用后，该问卷将无法被分发，已分发的链接仍可继续使用。
        </p>
        <p class="info-text" v-else>
          启用后，该问卷可以被分发给候选人。
        </p>
        <div class="modal-actions">
          <button class="btn-secondary" @click="cancelToggleStatus">取消</button>
          <button
            :class="toggleStatusTarget?.status === 'active' ? 'btn-warning' : 'btn-success'"
            @click="executeToggleStatus"
          >
            {{ toggleStatusTarget?.status === 'active' ? '确认停用' : '确认启用' }}
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
@import './styles/questionnaire-center.css';
</style>
