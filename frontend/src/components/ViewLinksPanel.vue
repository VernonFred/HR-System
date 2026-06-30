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
import { getQuestionnaireCopy } from '../utils/questionnaireCopy'

// ===== Props =====
const props = defineProps<{
  questionnaire: Questionnaire | null
}>()

// ===== Emits =====
const emit = defineEmits<{
  (e: 'close'): void
  (e: 'create-new'): void
  (e: 'edit', assessment: Assessment): void
  (e: 'clone', assessment: Assessment): void
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
const deleteError = ref('')  // ⭐ V50: 删除错误提示

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
  createdAt: string
  createdAtTime: number
  isActive: boolean
  isExpired: boolean
  assessment: Assessment
}

// ===== 计算属性 =====
const activeCount = computed(() => distributions.value.filter(d => d.isActive).length)
const expiredCount = computed(() => distributions.value.filter(d => d.isExpired).length)
const copy = computed(() => getQuestionnaireCopy(props.questionnaire))

// ===== 方法 =====
const close = () => emit('close')

const createNew = () => {
  emit('create-new')
}

const formatDateTime = (value?: string) => {
  if (!value) return '未知'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return '未知'
  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  })
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
        createdAt: formatDateTime(a.created_at),
        createdAtTime: a.created_at ? new Date(a.created_at).getTime() : 0,
        isActive,
        isExpired,
        assessment: a,
      }
    }))

    // 按生成时间倒序排列，便于识别最新链接
    distributions.value.sort((a, b) => b.createdAtTime - a.createdAtTime || b.id - a.id)

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

const editDistribution = (dist: DistributionInfo) => {
  emit('edit', dist.assessment)
}

const cloneDistribution = (dist: DistributionInfo) => {
  emit('clone', dist.assessment)
}

const downloadQRCode = (dataUrl: string, name: string) => {
  const link = document.createElement('a')
  link.download = `${name}_${copy.value.qrAlt}.png`
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

  deleteError.value = ''  // 清除之前的错误

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
      // ⭐ V50: 使用自定义错误提示代替 alert
      deleteError.value = error?.message || error?.detail || '删除失败，请重试'
      // 3秒后清除错误
      setTimeout(() => { deleteError.value = '' }, 3000)
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
          <span>请点击"分发"按钮创建新的{{ copy.linkLabel }}</span>
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
                <div class="meta-item">
                  <i class="ri-calendar-line"></i>
                  <span>有效期：{{ dist.validFrom }} ~ {{ dist.validUntil }}</span>
                </div>
                <div class="meta-item">
                  <i class="ri-time-line"></i>
                  <span>生成时间：{{ dist.createdAt }}</span>
                </div>
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
                <button class="dist-action-btn edit" @click="editDistribution(dist)" title="编辑配置">
                  <i class="ri-settings-3-line"></i>
                  编辑
                </button>
                <button class="dist-action-btn clone" @click="cloneDistribution(dist)" title="复制配置新建链接">
                  <i class="ri-file-copy-line"></i>
                  复制配置新建
                </button>
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
          <span>链接读取当前问卷内容；修改问卷后原链接自动使用新内容。长期/短期共存时可复制配置新建链接。</span>
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

        <!-- ⭐ V50: 错误提示 -->
        <div v-if="deleteError" class="delete-error-msg">
          <i class="ri-error-warning-line"></i>
          {{ deleteError }}
        </div>

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
@import './styles/view-links-panel.css';
</style>
