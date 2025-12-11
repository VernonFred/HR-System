<script setup lang="ts">
/**
 * 提交记录标签页组件
 * 
 * 功能：
 * 1. 显示提交记录列表（列表视图/分组视图）
 * 2. 筛选和搜索
 * 3. 导出数据
 * 4. 删除记录
 */
import { ref, computed, defineAsyncComponent } from 'vue'
import type { Submission, Questionnaire } from '../api/assessments'

// 异步加载提交详情弹窗
const SubmissionDetailModal = defineAsyncComponent(() => import('./SubmissionDetailModal.vue'))

// Props
const props = defineProps<{
  submissions: Submission[]
  questionnaires: Questionnaire[]
  loading?: boolean
}>()

// Emits
const emit = defineEmits<{
  (e: 'delete', submission: Submission): void
  (e: 'delete-batch', submissions: Submission[]): void  // ⭐ V44: 批量删除
  (e: 'export-pdf', submission: Submission): void
  (e: 'refresh'): void
}>()

// ===== 筛选状态 =====
const searchQuery = ref('')
const filterQuestionnaire = ref('all')
const filterStatus = ref('all')
const groupByCandidate = ref(false)

// V45: 年份/月份筛选
const filterYear = ref<number | null>(null)
const filterMonth = ref<number | null>(null)

// 生成年份选项（从2024年到当前年份）
const yearOptions = computed(() => {
  const currentYear = new Date().getFullYear()
  const years: number[] = []
  for (let y = currentYear; y >= 2024; y--) {
    years.push(y)
  }
  return years
})

// 月份选项
const monthOptions = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]
const expandedCandidates = ref<Set<string>>(new Set())

// ===== 查看详情弹窗 =====
const showSubmissionDetailModal = ref(false)
const selectedSubmission = ref<Submission | null>(null)

// ===== 删除确认弹窗 =====
const showDeleteConfirmModal = ref(false)
const deleteTargetSubmission = ref<Submission | null>(null)

// ⭐ V44: 批量删除功能
const selectedSubmissions = ref<Set<number>>(new Set())  // 选中的提交记录ID
const showBatchDeleteModal = ref(false)  // 批量删除确认弹窗
const isSelectMode = ref(false)  // 是否处于选择模式

// 切换选择模式
const toggleSelectMode = () => {
  isSelectMode.value = !isSelectMode.value
  if (!isSelectMode.value) {
    selectedSubmissions.value.clear()
  }
}

// 切换单条记录选择
const toggleSubmissionSelect = (id: number) => {
  if (selectedSubmissions.value.has(id)) {
    selectedSubmissions.value.delete(id)
  } else {
    selectedSubmissions.value.add(id)
  }
}

// 全选/取消全选
const toggleSelectAll = () => {
  if (selectedSubmissions.value.size === filteredSubmissions.value.length) {
    selectedSubmissions.value.clear()
  } else {
    selectedSubmissions.value = new Set(filteredSubmissions.value.map(s => s.id))
  }
}

// 打开批量删除确认弹窗
const openBatchDeleteModal = () => {
  if (selectedSubmissions.value.size === 0) return
  showBatchDeleteModal.value = true
}

// 确认批量删除
const confirmBatchDelete = () => {
  const toDelete = filteredSubmissions.value.filter(s => selectedSubmissions.value.has(s.id))
  emit('delete-batch', toDelete)
  showBatchDeleteModal.value = false
  selectedSubmissions.value.clear()
  isSelectMode.value = false
}

// ===== 导出弹窗 =====
const showExportModal = ref(false)
const exportFormat = ref<'csv' | 'excel'>('csv')
const exportLoading = ref(false)
const showExportSuccessToast = ref(false)

// ===== 过滤后的提交记录 =====
const filteredSubmissions = computed(() => {
  let result = [...props.submissions]
  
  // V45: 年份筛选
  if (filterYear.value) {
    result = result.filter(s => {
      const dateStr = s.submitted_at || s.started_at
      if (!dateStr) return false
      const date = new Date(dateStr)
      return date.getFullYear() === filterYear.value
    })
  }
  
  // V45: 月份筛选
  if (filterMonth.value) {
    result = result.filter(s => {
      const dateStr = s.submitted_at || s.started_at
      if (!dateStr) return false
      const date = new Date(dateStr)
      return (date.getMonth() + 1) === filterMonth.value
    })
  }
  
  // 搜索过滤
  if (searchQuery.value) {
    const query = searchQuery.value.toLowerCase()
    result = result.filter(s => 
      (s.candidate_name || '').toLowerCase().includes(query) ||
      (s.candidate_phone || '').includes(query) ||
      (s.code || '').toLowerCase().includes(query)
    )
  }
  
  // 问卷类型过滤
  if (filterQuestionnaire.value !== 'all') {
    result = result.filter(s => s.questionnaire_name === filterQuestionnaire.value)
  }
  
  // 状态过滤
  if (filterStatus.value !== 'all') {
    result = result.filter(s => s.status === filterStatus.value)
  }
  
  return result
})

// ===== 按候选人分组的提交记录 =====
interface GroupedCandidate {
  phone: string
  name: string
  totalSubmissions: number
  completedCount: number
  latestSubmission: Submission | null
  submissions: Submission[]
}

const groupedSubmissions = computed<GroupedCandidate[]>(() => {
  const groups = new Map<string, GroupedCandidate>()
  
  for (const sub of filteredSubmissions.value) {
    const key = sub.candidate_phone || sub.candidate_name || 'unknown'
    
    if (!groups.has(key)) {
      groups.set(key, {
        phone: sub.candidate_phone || '',
        name: sub.candidate_name || '未知',
        totalSubmissions: 0,
        completedCount: 0,
        latestSubmission: null,
        submissions: []
      })
    }
    
    const group = groups.get(key)!
    group.totalSubmissions++
    if (sub.status === 'completed') {
      group.completedCount++
    }
    group.submissions.push(sub)
    
    // 更新最新提交
    if (!group.latestSubmission || 
        (sub.submitted_at && group.latestSubmission.submitted_at && 
         new Date(sub.submitted_at) > new Date(group.latestSubmission.submitted_at))) {
      group.latestSubmission = sub
    }
  }
  
  // 按最新提交时间排序
  return Array.from(groups.values()).sort((a, b) => {
    const timeA = a.latestSubmission?.submitted_at ? new Date(a.latestSubmission.submitted_at).getTime() : 0
    const timeB = b.latestSubmission?.submitted_at ? new Date(b.latestSubmission.submitted_at).getTime() : 0
    return timeB - timeA
  })
})

// ===== 辅助函数 =====
const formatDate = (dateStr: string | null | undefined) => {
  if (!dateStr) return '--'
  const d = new Date(dateStr)
  return d.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  })
}

const getStatusLabel = (status: string) => {
  const labels: Record<string, string> = {
    'completed': '已完成',
    'in_progress': '进行中',
    'pending': '待处理'
  }
  return labels[status] || status
}

// ⭐ 获取人格类型（从result_details中提取）
const getPersonalityType = (submission: Submission) => {
  if (submission.status !== 'completed') return '--'
  
  const details = submission.result_details
  if (!details) return '--'
  
  // MBTI类型
  if (details.mbti_type) return details.mbti_type
  // DISC类型
  if (details.disc_type) return details.disc_type
  // EPQ类型
  if (details.personality_trait) return details.personality_trait
  
  return '--'
}

// ⭐ 获取人格类型的样式类
const getPersonalityTypeClass = (submission: Submission) => {
  const type = getPersonalityType(submission)
  if (type === '--') return 'type-pending'
  
  const details = submission.result_details
  if (details?.mbti_type) return 'type-mbti'
  if (details?.disc_type) return 'type-disc'
  if (details?.personality_trait) return 'type-epq'
  
  return 'type-default'
}

// ===== 事件处理 =====
const openSubmissionDetail = (submission: Submission) => {
  selectedSubmission.value = submission
  showSubmissionDetailModal.value = true
}

const handleDeleteSubmission = (submission: Submission) => {
  deleteTargetSubmission.value = submission
  showDeleteConfirmModal.value = true
}

const confirmDeleteSubmission = () => {
  if (deleteTargetSubmission.value) {
    emit('delete', deleteTargetSubmission.value)
  }
  showDeleteConfirmModal.value = false
  deleteTargetSubmission.value = null
}

const handleExportPDF = (submission: Submission) => {
  emit('export-pdf', submission)
}

// 切换候选人展开状态
const toggleCandidateExpand = (key: string) => {
  if (expandedCandidates.value.has(key)) {
    expandedCandidates.value.delete(key)
  } else {
    expandedCandidates.value.add(key)
  }
}

// 全部展开/收起
const toggleAllCandidates = () => {
  if (expandedCandidates.value.size === groupedSubmissions.value.length) {
    expandedCandidates.value.clear()
  } else {
    expandedCandidates.value = new Set(
      groupedSubmissions.value.map(g => g.phone || g.name)
    )
  }
}

// 打开导出弹窗
const openExportModal = () => {
  if (filteredSubmissions.value.length === 0) {
    // 没有数据时显示提示
    showExportSuccessToast.value = true
    setTimeout(() => { showExportSuccessToast.value = false }, 2000)
    return
  }
  showExportModal.value = true
}

// 关闭导出弹窗
const closeExportModal = () => {
  showExportModal.value = false
}

// 执行导出
const executeExport = async () => {
  exportLoading.value = true
  
  try {
    const data = filteredSubmissions.value.map(r => ({
      '编号': r.code,
      '姓名': r.candidate_name,
      '联系方式': r.candidate_phone,
      '问卷': r.questionnaire_name,
      '类型': getPersonalityType(r),
      '状态': getStatusLabel(r.status),
      '提交时间': formatDate(r.submitted_at)
    }))
    
    const headers = Object.keys(data[0] || {})
    const dateStr = new Date().toISOString().slice(0, 10)
    
    if (exportFormat.value === 'csv') {
      // CSV导出
      const csvContent = [
        headers.join(','),
        ...data.map(row => headers.map(h => `"${(row as any)[h] || ''}"`).join(','))
      ].join('\n')
      
      const blob = new Blob(['\uFEFF' + csvContent], { type: 'text/csv;charset=utf-8;' })
      const link = document.createElement('a')
      link.href = URL.createObjectURL(blob)
      link.download = `提交记录_${dateStr}.csv`
      link.click()
    } else {
      // Excel导出 (使用HTML表格格式，可被Excel打开)
      let htmlContent = `
        <html xmlns:o="urn:schemas-microsoft-com:office:office" xmlns:x="urn:schemas-microsoft-com:office:excel">
        <head><meta charset="UTF-8"></head>
        <body>
          <table border="1">
            <tr>${headers.map(h => `<th style="background:#f0f0f0;font-weight:bold;">${h}</th>`).join('')}</tr>
            ${data.map(row => `<tr>${headers.map(h => `<td>${(row as any)[h] || ''}</td>`).join('')}</tr>`).join('')}
          </table>
        </body>
        </html>
      `
      const blob = new Blob([htmlContent], { type: 'application/vnd.ms-excel;charset=utf-8;' })
      const link = document.createElement('a')
      link.href = URL.createObjectURL(blob)
      link.download = `提交记录_${dateStr}.xls`
      link.click()
    }
    
    // 关闭弹窗并显示成功提示
    showExportModal.value = false
    showExportSuccessToast.value = true
    setTimeout(() => { showExportSuccessToast.value = false }, 3000)
    
  } catch (error) {
    console.error('导出失败:', error)
  } finally {
    exportLoading.value = false
  }
}
</script>

<template>
  <div class="records-tab">
    <!-- V45: 现代化筛选工具栏 - 飞书/Notion风格 -->
    <div class="toolbar">
      <!-- 搜索框 -->
      <div class="toolbar-search">
          <i class="ri-search-line"></i>
          <input
            type="text"
            v-model="searchQuery"
            placeholder="搜索候选人姓名或编号..."
          />
        </div>
      
      <!-- 筛选器组 -->
      <div class="toolbar-filters">
        <div class="filter-chip" :class="{ active: filterYear !== null }">
          <i class="ri-calendar-line"></i>
          <select v-model="filterYear">
            <option :value="null">全部年份</option>
            <option v-for="year in yearOptions" :key="year" :value="year">{{ year }}年</option>
          </select>
        </div>
        <div class="filter-chip" :class="{ active: filterMonth !== null }">
          <i class="ri-calendar-event-line"></i>
          <select v-model="filterMonth">
            <option :value="null">全部月份</option>
            <option v-for="month in monthOptions" :key="month" :value="month">{{ month }}月</option>
          </select>
        </div>
        <div class="filter-chip" :class="{ active: filterQuestionnaire !== 'all' }">
          <i class="ri-file-list-3-line"></i>
          <select v-model="filterQuestionnaire">
            <option value="all">全部问卷</option>
            <option v-for="q in questionnaires" :key="q.id" :value="q.name">{{ q.name }}</option>
          </select>
        </div>
        <div class="filter-chip" :class="{ active: filterStatus !== 'all' }">
          <i class="ri-checkbox-circle-line"></i>
          <select v-model="filterStatus">
            <option value="all">全部</option>
            <option value="completed">已完成</option>
            <option value="in_progress">进行中</option>
          </select>
        </div>
      </div>
      
        <!-- 视图切换 -->
      <div class="toolbar-view">
          <button 
          :class="['view-btn', { active: !groupByCandidate }]" 
            @click="groupByCandidate = false"
            title="列表视图"
          >
            <i class="ri-list-unordered"></i>
          </button>
          <button 
          :class="['view-btn', { active: groupByCandidate }]" 
            @click="groupByCandidate = true"
          title="分组视图"
          >
          <i class="ri-layout-grid-line"></i>
          </button>
        </div>
      
      <!-- 操作按钮 -->
      <div class="toolbar-actions">
        <button class="action-btn primary" @click="openExportModal">
          <i class="ri-download-line"></i>
          导出
        </button>
        <button 
          v-if="!groupByCandidate"
          :class="['action-btn', { danger: isSelectMode }]" 
          @click="toggleSelectMode"
        >
          <i :class="isSelectMode ? 'ri-close-line' : 'ri-checkbox-multiple-line'"></i>
          {{ isSelectMode ? '取消' : '批量删除' }}
        </button>
      </div>
    </div>
    
    <!-- ⭐ V44: 批量操作栏 - 列表模式显示 -->
    <div v-if="isSelectMode && !groupByCandidate" class="batch-action-bar">
      <div class="batch-left">
        <label class="select-all-checkbox">
          <input 
            type="checkbox" 
            :checked="selectedSubmissions.size === filteredSubmissions.length && filteredSubmissions.length > 0"
            :indeterminate="selectedSubmissions.size > 0 && selectedSubmissions.size < filteredSubmissions.length"
            @change="toggleSelectAll"
          />
          <span>全选</span>
        </label>
        <span class="selected-count">已选择 {{ selectedSubmissions.size }} 条</span>
      </div>
      <div class="batch-right">
        <button 
          class="btn-batch-delete" 
          :disabled="selectedSubmissions.size === 0"
          @click="openBatchDeleteModal"
        >
          <i class="ri-delete-bin-line"></i>
          删除选中 ({{ selectedSubmissions.size }})
        </button>
      </div>
    </div>

    <!-- 统计信息 -->
    <div class="records-summary">
      <div class="summary-item">
        <span class="summary-value">{{ filteredSubmissions.length }}</span>
        <span class="summary-label">条记录</span>
      </div>
      <div class="summary-item" v-if="groupByCandidate">
        <i class="ri-user-line"></i>
        <span class="summary-value">{{ groupedSubmissions.length }}</span>
        <span class="summary-label">位候选人</span>
      </div>
      <div class="summary-item completed">
        <i class="ri-checkbox-circle-fill"></i>
        <span class="summary-value">{{ filteredSubmissions.filter(s => s.status === 'completed').length }}</span>
        <span class="summary-label">已完成</span>
      </div>
      <div class="summary-item pending">
        <i class="ri-time-fill"></i>
        <span class="summary-value">{{ filteredSubmissions.filter(s => s.status === 'in_progress').length }}</span>
        <span class="summary-label">进行中</span>
      </div>
    </div>

    <!-- 列表视图 -->
    <div v-if="!groupByCandidate" class="table-wrapper">
      <table class="records-table">
        <thead>
          <tr>
            <th v-if="isSelectMode" class="cell-checkbox">
              <input 
                type="checkbox" 
                :checked="selectedSubmissions.size === filteredSubmissions.length && filteredSubmissions.length > 0"
                @change="toggleSelectAll"
              />
            </th>
            <th>编号</th>
            <th>姓名</th>
            <th>联系方式</th>
            <th>问卷</th>
            <th>类型</th>
            <th>状态</th>
            <th>提交时间</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="r in filteredSubmissions" :key="r.id" class="record-row" :class="{ selected: selectedSubmissions.has(r.id) }">
            <td v-if="isSelectMode" class="cell-checkbox">
              <input 
                type="checkbox" 
                :checked="selectedSubmissions.has(r.id)"
                @change="toggleSubmissionSelect(r.id)"
              />
            </td>
            <td class="cell-code">{{ r.code }}</td>
            <td class="cell-name">
              <div class="candidate-info">
                <span class="candidate-avatar">{{ (r.candidate_name || 'U')[0].toUpperCase() }}</span>
                <span>{{ r.candidate_name }}</span>
              </div>
            </td>
            <td class="cell-phone">{{ r.candidate_phone }}</td>
            <td class="cell-questionnaire">{{ r.questionnaire_name || "N/A" }}</td>
            <td class="cell-type">
              <span class="type-badge" :class="getPersonalityTypeClass(r)">
                {{ getPersonalityType(r) }}
              </span>
            </td>
            <td class="cell-status">
              <span :class="['status-pill', r.status === 'completed' ? 'status-completed' : 'status-progress']">
                <i :class="r.status === 'completed' ? 'ri-checkbox-circle-fill' : 'ri-time-fill'"></i>
                {{ getStatusLabel(r.status) }}
              </span>
            </td>
            <td class="cell-time">{{ formatDate(r.submitted_at) }}</td>
            <td class="cell-actions">
              <button class="btn-action-delete" title="删除记录" @click="handleDeleteSubmission(r)">
                <i class="ri-delete-bin-line"></i>
              </button>
            </td>
          </tr>
          <tr v-if="filteredSubmissions.length === 0">
            <td :colspan="isSelectMode ? 9 : 8" class="empty-cell">
              <div class="empty-state-inline">
                <i class="ri-inbox-line"></i>
                <span>暂无提交记录</span>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- 分组视图 -->
    <div v-else class="grouped-view">
      <!-- V45: 分组模式控制栏 -->
      <div class="grouped-controls">
        <button class="btn-toggle-all" @click="toggleAllCandidates">
          <i :class="expandedCandidates.size === groupedSubmissions.length ? 'ri-contract-up-down-line' : 'ri-expand-up-down-line'"></i>
          {{ expandedCandidates.size === groupedSubmissions.length ? '全部收起' : '全部展开' }}
        </button>
        <button class="btn-export" @click="openExportModal">
          <i class="ri-download-line"></i>
          导出数据
        </button>
        <button 
          :class="['btn-batch-select', { active: isSelectMode }]" 
          @click="toggleSelectMode"
        >
          <i :class="isSelectMode ? 'ri-close-line' : 'ri-checkbox-multiple-line'"></i>
          {{ isSelectMode ? '取消选择' : '批量删除' }}
        </button>
      </div>
      
      <!-- V45: 批量操作栏 - 选择模式下显示 -->
      <div v-if="isSelectMode" class="batch-action-bar">
        <div class="batch-left">
          <label class="select-all-checkbox">
            <input 
              type="checkbox" 
              :checked="selectedSubmissions.size === filteredSubmissions.length && filteredSubmissions.length > 0"
              @change="toggleSelectAll"
            />
            <span>全选</span>
          </label>
          <span class="selected-count">已选择 {{ selectedSubmissions.size }} 条</span>
        </div>
        <div class="batch-right">
          <button 
            class="btn-batch-delete" 
            :disabled="selectedSubmissions.size === 0"
            @click="openBatchDeleteModal"
          >
            <i class="ri-delete-bin-line"></i>
            删除选中 ({{ selectedSubmissions.size }})
          </button>
        </div>
      </div>
      
      <!-- 候选人分组卡片 -->
      <div class="candidate-groups">
        <div 
          v-for="group in groupedSubmissions" 
          :key="group.phone || group.name"
          class="candidate-group-card"
          :class="{ expanded: expandedCandidates.has(group.phone || group.name) }"
        >
          <!-- 分组头部 -->
          <div 
            class="group-header"
            @click="toggleCandidateExpand(group.phone || group.name)"
          >
            <div class="group-main">
              <span class="group-avatar">{{ (group.name || 'U')[0].toUpperCase() }}</span>
              <div class="group-info">
                <div class="group-name-row">
                <span class="group-name">{{ group.name || '未知' }}</span>
                <span class="group-phone">{{ group.phone }}</span>
            </div>
            <div class="group-stats">
              <span class="stat-badge total">
                <i class="ri-file-list-3-line"></i>
                {{ group.totalSubmissions }}次测评
              </span>
              <span class="stat-badge completed" v-if="group.completedCount > 0">
                <i class="ri-checkbox-circle-fill"></i>
                {{ group.completedCount }}已完成
              </span>
                  <span class="stat-badge latest" v-if="group.latestSubmission?.submitted_at">
                <i class="ri-time-line"></i>
                    {{ formatDate(group.latestSubmission.submitted_at).split(' ')[0] }}
              </span>
                </div>
              </div>
            </div>
            <i :class="['expand-icon', expandedCandidates.has(group.phone || group.name) ? 'ri-arrow-up-s-line' : 'ri-arrow-down-s-line']"></i>
          </div>
          
          <!-- 展开的测评列表 -->
          <div v-if="expandedCandidates.has(group.phone || group.name)" class="group-submissions">
            <div 
              v-for="(sub, idx) in group.submissions" 
              :key="sub.id"
              class="submission-item"
              :class="{ selected: selectedSubmissions.has(sub.id) }"
            >
              <!-- V45: 分组模式下也显示复选框 -->
              <input 
                v-if="isSelectMode"
                type="checkbox" 
                class="submission-checkbox"
                :checked="selectedSubmissions.has(sub.id)"
                @click.stop
                @change="toggleSubmissionSelect(sub.id)"
              />
              <div class="submission-order">#{{ idx + 1 }}</div>
              <div class="submission-info">
                <span class="submission-questionnaire">{{ sub.questionnaire_name || 'N/A' }}</span>
              </div>
              <div class="submission-result">
                <span class="type-badge" :class="getPersonalityTypeClass(sub)">
                  {{ getPersonalityType(sub) }}
                </span>
                <span :class="['status-mini', sub.status === 'completed' ? 'completed' : 'progress']">
                  {{ sub.status === 'completed' ? '已完成' : '进行中' }}
                </span>
                <span class="submission-time">
                  {{ sub.submitted_at ? formatDate(sub.submitted_at) : '--' }}
                </span>
              </div>
              <div class="submission-actions">
                <button class="btn-mini delete" title="删除" @click.stop="handleDeleteSubmission(sub)">
                  <i class="ri-delete-bin-line"></i>
                </button>
              </div>
            </div>
          </div>
        </div>
        
        <!-- 空状态 -->
        <div v-if="groupedSubmissions.length === 0" class="empty-grouped">
          <i class="ri-inbox-line"></i>
          <span>暂无提交记录</span>
        </div>
      </div>
    </div>

    <!-- 删除确认弹窗 -->
    <div v-if="showDeleteConfirmModal" class="modal-overlay" @click="showDeleteConfirmModal = false">
      <div class="modal-dialog confirm-modal" @click.stop>
        <div class="modal-header">
          <h3>确认删除</h3>
        </div>
        <div class="modal-body confirm-body">
          <p>确定要删除 <strong>{{ deleteTargetSubmission?.candidate_name }}</strong> 的提交记录吗？</p>
          <p class="confirm-warning">
            <i class="ri-error-warning-line"></i>
            此操作不可恢复
          </p>
        </div>
        <div class="modal-footer">
          <button class="btn-cancel" @click="showDeleteConfirmModal = false">取消</button>
          <button class="btn-danger" @click="confirmDeleteSubmission">确认删除</button>
        </div>
      </div>
    </div>
    
    <!-- ⭐ V44: 批量删除确认弹窗（优化样式） -->
    <div v-if="showBatchDeleteModal" class="modal-overlay batch-delete-overlay" @click="showBatchDeleteModal = false">
      <div class="batch-delete-dialog" @click.stop>
        <!-- 顶部警告图标 -->
        <div class="batch-delete-icon">
          <i class="ri-delete-bin-line"></i>
        </div>
        
        <!-- 标题 -->
        <h3 class="batch-delete-title">批量删除确认</h3>
        
        <!-- 删除数量提示 -->
        <p class="batch-delete-count">
          即将删除 <strong>{{ selectedSubmissions.size }}</strong> 条提交记录
        </p>
        
        <!-- 预览列表 -->
          <div class="batch-delete-preview">
            <div v-for="sub in filteredSubmissions.filter(s => selectedSubmissions.has(s.id)).slice(0, 5)" :key="sub.id" class="preview-item">
            <div class="preview-avatar">{{ sub.candidate_name?.charAt(0) || '?' }}</div>
            <div class="preview-info">
              <span class="preview-name">{{ sub.candidate_name }}</span>
              <span class="preview-questionnaire">{{ sub.questionnaire_name }}</span>
            </div>
            </div>
            <div v-if="selectedSubmissions.size > 5" class="preview-more">
            <i class="ri-more-2-line"></i>
            还有 {{ selectedSubmissions.size - 5 }} 条记录
            </div>
          </div>
        
        <!-- 警告提示 -->
        <div class="batch-delete-warning">
            <i class="ri-error-warning-line"></i>
          <span>此操作不可恢复，请谨慎操作</span>
        </div>
        
        <!-- 操作按钮 -->
        <div class="batch-delete-actions">
          <button class="btn-batch-cancel" @click="showBatchDeleteModal = false">
            取消
          </button>
          <button class="btn-batch-confirm" @click="confirmBatchDelete">
            <i class="ri-delete-bin-line"></i>
            确认删除
          </button>
        </div>
      </div>
    </div>

    <!-- 导出弹窗 -->
    <div v-if="showExportModal" class="modal-overlay" @click="closeExportModal">
      <div class="modal-dialog export-modal" @click.stop>
        <div class="modal-header">
          <h3><i class="ri-download-line"></i> 导出数据</h3>
          <button class="btn-close" @click="closeExportModal">
            <i class="ri-close-line"></i>
          </button>
        </div>
        <div class="modal-body export-body">
          <p class="export-info">
            <i class="ri-file-list-3-line"></i>
            将导出 <strong>{{ filteredSubmissions.length }}</strong> 条提交记录
          </p>
          <div class="export-format-group">
            <label class="format-label">选择导出格式：</label>
            <div class="format-options">
              <label class="format-option" :class="{ active: exportFormat === 'csv' }">
                <input type="radio" v-model="exportFormat" value="csv" />
                <i class="ri-file-text-line"></i>
                <span>CSV 文件</span>
                <small>通用格式，可用Excel打开</small>
              </label>
              <label class="format-option" :class="{ active: exportFormat === 'excel' }">
                <input type="radio" v-model="exportFormat" value="excel" />
                <i class="ri-file-excel-2-line"></i>
                <span>Excel 文件</span>
                <small>带格式的表格文件</small>
              </label>
            </div>
          </div>
        </div>
        <div class="modal-footer">
          <button class="btn-cancel" @click="closeExportModal">取消</button>
          <button class="btn-primary" @click="executeExport" :disabled="exportLoading">
            <i v-if="exportLoading" class="ri-loader-4-line spinning"></i>
            <i v-else class="ri-download-line"></i>
            {{ exportLoading ? '导出中...' : '确认导出' }}
          </button>
        </div>
      </div>
    </div>

    <!-- 导出成功提示 -->
    <Transition name="toast">
      <div v-if="showExportSuccessToast" class="toast-success">
        <i class="ri-checkbox-circle-fill"></i>
        <span>{{ filteredSubmissions.length > 0 ? '导出成功！文件已下载' : '暂无数据可导出' }}</span>
      </div>
    </Transition>

    <!-- 提交详情弹窗 -->
    <SubmissionDetailModal
      v-if="showSubmissionDetailModal"
      :submission="selectedSubmission"
      @close="showSubmissionDetailModal = false"
      @delete="handleDeleteSubmission"
      @export-pdf="handleExportPDF"
    />
  </div>
</template>

<style scoped>
/* ===== V45: 现代化工具栏 - 飞书/Notion风格 ===== */
.toolbar {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 0.875rem 1.25rem;
  background: white;
  border-bottom: 1px solid #e5e7eb;
  flex-wrap: wrap;
}

/* 搜索框 */
.toolbar-search {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 0.75rem;
  background: #f9fafb;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  min-width: 240px;
  transition: all 0.2s;
}

.toolbar-search:focus-within {
  background: white;
  border-color: #6366f1;
  box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.1);
}

.toolbar-search i {
  color: #9ca3af;
  font-size: 1rem;
}

.toolbar-search input {
  flex: 1;
  border: none;
  background: transparent;
  font-size: 0.875rem;
  color: #1f2937;
  outline: none;
}

.toolbar-search input::placeholder {
  color: #9ca3af;
}

/* 筛选器组 */
.toolbar-filters {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  flex-wrap: wrap;
}

/* 筛选芯片 - 现代化设计 */
.filter-chip {
  display: flex;
  align-items: center;
  gap: 0.375rem;
  padding: 0.375rem 0.625rem;
  background: #f9fafb;
  border: 1px solid #e5e7eb;
  border-radius: 6px;
  font-size: 0.8125rem;
  color: #6b7280;
  cursor: pointer;
  transition: all 0.15s;
}

.filter-chip:hover {
  background: #f3f4f6;
  border-color: #d1d5db;
}

.filter-chip.active {
  background: #eef2ff;
  border-color: #c7d2fe;
  color: #4f46e5;
}

.filter-chip.active i {
  color: #6366f1;
}

.filter-chip i {
  font-size: 0.875rem;
  color: #9ca3af;
}

.filter-chip select {
  border: none;
  background: transparent;
  font-size: 0.8125rem;
  color: inherit;
  cursor: pointer;
  outline: none;
  padding-right: 0.25rem;
  appearance: none;
  -webkit-appearance: none;
}

/* 视图切换 */
.toolbar-view {
  display: flex;
  align-items: center;
  gap: 2px;
  padding: 3px;
  background: #f3f4f6;
  border-radius: 8px;
  margin-left: auto;
}

.view-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 28px;
  border: none;
  background: transparent;
  border-radius: 6px;
  color: #6b7280;
  cursor: pointer;
  transition: all 0.15s;
}

.view-btn:hover {
  color: #374151;
}

.view-btn.active {
  background: white;
  color: #6366f1;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
}

.view-btn i {
  font-size: 1rem;
}

/* 操作按钮 */
.toolbar-actions {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.action-btn {
  display: flex;
  align-items: center;
  gap: 0.375rem;
  padding: 0.5rem 0.875rem;
  border: 1px solid #e5e7eb;
  background: white;
  border-radius: 6px;
  font-size: 0.8125rem;
  font-weight: 500;
  color: #374151;
  cursor: pointer;
  transition: all 0.15s;
}

.action-btn:hover {
  background: #f9fafb;
  border-color: #d1d5db;
}

.action-btn.primary {
  background: #6366f1;
  border-color: #6366f1;
  color: white;
}

.action-btn.primary:hover {
  background: #4f46e5;
  border-color: #4f46e5;
}

.action-btn.danger {
  background: #fef2f2;
  border-color: #fecaca;
  color: #dc2626;
}

.action-btn.danger:hover {
  background: #fee2e2;
  border-color: #fca5a5;
}

.action-btn i {
  font-size: 0.9375rem;
}

.filter-select {
  padding: 0.5rem 2rem 0.5rem 0.75rem;
  border: 2px solid #e5e7eb;
  border-radius: 8px;
  font-size: 0.875rem;
  background: white;
  cursor: pointer;
  outline: none;
  transition: all 0.2s;
  appearance: none;
  background-image: url("data:image/svg+xml,%3csvg xmlns='http://www.w3.org/2000/svg' fill='none' viewBox='0 0 20 20'%3e%3cpath stroke='%236b7280' stroke-linecap='round' stroke-linejoin='round' stroke-width='1.5' d='M6 8l4 4 4-4'/%3e%3c/svg%3e");
  background-position: right 0.5rem center;
  background-repeat: no-repeat;
  background-size: 1.5em 1.5em;
}

.filter-select:focus {
  border-color: #7c3aed;
}

/* 按钮样式 - 简约风格 */
.btn-export {
  display: flex;
  align-items: center;
  gap: 0.375rem;
  padding: 0.4rem 0.875rem;
  background: #6366f1;
  color: white;
  border: none;
  border-radius: 6px;
  font-size: 0.8125rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.15s;
}

.btn-export:hover {
  background: #4f46e5;
}

.btn-export i {
  font-size: 0.9375rem;
}

/* 批量选择按钮 */
.btn-batch-select {
  display: flex;
  align-items: center;
  gap: 0.375rem;
  padding: 0.4rem 0.875rem;
  background: transparent;
  color: #6b7280;
  border: 1px solid #e5e7eb;
  border-radius: 6px;
  font-size: 0.8125rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.15s;
}

.btn-batch-select:hover {
  background: #f9fafb;
  border-color: #d1d5db;
  color: #374151;
}

.btn-batch-select i {
  font-size: 0.9375rem;
}

.btn-batch-select.active {
  background: #ef4444;
  color: white;
  border-color: #ef4444;
}

.btn-batch-select.active:hover {
  background: #dc2626;
  border-color: #dc2626;
}

/* ⭐ V44: 批量操作栏 */
.batch-action-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.75rem 1rem;
  background: linear-gradient(135deg, #fef2f2 0%, #fee2e2 100%);
  border: 1px solid #fecaca;
  border-radius: 10px;
  margin-bottom: 1rem;
}

.batch-left {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.select-all-checkbox {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  cursor: pointer;
  font-size: 0.875rem;
  color: #64748b;
}

.select-all-checkbox input {
  width: 16px;
  height: 16px;
  cursor: pointer;
  accent-color: #ef4444;
}

.selected-count {
  font-size: 0.875rem;
  font-weight: 500;
  color: #ef4444;
}

.batch-right {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.btn-batch-delete {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 1rem;
  background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%);
  color: white;
  border: none;
  border-radius: 8px;
  font-size: 0.875rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-batch-delete:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(239, 68, 68, 0.3);
}

.btn-batch-delete:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* 表格复选框列 */
.cell-checkbox {
  width: 40px;
  text-align: center;
}

.cell-checkbox input {
  width: 16px;
  height: 16px;
  cursor: pointer;
  accent-color: #7c3aed;
}

.record-row.selected {
  background: rgba(124, 58, 237, 0.05);
}

/* ⭐ V44: 批量删除弹窗样式（优化版） */
.batch-delete-overlay {
  background: rgba(0, 0, 0, 0.6);
  backdrop-filter: blur(4px);
}

.batch-delete-dialog {
  background: white;
  border-radius: 20px;
  padding: 2rem;
  width: 90%;
  max-width: 420px;
  text-align: center;
  box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.25);
  animation: batchDeleteSlideIn 0.3s ease-out;
}

@keyframes batchDeleteSlideIn {
  from {
    opacity: 0;
    transform: scale(0.9) translateY(-20px);
  }
  to {
    opacity: 1;
    transform: scale(1) translateY(0);
  }
}

.batch-delete-icon {
  width: 72px;
  height: 72px;
  margin: 0 auto 1.5rem;
  background: linear-gradient(135deg, #fee2e2 0%, #fecaca 100%);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
}

.batch-delete-icon i {
  font-size: 2rem;
  color: #ef4444;
}

.batch-delete-title {
  font-size: 1.25rem;
  font-weight: 700;
  color: #1f2937;
  margin: 0 0 0.5rem;
  /* V45: 确保标题颜色正确 */
  background: transparent;
}

.batch-delete-count {
  font-size: 0.9375rem;
  color: #64748b;
  margin: 0 0 1.25rem;
}

.batch-delete-count strong {
  color: #ef4444;
  font-weight: 700;
  font-size: 1.125rem;
}

.batch-delete-preview {
  background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%);
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  padding: 0.75rem;
  margin-bottom: 1rem;
  max-height: 180px;
  overflow-y: auto;
}

.preview-item {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.625rem;
  background: white;
  border-radius: 8px;
  margin-bottom: 0.5rem;
  transition: all 0.2s;
}

.preview-item:last-child {
  margin-bottom: 0;
}

.preview-item:hover {
  background: #fef2f2;
}

.preview-avatar {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%);
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.75rem;
  font-weight: 600;
  flex-shrink: 0;
}

.preview-info {
  flex: 1;
  text-align: left;
  min-width: 0;
}

.preview-name {
  display: block;
  font-weight: 600;
  color: #1e293b;
  font-size: 0.875rem;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.preview-questionnaire {
  display: block;
  font-size: 0.75rem;
  color: #94a3b8;
  margin-top: 2px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.preview-more {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  padding: 0.625rem;
  color: #64748b;
  font-size: 0.8125rem;
  background: rgba(239, 68, 68, 0.05);
  border-radius: 8px;
  margin-top: 0.5rem;
}

.preview-more i {
  font-size: 1rem;
}

.batch-delete-warning {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  padding: 0.75rem;
  background: #fef2f2;
  border-radius: 8px;
  margin-bottom: 1.5rem;
  font-size: 0.8125rem;
  color: #b91c1c;
}

.batch-delete-warning i {
  font-size: 1rem;
  color: #ef4444;
}

.batch-delete-actions {
  display: flex;
  gap: 0.75rem;
}

.btn-batch-cancel {
  flex: 1;
  padding: 0.75rem 1.5rem;
  background: #f1f5f9;
  border: none;
  border-radius: 10px;
  font-size: 0.9375rem;
  font-weight: 500;
  color: #64748b;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-batch-cancel:hover {
  background: #e2e8f0;
  color: #475569;
}

.btn-batch-confirm {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  padding: 0.75rem 1.5rem;
  background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%);
  border: none;
  border-radius: 10px;
  font-size: 0.9375rem;
  font-weight: 600;
  color: white;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-batch-confirm:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(239, 68, 68, 0.4);
}

.btn-batch-confirm i {
  font-size: 1rem;
}

/* ===== 统计摘要 ===== */
.records-summary {
  display: flex;
  align-items: center;
  justify-content: flex-start;
  gap: 2.5rem;
  padding: 1.25rem 1.5rem;
  background: white;
  border-bottom: 1px solid #e5e7eb;
  flex-wrap: nowrap;
}

.summary-item {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  flex-direction: row;
  white-space: nowrap;
}

.summary-item i {
  font-size: 1.125rem;
  flex-shrink: 0;
}

.summary-item .summary-value {
  font-size: 1.25rem;
  font-weight: 600;
  color: #111827;
  line-height: 1;
}

.summary-item .summary-label {
  font-size: 0.875rem;
  color: #6b7280;
  line-height: 1;
}

.summary-item.completed i {
  color: #10b981;
}

.summary-item.pending i {
  color: #f59e0b;
}

/* ===== 表格样式 ===== */
.table-wrapper {
  overflow-x: auto;
}

.records-table {
  width: 100%;
  border-collapse: collapse;
}

.records-table thead {
  background: #f9fafb;
}

.records-table th {
  padding: 0.875rem 1rem;
  text-align: left;
  font-size: 0.75rem;
  font-weight: 600;
  color: #6b7280;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  border-bottom: 1px solid #e5e7eb;
}

.records-table td {
  padding: 1rem;
  border-bottom: 1px solid #f3f4f6;
  font-size: 0.875rem;
  color: #374151;
}

.record-row:hover {
  background: #faf5ff;
}

.cell-code {
  font-family: 'SF Mono', 'Menlo', monospace;
  font-size: 0.75rem;
  color: #6b7280;
  white-space: nowrap;
  max-width: 180px;
  overflow: hidden;
  text-overflow: ellipsis;
}

.candidate-info {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  white-space: nowrap;
}

.candidate-avatar {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: linear-gradient(135deg, #7c3aed 0%, #a855f7 100%);
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.75rem;
  font-weight: 600;
}

.cell-name span:last-child {
  font-weight: 500;
  color: #1f2937;
  white-space: nowrap;
}

.cell-phone {
  color: #6b7280;
  white-space: nowrap;
}

.cell-questionnaire {
  font-weight: 500;
  white-space: nowrap;
}

.cell-type {
  white-space: nowrap;
}

.cell-status {
  white-space: nowrap;
}

.cell-time {
  white-space: nowrap;
  font-size: 0.8125rem;
  color: #6b7280;
}

.score-value {
  font-weight: 700;
  color: #1f2937;
  font-size: 1rem;
}

.score-pending, .grade-pending {
  color: #d1d5db;
  font-size: 0.875rem;
}

/* ⭐ 人格类型标签样式 */
.type-badge {
  display: inline-block;
  padding: 0.25rem 0.625rem;
  border-radius: 6px;
  font-size: 0.75rem;
  font-weight: 600;
  white-space: nowrap;
}

.type-badge.type-mbti {
  background: linear-gradient(135deg, #e0e7ff 0%, #c7d2fe 100%);
  color: #4338ca;
}

.type-badge.type-disc {
  background: linear-gradient(135deg, #fef3c7 0%, #fde68a 100%);
  color: #92400e;
}

.type-badge.type-epq {
  background: linear-gradient(135deg, #d1fae5 0%, #a7f3d0 100%);
  color: #065f46;
}

.type-badge.type-pending {
  background: #f3f4f6;
  color: #9ca3af;
}

.type-badge.type-default {
  background: #f3f4f6;
  color: #6b7280;
}

.status-pill {
  display: inline-flex;
  align-items: center;
  gap: 0.375rem;
  padding: 0.375rem 0.75rem;
  border-radius: 20px;
  font-size: 0.75rem;
  font-weight: 500;
}

.status-pill.status-completed {
  background: #d1fae5;
  color: #065f46;
}

.status-pill.status-progress {
  background: #fef3c7;
  color: #92400e;
}

.status-pill i {
  font-size: 0.875rem;
}

.cell-time {
  color: #6b7280;
  font-size: 0.8125rem;
}

.cell-actions {
  display: flex;
  gap: 0.5rem;
}

.btn-action-view {
  padding: 0.5rem;
  background: #f3f4f6;
  border: none;
  border-radius: 8px;
  color: #6b7280;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-action-view:hover {
  background: #7c3aed;
  color: white;
}

.btn-action-delete {
  padding: 0.5rem;
  background: #f3f4f6;
  border: none;
  border-radius: 8px;
  color: #6b7280;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-action-delete:hover {
  background: #ef4444;
  color: white;
}

.empty-cell {
  text-align: center;
  padding: 3rem !important;
}

.empty-state-inline {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.5rem;
  color: #9ca3af;
}

.empty-state-inline i {
  font-size: 2rem;
}

/* ===== 分组视图样式 ===== */
.grouped-view {
  padding: 1rem;
}

/* ===== 分组视图样式 ===== */
.grouped-controls {
  display: flex;
  justify-content: flex-end;
  margin-bottom: 1rem;
}

.btn-toggle-all {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 1rem;
  background: white;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  font-size: 0.8125rem;
  color: #6b7280;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-toggle-all:hover {
  background: #f3f4f6;
  border-color: #d1d5db;
}

.candidate-groups {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.candidate-group-card {
  background: white;
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  overflow: hidden;
  transition: all 0.2s;
}

.candidate-group-card:hover {
  border-color: #d1d5db;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
}

.candidate-group-card.expanded {
  border-color: #8b5cf6;
  box-shadow: 0 4px 12px rgba(139, 92, 246, 0.1);
}

.group-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.875rem 1rem;
  cursor: pointer;
  background: linear-gradient(135deg, #faf5ff 0%, #f5f3ff 100%);
  transition: all 0.2s;
  gap: 0.75rem;
}

.group-header:hover {
  background: linear-gradient(135deg, #f3e8ff 0%, #ede9fe 100%);
}

.group-main {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  flex: 1;
  min-width: 0;
}

.group-avatar {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  flex-shrink: 0;
  background: linear-gradient(135deg, #7c3aed 0%, #a855f7 100%);
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.875rem;
  flex-shrink: 0;
  font-weight: 600;
}

.group-info {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  flex: 1;
  min-width: 0;
}

.group-name-row {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.group-name {
  font-weight: 600;
  color: #1f2937;
  font-size: 0.9375rem;
  white-space: nowrap;
}

.group-phone {
  font-size: 0.8125rem;
  color: #9ca3af;
  white-space: nowrap;
}

.group-stats {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  flex-wrap: wrap;
}

.stat-badge {
  display: inline-flex;
  align-items: center;
  gap: 0.25rem;
  padding: 0.25rem 0.5rem;
  border-radius: 12px;
  font-size: 0.7rem;
  font-weight: 500;
  white-space: nowrap;
}

.stat-badge.total {
  background: #f3f4f6;
  color: #4b5563;
}

.stat-badge.completed {
  background: #d1fae5;
  color: #065f46;
}

.stat-badge.latest {
  background: #dbeafe;
  color: #1e40af;
}

.stat-badge i {
  font-size: 0.875rem;
}

.expand-icon {
  font-size: 1.25rem;
  color: #9ca3af;
  transition: transform 0.2s;
}

.candidate-group-card.expanded .expand-icon {
  color: #7c3aed;
}

/* 展开的测评列表 */
.group-submissions {
  border-top: 1px solid #e5e7eb;
  background: white;
}

.submission-item {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.625rem 1rem;
  border-bottom: 1px solid #f3f4f6;
  transition: background 0.2s;
}

.submission-item.selected {
  background: rgba(124, 58, 237, 0.05);
}

/* V45: 分组模式下的复选框 */
.submission-checkbox {
  width: 16px;
  height: 16px;
  cursor: pointer;
  accent-color: #7c3aed;
  flex-shrink: 0;
}

.submission-item:last-child {
  border-bottom: none;
}

.submission-item:hover {
  background: #faf5ff;
}

.submission-order {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background: linear-gradient(135deg, #e0e7ff 0%, #ddd6fe 100%);
  color: #6366f1;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.625rem;
  font-weight: 600;
  flex-shrink: 0;
}

.submission-info {
  flex: 1;
  min-width: 0;
}

.submission-questionnaire {
  font-weight: 500;
  color: #1f2937;
  font-size: 0.8125rem;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.submission-time {
  font-size: 0.6875rem;
  color: #9ca3af;
  white-space: nowrap;
}

.submission-result {
  display: flex;
  align-items: center;
  gap: 0.375rem;
  flex-shrink: 0;
}

.submission-result .type-badge {
  font-size: 0.625rem;
  padding: 0.125rem 0.375rem;
}

.status-mini {
  padding: 0.125rem 0.5rem;
  border-radius: 4px;
  font-size: 0.6875rem;
  font-weight: 500;
}

.status-mini.completed {
  background: #d1fae5;
  color: #065f46;
}

.status-mini.progress {
  background: #fef3c7;
  color: #92400e;
}

.submission-actions {
  display: flex;
  gap: 0.375rem;
}

.btn-mini {
  padding: 0.375rem;
  background: #f3f4f6;
  border: none;
  border-radius: 6px;
  color: #6b7280;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-mini:hover {
  background: #7c3aed;
  color: white;
}

.btn-mini.delete:hover {
  background: #ef4444;
}

.btn-mini i {
  font-size: 0.875rem;
}

.empty-grouped {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 3rem;
  color: #9ca3af;
  gap: 0.5rem;
}

.empty-grouped i {
  font-size: 2.5rem;
}

/* ===== 弹窗样式 ===== */
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

.modal-dialog {
  background: white;
  border-radius: 16px;
  width: 90%;
  max-width: 420px;
  overflow: hidden;
  box-shadow: 0 20px 40px rgba(0, 0, 0, 0.2);
}

.confirm-modal .modal-header {
  padding: 1.25rem 1.5rem;
  border-bottom: 1px solid #e5e7eb;
}

.confirm-modal .modal-header h3 {
  margin: 0;
  font-size: 1.125rem;
  font-weight: 600;
  color: #1f2937;
}

.confirm-body {
  padding: 1.5rem;
}

.confirm-body p {
  margin: 0 0 1rem 0;
  color: #374151;
}

.confirm-warning {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  color: #dc2626;
  font-size: 0.875rem;
}

.confirm-warning i {
  font-size: 1.125rem;
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 0.75rem;
  padding: 1rem 1.5rem;
  background: #f9fafb;
  border-top: 1px solid #e5e7eb;
}

.btn-cancel {
  padding: 0.5rem 1rem;
  background: white;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  color: #6b7280;
  font-size: 0.875rem;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-cancel:hover {
  background: #f3f4f6;
}

.btn-danger {
  padding: 0.5rem 1rem;
  background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%);
  border: none;
  border-radius: 8px;
  color: white;
  font-size: 0.875rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-danger:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(239, 68, 68, 0.3);
}

/* ===== 导出弹窗 ===== */
.export-modal {
  max-width: 480px;
}

.export-modal .modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.export-modal .modal-header h3 {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.export-modal .modal-header h3 i {
  color: #10b981;
}

.btn-close {
  background: none;
  border: none;
  font-size: 1.25rem;
  color: #9ca3af;
  cursor: pointer;
  padding: 0.25rem;
  border-radius: 4px;
  transition: all 0.2s;
}

.btn-close:hover {
  background: #f3f4f6;
  color: #6b7280;
}

.export-body {
  padding: 1.5rem !important;
}

.export-info {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 1rem;
  background: linear-gradient(135deg, #ecfdf5 0%, #d1fae5 100%);
  border-radius: 8px;
  color: #059669;
  font-size: 0.9375rem;
  margin-bottom: 1.5rem;
}

.export-info i {
  font-size: 1.25rem;
}

.export-format-group {
  margin-top: 0.5rem;
}

.format-label {
  display: block;
  font-size: 0.875rem;
  font-weight: 500;
  color: #374151;
  margin-bottom: 0.75rem;
}

.format-options {
  display: flex;
  gap: 1rem;
}

.format-option {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.5rem;
  padding: 1.25rem 1rem;
  background: #f9fafb;
  border: 2px solid #e5e7eb;
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.2s;
}

.format-option:hover {
  border-color: #10b981;
  background: #f0fdf4;
}

.format-option.active {
  border-color: #10b981;
  background: linear-gradient(135deg, #ecfdf5 0%, #d1fae5 100%);
}

.format-option input {
  display: none;
}

.format-option i {
  font-size: 2rem;
  color: #6b7280;
}

.format-option.active i {
  color: #10b981;
}

.format-option span {
  font-size: 0.9375rem;
  font-weight: 500;
  color: #374151;
}

.format-option small {
  font-size: 0.75rem;
  color: #9ca3af;
  text-align: center;
}

.btn-primary {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 1.25rem;
  background: linear-gradient(135deg, #10b981 0%, #059669 100%);
  border: none;
  border-radius: 8px;
  color: white;
  font-size: 0.875rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-primary:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(16, 185, 129, 0.3);
}

.btn-primary:disabled {
  opacity: 0.7;
  cursor: not-allowed;
}

.spinning {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

/* ===== 成功提示 ===== */
.toast-success {
  position: fixed;
  bottom: 2rem;
  left: 50%;
  transform: translateX(-50%);
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 1rem 1.5rem;
  background: linear-gradient(135deg, #10b981 0%, #059669 100%);
  color: white;
  border-radius: 12px;
  box-shadow: 0 10px 40px rgba(16, 185, 129, 0.3);
  font-size: 0.9375rem;
  font-weight: 500;
  z-index: 10000;
}

.toast-success i {
  font-size: 1.25rem;
}

.toast-enter-active,
.toast-leave-active {
  transition: all 0.3s ease;
}

.toast-enter-from,
.toast-leave-to {
  opacity: 0;
  transform: translateX(-50%) translateY(20px);
}

/* ===== 响应式 ===== */
@media (max-width: 768px) {
  .records-filter-bar {
    padding: 0.875rem 1rem;
  }
  
  .filter-row-main {
    flex-direction: column;
    align-items: stretch;
    gap: 0.75rem;
  }
  
  .filter-left {
    flex-wrap: wrap;
  }
  
  .filter-actions {
    justify-content: flex-end;
  }
  
  .filter-row-conditions {
    flex-wrap: wrap;
    gap: 0.75rem;
  }
  
  .search-box input {
    min-width: 150px;
  }
}
</style>

