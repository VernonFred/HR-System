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
import { ref, computed, defineAsyncComponent, watch } from 'vue'
import type { Submission, Questionnaire } from '../api/assessments'
import { useSubmissionRecordsExport } from './useSubmissionRecordsExport'
import { useSubmissionRecordsGrouping, type DisplaySubmission } from './useSubmissionRecordsGrouping'

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
// ===== 分页状态 =====
const currentPage = ref(1)
const pageSize = 10

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
  if (id < 0) return
  if (selectedSubmissions.value.has(id)) {
    selectedSubmissions.value.delete(id)
  } else {
    selectedSubmissions.value.add(id)
  }
}

// 全选/取消全选
const toggleSelectAll = () => {
  if (selectedSubmissions.value.size === selectableSubmissions.value.length) {
    selectedSubmissions.value.clear()
  } else {
    selectedSubmissions.value = new Set(selectableSubmissions.value.map(s => s.id))
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

const {
  groupPageSize,
  groupListPageSize,
  groupListPage,
  displaySubmissions,
  selectableSubmissions,
  isAggregateSubmission,
  getGroupKey,
  getGroupDisplayName,
  getGroupPage,
  setGroupPage,
  getGroupTotalPages,
  getGroupSubmissions,
  changeGroupPage,
  changeGroupListPage,
  groupedSubmissionsAll,
  groupListTotalPages,
  getGroupPendingCount,
  paginatedGroupedSubmissions,
  visibleGroupKeys,
  areVisibleGroupsExpanded,
} = useSubmissionRecordsGrouping(filteredSubmissions, expandedCandidates)

// ===== 分页相关 =====
const actualFilteredCount = computed(() => filteredSubmissions.value.length)
const displayFilteredCount = computed(() => displaySubmissions.value.length)
const totalPages = computed(() => Math.ceil(displayFilteredCount.value / pageSize))
const paginatedSubmissions = computed(() => {
  const start = (currentPage.value - 1) * pageSize
  const end = start + pageSize
  return displaySubmissions.value.slice(start, end)
})

const changePage = (newPage: number) => {
  if (newPage < 1 || newPage > totalPages.value) return
  currentPage.value = newPage
}

// 筛选变化时重置页码
watch([searchQuery, filterQuestionnaire, filterStatus, filterYear, filterMonth], () => {
  currentPage.value = 1
})

watch(groupByCandidate, () => {
  groupListPage.value = 1
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
    'pending': '待处理',
    'anonymous': '匿名汇总'
  }
  return labels[status] || status
}

// ⭐ 获取人格类型（从result_details中提取）
const getPersonalityType = (submission: Submission | DisplaySubmission) => {
  if (isAggregateSubmission(submission)) return '匿名'
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

const handleDeleteSubmission = (submission: Submission | DisplaySubmission) => {
  if (isAggregateSubmission(submission)) return
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
    setGroupPage(key, 1)
  }
}

// 全部展开/收起
const toggleAllCandidates = () => {
  const keys = visibleGroupKeys.value
  if (areVisibleGroupsExpanded.value) {
    keys.forEach(key => expandedCandidates.value.delete(key))
    return
  }
  keys.forEach(key => {
    expandedCandidates.value.add(key)
    setGroupPage(key, 1)
  })
}

const {
  showExportModal,
  exportFormat,
  exportLoading,
  showExportSuccessToast,
  openExportModal,
  closeExportModal,
  executeExport,
} = useSubmissionRecordsExport({
  filteredSubmissions,
  getPersonalityType,
  getStatusLabel,
  formatDate,
})
</script>

<template src="./SubmissionRecordsTab.template.html"></template>


<style scoped>
@import './styles/submission-records-tab.css';
</style>
