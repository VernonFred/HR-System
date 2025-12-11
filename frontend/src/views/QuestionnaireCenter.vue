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
  closeEditorModal()
  loadData()
}

// ===== 分发弹窗 =====
const showDistributeModal = ref(false)
const distributeQuestionnaire = ref<Questionnaire | null>(null)

const openDistributeModal = (q: Questionnaire) => {
  distributeQuestionnaire.value = q
  showDistributeModal.value = true
}

const closeDistributeModal = () => {
  showDistributeModal.value = false
  distributeQuestionnaire.value = null
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
      @close="closeDistributeModal"
      @success="handleDistributeSuccess"
    />

    <!-- 查看链接面板 -->
    <ViewLinksPanel
      v-if="showViewLinksPanel"
      :questionnaire="viewLinksQuestionnaire"
      @close="closeViewLinksPanel"
      @create-new="handleCreateNewLink"
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
.questionnaire-center {
  padding: 24px;
  min-height: 100vh;
  background: transparent;
}

/* 页面头部 */
.page-header {
  display: flex;
  align-items: center;
  gap: 20px;
  padding: 32px;
  background: linear-gradient(135deg, #14b8a6 0%, #0d9488 50%, #0f766e 100%);
  border-radius: 20px;
  margin-bottom: 24px;
  box-shadow: 0 4px 12px rgba(20, 184, 166, 0.15);
}

.header-icon {
  width: 64px;
  height: 64px;
  background: rgba(255, 255, 255, 0.2);
  border-radius: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 32px;
  color: white;
}

.header-content h1 {
  font-size: 28px;
  font-weight: 700;
  color: white;
  margin: 0 0 8px;
}

.header-content p {
  font-size: 14px;
  color: rgba(255, 255, 255, 0.8);
  margin: 0;
}

/* 问卷库区域 */
.questionnaire-section {
  background: white;
  border-radius: 16px;
  padding: 24px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
}

.section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 24px;
}

.section-header h2 {
  font-size: 18px;
  font-weight: 600;
  color: #1e293b;
  margin: 0;
}

.section-actions {
  display: flex;
  gap: 12px;
}

/* 问卷网格 */
.questionnaires-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 20px;
}

/* 加载状态 */
.loading-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px 20px;
  color: #64748b;
  gap: 12px;
}

.loading-state i {
  font-size: 32px;
}

.spin {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

/* 空状态 */
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px 20px;
  color: #94a3b8;
}

.empty-state i {
  font-size: 48px;
  margin-bottom: 16px;
  opacity: 0.5;
}

.empty-state p {
  font-size: 16px;
  font-weight: 500;
  color: #64748b;
  margin: 0 0 8px;
}

.empty-state span {
  font-size: 14px;
  margin-bottom: 20px;
}

/* 按钮样式 */
.btn-primary {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 10px 20px;
  background: linear-gradient(135deg, #6366f1, #8b5cf6);
  color: white;
  border: none;
  border-radius: 10px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-primary:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(99, 102, 241, 0.3);
}

.btn-secondary {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 10px 20px;
  background: #f1f5f9;
  color: #475569;
  border: none;
  border-radius: 10px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-secondary:hover {
  background: #e2e8f0;
}

.btn-danger {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 10px 20px;
  background: linear-gradient(135deg, #ef4444, #dc2626);
  color: white;
  border: none;
  border-radius: 10px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-danger:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(239, 68, 68, 0.3);
}

/* 删除确认弹窗 */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.delete-confirm-modal {
  background: white;
  border-radius: 16px;
  padding: 32px;
  max-width: 400px;
  text-align: center;
}

.modal-icon {
  width: 64px;
  height: 64px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto 20px;
  font-size: 32px;
}

.modal-icon.warning {
  background: #fef3c7;
  color: #d97706;
}

.modal-icon.success {
  background: #d1fae5;
  color: #059669;
}

.delete-confirm-modal h3,
.status-confirm-modal h3 {
  font-size: 20px;
  font-weight: 600;
  color: #1e293b;
  margin: 0 0 12px;
}

.delete-confirm-modal p,
.status-confirm-modal p {
  font-size: 14px;
  color: #64748b;
  margin: 0 0 8px;
}

.warning-text {
  color: #ef4444 !important;
  font-size: 13px !important;
}

.info-text {
  color: #64748b !important;
  font-size: 13px !important;
}

.status-confirm-modal {
  background: white;
  border-radius: 16px;
  padding: 32px;
  max-width: 400px;
  text-align: center;
}

.btn-warning {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 12px 24px;
  background: linear-gradient(135deg, #f59e0b, #d97706);
  color: white;
  border: none;
  border-radius: 10px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-warning:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(245, 158, 11, 0.3);
}

.btn-success {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 12px 24px;
  background: linear-gradient(135deg, #10b981, #059669);
  color: white;
  border: none;
  border-radius: 10px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-success:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(16, 185, 129, 0.3);
}

.modal-actions {
  display: flex;
  gap: 12px;
  justify-content: center;
  margin-top: 24px;
}

/* 消息提示 */
.message-toast {
  position: fixed;
  top: 24px;
  left: 50%;
  transform: translateX(-50%);
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 24px;
  border-radius: 10px;
  font-size: 14px;
  font-weight: 500;
  z-index: 2000;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

.message-toast.success {
  background: #d1fae5;
  color: #059669;
}

.message-toast.error {
  background: #fee2e2;
  color: #dc2626;
}

.message-toast.warning {
  background: #fef3c7;
  color: #d97706;
}

.message-toast.info {
  background: #dbeafe;
  color: #2563eb;
}

.message-enter-active,
.message-leave-active {
  transition: all 0.3s ease;
}

.message-enter-from,
.message-leave-to {
  opacity: 0;
  transform: translate(-50%, -20px);
}

/* V43: 导入按钮 */
.btn-outline {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 10px 20px;
  background: white;
  color: #6366f1;
  border: 1px solid #6366f1;
  border-radius: 10px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-outline:hover {
  background: #f0f0ff;
}

/* V43: 导入弹窗 */
.import-modal {
  background: white;
  border-radius: 16px;
  width: 520px;
  max-width: 90vw;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.2);
  overflow: hidden;
}

.import-modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 20px 24px;
  background: linear-gradient(135deg, #14b8a6, #0d9488);
}

.import-modal-header h3 {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
  color: white;
  display: flex;
  align-items: center;
  gap: 8px;
}

.import-modal-header .btn-close {
  background: rgba(255, 255, 255, 0.2);
  border: none;
  width: 32px;
  height: 32px;
  border-radius: 8px;
  color: white;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
  transition: background 0.2s;
}

.import-modal-header .btn-close:hover {
  background: rgba(255, 255, 255, 0.3);
}

.import-modal-body {
  padding: 24px;
}

.import-dropzone {
  border: 2px dashed #d1d5db;
  border-radius: 12px;
  padding: 40px 20px;
  text-align: center;
  cursor: pointer;
  transition: all 0.2s;
  background: #fafafa;
}

.import-dropzone:hover {
  border-color: #6366f1;
  background: #f0f0ff;
}

.dropzone-icon {
  font-size: 48px;
  color: #6366f1;
  margin-bottom: 16px;
}

.dropzone-title {
  font-size: 16px;
  font-weight: 500;
  color: #374151;
  margin: 0 0 8px;
}

.dropzone-hint {
  font-size: 13px;
  color: #9ca3af;
  margin: 0;
}

/* V45: AI解析开关样式 */
.import-options {
  margin-top: 16px;
  padding: 12px 16px;
  background: linear-gradient(135deg, rgba(99, 102, 241, 0.08), rgba(139, 92, 246, 0.05));
  border-radius: 10px;
  border: 1px solid rgba(99, 102, 241, 0.15);
}

.ai-toggle {
  display: flex;
  align-items: center;
  gap: 12px;
  cursor: pointer;
  user-select: none;
}

.ai-toggle input[type="checkbox"] {
  display: none;
}

.toggle-slider {
  position: relative;
  width: 44px;
  height: 24px;
  background: #d1d5db;
  border-radius: 12px;
  transition: all 0.3s ease;
  flex-shrink: 0;
}

.toggle-slider::after {
  content: '';
  position: absolute;
  top: 2px;
  left: 2px;
  width: 20px;
  height: 20px;
  background: white;
  border-radius: 50%;
  transition: all 0.3s ease;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.15);
}

.ai-toggle input:checked + .toggle-slider {
  background: linear-gradient(135deg, #6366f1, #8b5cf6);
}

.ai-toggle input:checked + .toggle-slider::after {
  left: 22px;
}

.toggle-label {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 14px;
  font-weight: 600;
  color: #374151;
}

.toggle-label i {
  font-size: 16px;
  color: #6366f1;
}

.toggle-hint {
  font-size: 12px;
  color: #9ca3af;
  margin-left: auto;
}

.import-tips {
  margin-top: 20px;
  padding: 16px;
  background: #f8fafc;
  border-radius: 10px;
}

.import-tips h4 {
  font-size: 14px;
  font-weight: 600;
  color: #475569;
  margin: 0 0 12px;
  display: flex;
  align-items: center;
  gap: 6px;
}

.import-tips h4 i {
  color: #f59e0b;
}

.import-tips ul {
  margin: 0;
  padding-left: 20px;
  font-size: 13px;
  color: #64748b;
  line-height: 1.8;
}

.import-tips strong {
  color: #334155;
}

.import-error {
  margin-top: 16px;
  padding: 12px 16px;
  background: #fef2f2;
  border-radius: 8px;
  color: #dc2626;
  font-size: 13px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.import-modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  padding: 16px 24px;
  background: #f8fafc;
  border-top: 1px solid #e2e8f0;
}

/* 弹窗动画 */
.modal-enter-active,
.modal-leave-active {
  transition: opacity 0.3s ease;
}

.modal-enter-active .import-modal,
.modal-leave-active .import-modal {
  transition: transform 0.3s ease;
}

.modal-enter-from,
.modal-leave-to {
  opacity: 0;
}

.modal-enter-from .import-modal {
  transform: scale(0.95) translateY(-20px);
}

.modal-leave-to .import-modal {
  transform: scale(0.95) translateY(20px);
}

/* 响应式 */
@media (max-width: 768px) {
  .questionnaires-grid {
    grid-template-columns: 1fr;
  }
  
  .import-modal {
    width: 100%;
    max-width: 100%;
    border-radius: 16px 16px 0 0;
  }
}
</style>

