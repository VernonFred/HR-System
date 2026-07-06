<script setup lang="ts">
import { computed } from 'vue'
import type { QuestionnaireQuestionStats, Submission } from '../../api/assessments'

type StatsExportFormat = 'pdf' | 'png' | 'excel'
type SubmissionExportFormat = 'csv' | 'excel'

const props = defineProps<{
  showStatsExportModal: boolean
  statsExportFormat: StatsExportFormat
  statsExportLoading: boolean
  questionStats: QuestionnaireQuestionStats | null
  showExportModal: boolean
  exportFormat: SubmissionExportFormat
  exportLoading: boolean
  submissions: Submission[]
  showExportSuccessToast: boolean
  showStatsExportToast: boolean
  statsExportToastType: 'success' | 'error'
  statsExportToastMessage: string
  showBatchDeleteModal: boolean
  selectedSubmissions: Set<number>
  formatDate: (dateStr: string | null | undefined) => string
}>()

const emit = defineEmits<{
  'update:statsExportFormat': [value: StatsExportFormat]
  'update:exportFormat': [value: SubmissionExportFormat]
  'close-stats-export-modal': []
  'execute-stats-export': []
  'close-export-modal': []
  'execute-export': []
  'close-batch-delete-modal': []
  'confirm-batch-delete': []
}>()

const selectedPreview = computed(() =>
  props.submissions.filter(sub => props.selectedSubmissions.has(sub.id)).slice(0, 5)
)
</script>

<template>
  <Teleport to="body">
    <Transition name="modal">
      <div v-if="showStatsExportModal" class="modal-overlay" @click="emit('close-stats-export-modal')">
        <div class="modal-dialog export-modal stats-export-modal" @click.stop>
          <div class="modal-header">
            <h3><i class="ri-download-cloud-2-line"></i> 导出统计报告</h3>
            <button class="btn-close-modal" :disabled="statsExportLoading" @click="emit('close-stats-export-modal')">
              <i class="ri-close-line"></i>
            </button>
          </div>
          <div class="modal-body export-body">
            <p class="export-info">
              <i class="ri-bar-chart-grouped-line"></i>
              将导出 <strong>{{ questionStats?.questions?.length || 0 }}</strong> 道题目的完整统计报告
            </p>
            <div class="export-format-group">
              <label class="format-label">选择导出格式：</label>
              <div class="format-options stats-format-options">
                <label class="format-option recommended" :class="{ active: statsExportFormat === 'pdf' }">
                  <input type="radio" :checked="statsExportFormat === 'pdf'" @change="emit('update:statsExportFormat', 'pdf')" />
                  <i class="ri-file-pdf-line"></i>
                  <span>PDF 报告</span>
                  <small>推荐，自动分页</small>
                </label>
                <label class="format-option" :class="{ active: statsExportFormat === 'png' }">
                  <input type="radio" :checked="statsExportFormat === 'png'" @change="emit('update:statsExportFormat', 'png')" />
                  <i class="ri-image-2-line"></i>
                  <span>PNG 图片</span>
                  <small>长内容自动拆图</small>
                </label>
                <label class="format-option" :class="{ active: statsExportFormat === 'excel' }">
                  <input type="radio" :checked="statsExportFormat === 'excel'" @change="emit('update:statsExportFormat', 'excel')" />
                  <i class="ri-file-excel-2-line"></i>
                  <span>Excel 表格</span>
                  <small>用于二次分析</small>
                </label>
              </div>
            </div>
          </div>
          <div class="modal-footer">
            <button class="btn-cancel" :disabled="statsExportLoading" @click="emit('close-stats-export-modal')">取消</button>
            <button class="btn-primary" :disabled="statsExportLoading" @click="emit('execute-stats-export')">
              <i v-if="statsExportLoading" class="ri-time-line"></i>
              <i v-else class="ri-download-line"></i>
              {{ statsExportLoading ? '正在生成...' : '确认导出' }}
            </button>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>

  <Teleport to="body">
    <Transition name="modal">
      <div v-if="showExportModal" class="modal-overlay" @click="emit('close-export-modal')">
        <div class="modal-dialog export-modal" @click.stop>
          <div class="modal-header">
            <h3><i class="ri-download-line"></i> 导出数据</h3>
            <button class="btn-close-modal" @click="emit('close-export-modal')">
              <i class="ri-close-line"></i>
            </button>
          </div>
          <div class="modal-body export-body">
            <p class="export-info">
              <i class="ri-file-list-3-line"></i>
              将导出 <strong>{{ submissions.length }}</strong> 条提交记录
            </p>
            <div class="export-format-group">
              <label class="format-label">选择导出格式：</label>
              <div class="format-options">
                <label class="format-option" :class="{ active: exportFormat === 'csv' }">
                  <input type="radio" :checked="exportFormat === 'csv'" @change="emit('update:exportFormat', 'csv')" />
                  <i class="ri-file-text-line"></i>
                  <span>CSV 文件</span>
                  <small>通用格式，可用Excel打开</small>
                </label>
                <label class="format-option" :class="{ active: exportFormat === 'excel' }">
                  <input type="radio" :checked="exportFormat === 'excel'" @change="emit('update:exportFormat', 'excel')" />
                  <i class="ri-file-excel-2-line"></i>
                  <span>Excel 文件</span>
                  <small>含提交明细、答题明细、选项人员明细</small>
                </label>
              </div>
            </div>
          </div>
          <div class="modal-footer">
            <button class="btn-cancel" @click="emit('close-export-modal')">取消</button>
            <button class="btn-primary" :disabled="exportLoading" @click="emit('execute-export')">
              <i v-if="exportLoading" class="ri-loader-4-line spinning"></i>
              <i v-else class="ri-download-line"></i>
              {{ exportLoading ? '导出中...' : '确认导出' }}
            </button>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>

  <Teleport to="body">
    <Transition name="toast">
      <div v-if="showExportSuccessToast" class="toast-success">
        <i class="ri-checkbox-circle-fill"></i>
        <span>{{ submissions.length > 0 ? '导出成功！文件已下载' : '暂无数据可导出' }}</span>
      </div>
    </Transition>
  </Teleport>

  <Teleport to="body">
    <Transition name="toast">
      <div v-if="showStatsExportToast" class="toast-success" :class="statsExportToastType">
        <i :class="statsExportToastType === 'success' ? 'ri-checkbox-circle-fill' : 'ri-error-warning-fill'"></i>
        <span>{{ statsExportToastMessage }}</span>
      </div>
    </Transition>
  </Teleport>

  <Teleport to="body">
    <Transition name="modal">
      <div v-if="showBatchDeleteModal" class="modal-overlay" @click="emit('close-batch-delete-modal')">
        <div class="modal-dialog confirm-modal batch-delete-modal" @click.stop>
          <div class="modal-header">
            <h3><i class="ri-delete-bin-line"></i> 批量删除确认</h3>
          </div>
          <div class="modal-body confirm-body">
            <p>确定要删除选中的 <strong>{{ selectedSubmissions.size }}</strong> 条提交记录吗？</p>
            <div class="batch-delete-preview">
              <div v-for="sub in selectedPreview" :key="sub.id" class="preview-item">
                <span class="preview-name">{{ sub.candidate_name }}</span>
                <span class="preview-time">{{ formatDate(sub.submitted_at) }}</span>
              </div>
              <div v-if="selectedSubmissions.size > 5" class="preview-more">
                ...还有 {{ selectedSubmissions.size - 5 }} 条记录
              </div>
            </div>
            <p class="confirm-warning">
              <i class="ri-error-warning-line"></i>
              此操作不可恢复，请谨慎操作！
            </p>
          </div>
          <div class="modal-footer">
            <button class="btn-cancel" @click="emit('close-batch-delete-modal')">取消</button>
            <button class="btn-danger" @click="emit('confirm-batch-delete')">
              <i class="ri-delete-bin-line"></i>
              确认删除 ({{ selectedSubmissions.size }})
            </button>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.modal-overlay {
  position: fixed;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(0, 0, 0, 0.5);
  z-index: 3000;
}

.modal-dialog {
  width: 90%;
  max-width: 480px;
  overflow: hidden;
  border-radius: 16px;
  background: #ffffff;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.2);
}

.stats-export-modal {
  max-width: 640px;
}

.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 20px 24px;
  background: linear-gradient(135deg, #7c3aed 0%, #6d28d9 100%);
  color: #ffffff;
}

.modal-header h3 {
  display: flex;
  align-items: center;
  gap: 10px;
  margin: 0;
  font-size: 18px;
  font-weight: 600;
}

.btn-close-modal {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border: 0;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.2);
  color: #ffffff;
  cursor: pointer;
  font-size: 18px;
}

.modal-body {
  padding: 24px;
}

.export-info {
  display: flex;
  align-items: center;
  gap: 10px;
  margin: 0 0 20px;
  padding: 16px;
  border-radius: 10px;
  background: #f8fafc;
  color: #475569;
  font-size: 14px;
}

.export-info i,
.export-info strong {
  color: #7c3aed;
}

.format-label {
  display: block;
  margin-bottom: 12px;
  color: #334155;
  font-size: 14px;
  font-weight: 500;
}

.format-options {
  display: flex;
  gap: 12px;
}

.stats-format-options {
  align-items: stretch;
}

.format-option {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  padding: 16px;
  border: 2px solid #e2e8f0;
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.2s;
}

.format-option.recommended {
  position: relative;
}

.format-option.recommended::after {
  content: "推荐";
  position: absolute;
  top: 8px;
  right: 8px;
  padding: 2px 7px;
  border-radius: 999px;
  background: #dcfce7;
  color: #047857;
  font-size: 11px;
  font-weight: 700;
}

.format-option:hover,
.format-option.active {
  border-color: #7c3aed;
  background: #faf5ff;
}

.format-option input {
  display: none;
}

.format-option i {
  color: #7c3aed;
  font-size: 28px;
}

.format-option span {
  color: #334155;
  font-size: 14px;
  font-weight: 500;
}

.format-option small {
  color: #64748b;
  font-size: 12px;
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  padding: 16px 24px 24px;
}

.btn-cancel,
.btn-primary {
  border: 0;
  border-radius: 10px;
  cursor: pointer;
  font-size: 14px;
  font-weight: 600;
  padding: 10px 18px;
}

.btn-cancel {
  background: #f1f5f9;
  color: #475569;
}

.btn-primary {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  background: #7c3aed;
  color: #ffffff;
}

.btn-primary:disabled,
.btn-cancel:disabled {
  cursor: not-allowed;
  opacity: 0.65;
}
</style>
