<script setup lang="ts">
/**
 * 查看链接面板组件
 * 
 * 功能：
 * 1. 显示问卷的所有分发链接
 * 2. 复制链接
 * 3. 下载二维码
 * 4. 创建新链接
 */
import { ref, computed, onMounted } from 'vue'
import QRCode from 'qrcode'
import {
  fetchAssessments,
  deleteAssessment,
  type Questionnaire,
  type Assessment,
} from '../api/assessments'

// ===== Props =====
const props = defineProps<{
  questionnaire: Questionnaire | null
}>()

// ===== Emits =====
const emit = defineEmits<{
  (e: 'close'): void
  (e: 'create-new'): void
}>()

// ===== 状态 =====
const loading = ref(false)
const distributions = ref<DistributionInfo[]>([])
const copiedLink = ref('')

// 删除确认弹窗
const showDeleteModal = ref(false)
const deletingDistribution = ref<DistributionInfo | null>(null)
const submissionCount = ref(0)  // 关联的提交记录数量
const showForceDeleteConfirm = ref(false)  // 是否显示强制删除的二次确认

// 分发信息接口
interface DistributionInfo {
  id: number
  name: string
  code: string
  link: string
  qrcode: string
  linkType: 'permanent' | 'temporary'
  validFrom: string
  validUntil: string
  isActive: boolean
  isExpired: boolean
}

// ===== 计算属性 =====
const activeCount = computed(() => distributions.value.filter(d => d.isActive).length)
const expiredCount = computed(() => distributions.value.filter(d => d.isExpired).length)

// ===== 方法 =====
const close = () => emit('close')

const createNew = () => {
  emit('create-new')
}

const loadDistributions = async () => {
  if (!props.questionnaire) return
  
  loading.value = true
  try {
    const res = await fetchAssessments()
    const baseUrl = window.location.origin
    const now = new Date()
    
    // 过滤该问卷的分发记录
    const filtered = res.items.filter(a => a.questionnaire_id === props.questionnaire!.id)
    
    // 转换为分发信息
    distributions.value = await Promise.all(filtered.map(async (a) => {
      const link = `${baseUrl}/assessment/${a.code}`
      const validFrom = new Date(a.valid_from)
      const validUntil = new Date(a.valid_until)
      const isExpired = now > validUntil
      const isActive = now >= validFrom && now <= validUntil
      
      // 判断链接类型（100年后过期视为永久）
      const yearDiff = validUntil.getFullYear() - validFrom.getFullYear()
      const linkType = yearDiff > 50 ? 'permanent' : 'temporary'
      
      let qrcode = ''
      try {
        qrcode = await QRCode.toDataURL(link, { width: 160, margin: 2 })
      } catch (e) {
        console.error('生成二维码失败:', e)
      }
      
      return {
        id: a.id,
        name: a.name,
        code: a.code,
        link,
        qrcode,
        linkType,
        validFrom: validFrom.toLocaleDateString('zh-CN'),
        validUntil: linkType === 'permanent' ? '长期有效' : validUntil.toLocaleDateString('zh-CN'),
        isActive,
        isExpired,
      }
    }))
    
    // 按创建时间倒序排列
    distributions.value.sort((a, b) => b.id - a.id)
    
  } catch (error) {
    console.error('加载分发记录失败:', error)
  } finally {
    loading.value = false
  }
}

const copyLink = async (link: string) => {
  try {
    await navigator.clipboard.writeText(link)
    copiedLink.value = link
    setTimeout(() => { copiedLink.value = '' }, 2000)
  } catch (error) {
    console.error('复制失败:', error)
    // 降级方案
    const textArea = document.createElement('textarea')
    textArea.value = link
    textArea.style.position = 'fixed'
    textArea.style.left = '-999999px'
    document.body.appendChild(textArea)
    textArea.select()
    try {
      document.execCommand('copy')
      copiedLink.value = link
      setTimeout(() => { copiedLink.value = '' }, 2000)
    } catch (err) {
      console.error('复制失败')
    }
    document.body.removeChild(textArea)
  }
}

const downloadQRCode = (dataUrl: string, name: string) => {
  const link = document.createElement('a')
  link.download = `${name}_二维码.png`
  link.href = dataUrl
  link.click()
}

// 打开删除确认弹窗
const openDeleteModal = (dist: DistributionInfo) => {
  deletingDistribution.value = dist
  showDeleteModal.value = true
  showForceDeleteConfirm.value = false
  submissionCount.value = 0
}

// 取消删除
const cancelDelete = () => {
  showDeleteModal.value = false
  deletingDistribution.value = null
  showForceDeleteConfirm.value = false
  submissionCount.value = 0
}

// 确认删除
const confirmDelete = async (force: boolean = false) => {
  if (!deletingDistribution.value) return
  
  try {
    loading.value = true
    await deleteAssessment(deletingDistribution.value.id, force)
    
    // 从列表中移除
    distributions.value = distributions.value.filter(d => d.id !== deletingDistribution.value!.id)
    
    showDeleteModal.value = false
    deletingDistribution.value = null
    showForceDeleteConfirm.value = false
    
    // 如果没有链接了，关闭面板
    if (distributions.value.length === 0) {
      emit('close')
    }
  } catch (error: any) {
    // 检查是否是 409 错误（有提交记录）
    if (error?.response?.status === 409 || error?.detail?.error === 'has_submissions') {
      const detail = error?.detail || error?.response?.data?.detail || {}
      submissionCount.value = detail.submission_count || 0
      showForceDeleteConfirm.value = true
    } else {
    console.error('删除分发失败:', error)
      alert('删除失败，请重试')
    }
  } finally {
    loading.value = false
  }
}

// ===== 生命周期 =====
onMounted(() => {
  loadDistributions()
})
</script>

<template>
  <div class="modal-overlay" @click="close">
    <div class="modal-panel" @click.stop>
      <!-- 头部 -->
      <div class="modal-header">
        <div class="header-title">
          <i class="ri-links-line"></i>
          <h3>{{ questionnaire?.name }} - 链接管理</h3>
        </div>
        <button class="btn-close" @click="close">
          <i class="ri-close-line"></i>
        </button>
      </div>

      <!-- 内容 -->
      <div class="modal-body">
        <!-- 加载中 -->
        <div v-if="loading" class="loading-state">
          <i class="ri-loader-4-line spin"></i>
          <span>加载中...</span>
        </div>

        <!-- 无链接提示 -->
        <div v-else-if="distributions.length === 0" class="empty-state">
          <i class="ri-information-line"></i>
          <p>该问卷尚未生成任何链接</p>
          <span>请点击"分发"按钮创建新的测评链接</span>
        </div>

        <!-- 分发列表 -->
        <div v-else class="distributions-container">
          <!-- 统计 -->
          <div class="summary-bar">
            <span class="summary-badge total">
              <i class="ri-links-line"></i>
              共 {{ distributions.length }} 个链接
            </span>
            <span class="summary-badge active" v-if="activeCount > 0">
              <i class="ri-checkbox-circle-fill"></i>
              {{ activeCount }} 个有效
            </span>
            <span class="summary-badge expired" v-if="expiredCount > 0">
              <i class="ri-time-fill"></i>
              {{ expiredCount }} 个已过期
            </span>
          </div>

          <!-- 链接列表 -->
          <div class="distributions-list">
            <div 
              v-for="dist in distributions" 
              :key="dist.id"
              :class="['distribution-card', { expired: dist.isExpired, active: dist.isActive }]"
            >
              <div class="dist-header">
                <div class="dist-title">
                  <span :class="['type-badge', dist.linkType]">
                    <i :class="dist.linkType === 'permanent' ? 'ri-infinity-line' : 'ri-time-line'"></i>
                    {{ dist.linkType === 'permanent' ? '长期' : '短期' }}
                  </span>
                  <span class="dist-name">{{ dist.name }}</span>
                </div>
                <div class="dist-status">
                  <span v-if="dist.isExpired" class="status expired">
                    <i class="ri-close-circle-fill"></i>
                    已过期
                  </span>
                  <span v-else-if="dist.isActive" class="status active">
                    <i class="ri-checkbox-circle-fill"></i>
                    有效
                  </span>
                  <span v-else class="status pending">
                    <i class="ri-time-line"></i>
                    未开始
                  </span>
                </div>
              </div>

              <div class="dist-meta">
                <i class="ri-calendar-line"></i>
                <span>{{ dist.validFrom }} ~ {{ dist.validUntil }}</span>
              </div>

              <div class="dist-body">
                <div class="qr-section">
                  <img v-if="dist.qrcode" :src="dist.qrcode" :alt="dist.name" />
                  <button 
                    class="btn-download-qr" 
                    @click="downloadQRCode(dist.qrcode, dist.name)"
                    :disabled="!dist.qrcode"
                  >
                    <i class="ri-download-line"></i>
                  </button>
                </div>

                <div class="link-section">
                  <div class="link-box">
                    <input type="text" :value="dist.link" readonly />
                    <button 
                      :class="['btn-copy', { copied: copiedLink === dist.link }]"
                      @click="copyLink(dist.link)"
                    >
                      <i :class="copiedLink === dist.link ? 'ri-check-line' : 'ri-file-copy-line'"></i>
                      {{ copiedLink === dist.link ? '已复制' : '复制' }}
                    </button>
                  </div>
                  <div class="code-info">
                    <span class="code-label">访问码：</span>
                    <span class="code-value">{{ dist.code }}</span>
                  </div>
                </div>
              </div>

              <!-- 操作按钮 -->
              <div class="dist-actions">
                <button class="dist-action-btn delete" @click="openDeleteModal(dist)" title="删除链接">
                  <i class="ri-delete-bin-line"></i>
                  删除
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 底部 -->
      <div class="modal-footer">
        <div class="footer-tip">
          <i class="ri-lightbulb-line"></i>
          <span>每次分发都会生成新链接，旧链接在有效期内仍可使用</span>
        </div>
        <div class="footer-actions">
          <button class="btn-secondary" @click="close">关闭</button>
          <button 
            class="btn-primary" 
            @click="createNew"
            :disabled="questionnaire?.status !== 'active'"
          >
            <i class="ri-add-line"></i>
            创建新链接
          </button>
        </div>
      </div>
    </div>

    <!-- 删除确认弹窗 -->
    <div v-if="showDeleteModal" class="delete-modal-overlay" @click="cancelDelete">
      <div class="modal-delete-confirm" @click.stop>
        <div class="delete-confirm-icon" :class="{ danger: showForceDeleteConfirm }">
          <i class="ri-delete-bin-line"></i>
        </div>
        
        <!-- 第一次确认：普通删除 -->
        <template v-if="!showForceDeleteConfirm">
        <h3>确认删除分发链接？</h3>
        <p class="delete-dist-name">{{ deletingDistribution?.name }}</p>
        <p class="delete-dist-code">访问码：{{ deletingDistribution?.code }}</p>
        <div class="delete-warning">
          <i class="ri-error-warning-line"></i>
            <span>删除后，已分发的二维码和链接将失效</span>
        </div>
        </template>
        
        <!-- 第二次确认：强制删除（有提交记录） -->
        <template v-else>
          <h3>⚠️ 警告：该链接下有提交数据</h3>
          <p class="delete-dist-name">{{ deletingDistribution?.name }}</p>
          <div class="submissions-warning">
            <i class="ri-file-warning-line"></i>
            <div class="warning-content">
              <p class="warning-title">该分发链接下有 <strong>{{ submissionCount }}</strong> 条提交记录</p>
              <p class="warning-desc">删除链接将同时删除所有提交数据，此操作<strong>不可恢复</strong>！</p>
            </div>
          </div>
        </template>
        
        <div class="delete-confirm-actions">
          <button class="btn-secondary" @click="cancelDelete">取消</button>
          <button 
            v-if="!showForceDeleteConfirm"
            class="btn-danger" 
            @click="confirmDelete(false)" 
            :disabled="loading"
          >
            <i class="ri-delete-bin-line"></i>
            确认删除
          </button>
          <button 
            v-else
            class="btn-danger-strong" 
            @click="confirmDelete(true)" 
            :disabled="loading"
          >
            <i class="ri-alert-line"></i>
            仍要删除（含 {{ submissionCount }} 条数据）
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
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

.modal-panel {
  background: white;
  border-radius: 20px;
  width: 100%;
  max-width: 700px;
  max-height: 85vh;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.2);
}

/* 头部 */
.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 20px 24px;
  border-bottom: 1px solid #e2e8f0;
  background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);
  color: white;
}

.header-title {
  display: flex;
  align-items: center;
  gap: 12px;
}

.header-title i {
  font-size: 24px;
}

.header-title h3 {
  font-size: 18px;
  font-weight: 600;
  margin: 0;
}

.btn-close {
  width: 36px;
  height: 36px;
  border: none;
  background: rgba(255, 255, 255, 0.2);
  border-radius: 10px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  font-size: 20px;
  transition: all 0.2s;
}

.btn-close:hover {
  background: rgba(255, 255, 255, 0.3);
}

/* 内容 */
.modal-body {
  flex: 1;
  overflow-y: auto;
  padding: 24px;
}

/* 加载/空状态 */
.loading-state,
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px 20px;
  color: #64748b;
}

.loading-state i,
.empty-state i {
  font-size: 48px;
  margin-bottom: 16px;
  opacity: 0.5;
}

.empty-state p {
  font-size: 16px;
  font-weight: 500;
  color: #334155;
  margin: 0 0 8px;
}

.empty-state span {
  font-size: 14px;
}

/* 统计栏 */
.summary-bar {
  display: flex;
  gap: 12px;
  margin-bottom: 20px;
}

.summary-badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 8px 14px;
  border-radius: 20px;
  font-size: 13px;
  font-weight: 500;
}

.summary-badge.total {
  background: #f1f5f9;
  color: #475569;
}

.summary-badge.active {
  background: #d1fae5;
  color: #065f46;
}

.summary-badge.expired {
  background: #fee2e2;
  color: #dc2626;
}

/* 分发列表 */
.distributions-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.distribution-card {
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 16px;
  padding: 20px;
  transition: all 0.2s;
}

.distribution-card.active {
  border-color: #10b981;
  background: #f0fdf4;
}

.distribution-card.expired {
  opacity: 0.7;
  border-color: #fecaca;
  background: #fef2f2;
}

.dist-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}

.dist-title {
  display: flex;
  align-items: center;
  gap: 10px;
}

.type-badge {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 4px 10px;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 600;
}

.type-badge.permanent {
  background: #dbeafe;
  color: #1d4ed8;
}

.type-badge.temporary {
  background: #fef3c7;
  color: #d97706;
}

.dist-name {
  font-size: 15px;
  font-weight: 600;
  color: #1e293b;
}

.dist-status .status {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 4px 10px;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 500;
}

.status.active {
  background: #d1fae5;
  color: #065f46;
}

.status.expired {
  background: #fee2e2;
  color: #dc2626;
}

.status.pending {
  background: #fef3c7;
  color: #92400e;
}

.dist-meta {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  color: #64748b;
  margin-bottom: 16px;
}

.dist-body {
  display: flex;
  gap: 20px;
}

.qr-section {
  position: relative;
  flex-shrink: 0;
}

.qr-section img {
  width: 120px;
  height: 120px;
  border-radius: 12px;
  border: 1px solid #e2e8f0;
}

.btn-download-qr {
  position: absolute;
  bottom: 8px;
  right: 8px;
  width: 28px;
  height: 28px;
  border: none;
  background: rgba(0, 0, 0, 0.6);
  border-radius: 6px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  font-size: 14px;
  transition: all 0.2s;
}

.btn-download-qr:hover {
  background: rgba(0, 0, 0, 0.8);
}

.link-section {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.link-box {
  display: flex;
  gap: 8px;
}

.link-box input {
  flex: 1;
  padding: 10px 14px;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  font-size: 13px;
  background: white;
}

.btn-copy {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 10px 16px;
  background: #6366f1;
  color: white;
  border: none;
  border-radius: 10px;
  font-size: 13px;
  cursor: pointer;
  transition: all 0.2s;
  white-space: nowrap;
}

.btn-copy:hover {
  background: #4f46e5;
}

.btn-copy.copied {
  background: #10b981;
}

.code-info {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
}

.code-label {
  color: #64748b;
}

.code-value {
  font-family: monospace;
  font-weight: 600;
  color: #334155;
  padding: 4px 10px;
  background: white;
  border-radius: 6px;
  border: 1px solid #e2e8f0;
}

/* 底部 */
.modal-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 24px;
  border-top: 1px solid #e2e8f0;
  background: #f8fafc;
}

.footer-tip {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  color: #64748b;
}

.footer-tip i {
  color: #f59e0b;
}

.footer-actions {
  display: flex;
  gap: 12px;
}

.btn-primary {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 12px 24px;
  background: linear-gradient(135deg, #6366f1, #8b5cf6);
  color: white;
  border: none;
  border-radius: 12px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-primary:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(99, 102, 241, 0.3);
}

.btn-primary:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.btn-secondary {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 12px 24px;
  background: white;
  color: #475569;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-secondary:hover {
  background: #f1f5f9;
}

.spin {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

/* 操作按钮 */
.dist-actions {
  display: flex;
  justify-content: flex-end;
  padding-top: 12px;
  border-top: 1px solid #e2e8f0;
  margin-top: 16px;
}

.dist-action-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 8px 14px;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
  border: 1px solid transparent;
}

.dist-action-btn.delete {
  background: white;
  border-color: #e2e8f0;
  color: #6b7280;
}

.dist-action-btn.delete:hover {
  background: #ef4444;
  border-color: #ef4444;
  color: white;
}

/* 删除确认弹窗 */
.delete-modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.6);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1100;
}

.modal-delete-confirm {
  width: 400px;
  max-width: 90vw;
  padding: 2rem;
  text-align: center;
  background: white;
  border-radius: 16px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.2);
}

.delete-confirm-icon {
  width: 64px;
  height: 64px;
  margin: 0 auto 1.25rem;
  background: linear-gradient(135deg, #fee2e2 0%, #fecaca 100%);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
}

.delete-confirm-icon i {
  font-size: 2rem;
  color: #dc2626;
}

.delete-confirm-icon.danger {
  background: linear-gradient(135deg, #dc2626 0%, #991b1b 100%);
}

.delete-confirm-icon.danger i {
  color: white;
}

.modal-delete-confirm h3 {
  margin: 0 0 0.75rem;
  font-size: 1.125rem;
  font-weight: 600;
  color: #1f2937;
}

.delete-dist-name {
  margin: 0;
  font-size: 0.9375rem;
  font-weight: 500;
  color: #374151;
}

.delete-dist-code {
  margin: 0.25rem 0 1rem;
  font-size: 0.8125rem;
  color: #6b7280;
  font-family: 'SF Mono', monospace;
}

.delete-warning {
  display: flex;
  align-items: flex-start;
  gap: 0.5rem;
  padding: 0.875rem 1rem;
  background: #fef3c7;
  border-radius: 8px;
  margin-bottom: 1.5rem;
  text-align: left;
}

.delete-warning i {
  color: #f59e0b;
  font-size: 1.125rem;
  flex-shrink: 0;
}

.delete-warning span {
  font-size: 0.8125rem;
  color: #92400e;
  line-height: 1.5;
}

/* 提交记录警告样式 */
.submissions-warning {
  display: flex;
  align-items: flex-start;
  gap: 0.75rem;
  padding: 1rem 1.25rem;
  background: linear-gradient(135deg, #fef2f2 0%, #fee2e2 100%);
  border: 2px solid #fca5a5;
  border-radius: 10px;
  margin: 1rem 0 1.5rem;
  text-align: left;
}

.submissions-warning i {
  color: #dc2626;
  font-size: 1.5rem;
  flex-shrink: 0;
  margin-top: 0.125rem;
}

.warning-content {
  flex: 1;
}

.warning-title {
  margin: 0 0 0.5rem;
  font-size: 0.9375rem;
  font-weight: 600;
  color: #991b1b;
}

.warning-title strong {
  color: #dc2626;
  font-size: 1.125rem;
}

.warning-desc {
  margin: 0;
  font-size: 0.8125rem;
  color: #7f1d1d;
  line-height: 1.5;
}

.warning-desc strong {
  font-weight: 600;
  text-decoration: underline;
}

.delete-confirm-actions {
  display: flex;
  justify-content: center;
  gap: 0.75rem;
}

.btn-danger,
.btn-danger-strong {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.625rem 1.25rem;
  background: linear-gradient(135deg, #dc2626 0%, #ef4444 100%);
  color: white;
  border: none;
  border-radius: 10px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-danger:hover:not(:disabled),
.btn-danger-strong:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(220, 38, 38, 0.3);
}

.btn-danger:disabled,
.btn-danger-strong:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.btn-danger-strong {
  background: linear-gradient(135deg, #991b1b 0%, #dc2626 100%);
  font-weight: 600;
  animation: pulse-warning 2s ease-in-out infinite;
}

@keyframes pulse-warning {
  0%, 100% {
    box-shadow: 0 0 0 0 rgba(220, 38, 38, 0.7);
  }
  50% {
    box-shadow: 0 0 0 8px rgba(220, 38, 38, 0);
  }
}

/* 响应式 */
@media (max-width: 640px) {
  .modal-panel {
    margin: 16px;
    max-height: calc(100vh - 32px);
  }
  
  .dist-body {
    flex-direction: column;
  }
  
  .qr-section {
    align-self: center;
  }
  
  .modal-footer {
    flex-direction: column;
    gap: 16px;
  }
}
</style>

