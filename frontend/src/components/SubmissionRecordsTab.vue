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
import * as XLSX from 'xlsx'
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
const groupPageSize = 10
const groupPage = ref<Record<string, number>>({})
const groupListPageSize = 10
const groupListPage = ref(1)

type DisplaySubmission = Submission & {
  __anonymousAggregate?: boolean
  anonymous_count?: number
}

const isEmptyIdentity = (value?: string) => {
  const normalized = (value || '').trim().toLowerCase()
  if (!normalized) return true
  return ['匿名', '未知', 'unknown', 'n/a', 'na', '-', '—', '--', 'null'].includes(normalized)
}

const isAnonymousSubmission = (name?: string, phone?: string) => {
  if (!isEmptyIdentity(phone)) return false
  return isEmptyIdentity(name)
}

const isAggregateSubmission = (submission: Submission | DisplaySubmission) => {
  return Boolean((submission as DisplaySubmission).__anonymousAggregate)
}

const getGroupKey = (group: GroupedCandidate) => group.phone || group.name || 'unknown'

const getGroupDisplayName = (group: GroupedCandidate) => {
  if (isAnonymousSubmission(group.name, group.phone)) {
    return `匿名填写（${group.totalSubmissions}人）`
  }
  return group.name || '未知'
}

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

const getSubmissionTime = (submission: Submission) => {
  return submission.submitted_at || submission.started_at || ''
}

const getLatestSubmission = (subs: Submission[]) => {
  let latest: Submission | null = null
  for (const sub of subs) {
    const time = getSubmissionTime(sub)
    if (!time) continue
    if (!latest || new Date(time) > new Date(getSubmissionTime(latest))) {
      latest = sub
    }
  }
  return latest || subs[0] || null
}

const anonymousSubmissions = computed(() =>
  filteredSubmissions.value.filter(s => isAnonymousSubmission(s.candidate_name, s.candidate_phone))
)

const displaySubmissions = computed<DisplaySubmission[]>(() => {
  const anonSubs = anonymousSubmissions.value
  const normalSubs = filteredSubmissions.value.filter(
    s => !isAnonymousSubmission(s.candidate_name, s.candidate_phone)
  )

  if (anonSubs.length === 0) {
    return normalSubs
  }

  const questionnaireNames = Array.from(
    new Set(anonSubs.map(s => s.questionnaire_name).filter(Boolean))
  )
  const questionnaireName =
    questionnaireNames.length === 1 ? questionnaireNames[0] : '多个问卷'
  const latestSubmission = getLatestSubmission(anonSubs)
  const latestTime = latestSubmission ? getSubmissionTime(latestSubmission) : ''

  const aggregate: DisplaySubmission = {
    id: -1,
    code: `ANON-${anonSubs.length}`,
    candidate_name: `匿名填写（${anonSubs.length}人）`,
    candidate_phone: '',
    questionnaire_name: questionnaireName || '匿名提交',
    questionnaire_type:
      questionnaireNames.length === 1 ? anonSubs[0]?.questionnaire_type : undefined,
    status: 'anonymous',
    started_at: latestTime || new Date().toISOString(),
    submitted_at: latestTime || undefined,
    __anonymousAggregate: true,
    anonymous_count: anonSubs.length,
  }

  return [aggregate, ...normalSubs]
})

// ===== 分页相关 =====
const actualFilteredCount = computed(() => filteredSubmissions.value.length)
const displayFilteredCount = computed(() => displaySubmissions.value.length)
const totalPages = computed(() => Math.ceil(displayFilteredCount.value / pageSize))
const selectableSubmissions = computed(() =>
  displaySubmissions.value.filter(s => !isAggregateSubmission(s))
)

const paginatedSubmissions = computed(() => {
  const start = (currentPage.value - 1) * pageSize
  const end = start + pageSize
  return displaySubmissions.value.slice(start, end)
})

const getGroupPage = (key: string) => groupPage.value[key] || 1

const setGroupPage = (key: string, page: number) => {
  groupPage.value = { ...groupPage.value, [key]: page }
}

const getGroupTotalPages = (group: GroupedCandidate) =>
  Math.max(1, Math.ceil(group.submissions.length / groupPageSize))

const getGroupSubmissions = (group: GroupedCandidate) => {
  const key = getGroupKey(group)
  const page = getGroupPage(key)
  const start = (page - 1) * groupPageSize
  const end = start + groupPageSize
  return group.submissions.slice(start, end)
}

const changeGroupPage = (group: GroupedCandidate, nextPage: number) => {
  const key = getGroupKey(group)
  const total = getGroupTotalPages(group)
  if (nextPage < 1 || nextPage > total) return
  setGroupPage(key, nextPage)
}

const changePage = (newPage: number) => {
  if (newPage < 1 || newPage > totalPages.value) return
  currentPage.value = newPage
}

const changeGroupListPage = (newPage: number) => {
  if (newPage < 1 || newPage > groupListTotalPages.value) return
  groupListPage.value = newPage
}

// ===== 按候选人分组的提交记录 =====
interface GroupedCandidate {
  phone: string
  name: string
  totalSubmissions: number
  completedCount: number
  latestSubmission: Submission | null
  submissions: Submission[]
}

const groupedSubmissionsAll = computed<GroupedCandidate[]>(() => {
  const groups = new Map<string, GroupedCandidate>()

  const anonSubs = anonymousSubmissions.value
  if (anonSubs.length > 0) {
    const latest = getLatestSubmission(anonSubs)
    groups.set('__anonymous__', {
      phone: '',
      name: `匿名填写（${anonSubs.length}人）`,
      totalSubmissions: anonSubs.length,
      completedCount: anonSubs.filter(s => s.status === 'completed').length,
      latestSubmission: latest,
      submissions: anonSubs
    })
  }

  for (const sub of filteredSubmissions.value) {
    if (isAnonymousSubmission(sub.candidate_name, sub.candidate_phone)) {
      continue
    }
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

const groupListTotalPages = computed(() => Math.ceil(groupedSubmissionsAll.value.length / groupListPageSize) || 1)

// 筛选变化时重置页码
watch([searchQuery, filterQuestionnaire, filterStatus, filterYear, filterMonth], () => {
  currentPage.value = 1
  groupListPage.value = 1
})

watch(groupByCandidate, () => {
  groupListPage.value = 1
})

watch(groupListTotalPages, (total) => {
  if (groupListPage.value > total) {
    groupListPage.value = total
  }
})

const getGroupPendingCount = (group: GroupedCandidate) => {
  return Math.max(0, group.totalSubmissions - group.completedCount)
}

const paginatedGroupedSubmissions = computed<GroupedCandidate[]>(() => {
  const start = (groupListPage.value - 1) * groupListPageSize
  const end = start + groupListPageSize
  return groupedSubmissionsAll.value.slice(start, end)
})

const visibleGroupKeys = computed(() =>
  paginatedGroupedSubmissions.value.map(group => getGroupKey(group))
)

const areVisibleGroupsExpanded = computed(() => {
  if (visibleGroupKeys.value.length === 0) return false
  return visibleGroupKeys.value.every(key => expandedCandidates.value.has(key))
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
      // 真正的 .xlsx 导出，避免部分客户端把内容当源码展示
      const workbook = XLSX.utils.book_new()
      const sheet = XLSX.utils.json_to_sheet(data)
      XLSX.utils.book_append_sheet(workbook, sheet, '提交记录')
      const excelBuffer = XLSX.write(workbook, {
        bookType: 'xlsx',
        type: 'array'
      })
      const blob = new Blob([excelBuffer], {
        type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
      })
      const link = document.createElement('a')
      link.href = URL.createObjectURL(blob)
      link.download = `提交记录_${dateStr}.xlsx`
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

<template src="./SubmissionRecordsTab.template.html"></template>


<style scoped>
@import './styles/submission-records-tab.css';
</style>
