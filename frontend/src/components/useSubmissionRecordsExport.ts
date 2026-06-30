import { ref, type ComputedRef } from 'vue'
import * as XLSX from 'xlsx'
import type { Submission } from '../api/assessments'

interface UseSubmissionRecordsExportOptions {
  filteredSubmissions: ComputedRef<Submission[]>
  getPersonalityType: (submission: Submission) => string
  getStatusLabel: (status: string) => string
  formatDate: (dateStr: string | null | undefined) => string
}

export function useSubmissionRecordsExport(options: UseSubmissionRecordsExportOptions) {
  const showExportModal = ref(false)
  const exportFormat = ref<'csv' | 'excel'>('csv')
  const exportLoading = ref(false)
  const showExportSuccessToast = ref(false)

  const openExportModal = () => {
    if (options.filteredSubmissions.value.length === 0) {
      showExportSuccessToast.value = true
      setTimeout(() => { showExportSuccessToast.value = false }, 2000)
      return
    }
    showExportModal.value = true
  }

  const closeExportModal = () => {
    showExportModal.value = false
  }

  const executeExport = async () => {
    exportLoading.value = true

    try {
      const data = options.filteredSubmissions.value.map(r => ({
        '编号': r.code,
        '姓名': r.candidate_name,
        '联系方式': r.candidate_phone,
        '会议姓名': r.custom_data?.meeting_identity?.candidate_name || '',
        '会议手机号': r.custom_data?.meeting_identity?.candidate_phone || '',
        '会议学校': r.custom_data?.meeting_identity?.school || '',
        '会议部门': r.custom_data?.meeting_identity?.department || '',
        '问卷': r.questionnaire_name,
        '类型': options.getPersonalityType(r),
        '状态': options.getStatusLabel(r.status),
        '提交时间': options.formatDate(r.submitted_at),
      }))

      const headers = Object.keys(data[0] || {})
      const dateStr = new Date().toISOString().slice(0, 10)

      if (exportFormat.value === 'csv') {
        const csvContent = [
          headers.join(','),
          ...data.map(row => headers.map(h => `"${(row as any)[h] || ''}"`).join(',')),
        ].join('\n')
        const blob = new Blob(['\uFEFF' + csvContent], { type: 'text/csv;charset=utf-8;' })
        const link = document.createElement('a')
        link.href = URL.createObjectURL(blob)
        link.download = `提交记录_${dateStr}.csv`
        link.click()
      } else {
        const workbook = XLSX.utils.book_new()
        const sheet = XLSX.utils.json_to_sheet(data)
        XLSX.utils.book_append_sheet(workbook, sheet, '提交记录')
        const excelBuffer = XLSX.write(workbook, {
          bookType: 'xlsx',
          type: 'array',
        })
        const blob = new Blob([excelBuffer], {
          type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        })
        const link = document.createElement('a')
        link.href = URL.createObjectURL(blob)
        link.download = `提交记录_${dateStr}.xlsx`
        link.click()
      }

      showExportModal.value = false
      showExportSuccessToast.value = true
      setTimeout(() => { showExportSuccessToast.value = false }, 3000)
    } catch (error) {
      console.error('导出失败:', error)
    } finally {
      exportLoading.value = false
    }
  }

  return {
    showExportModal,
    exportFormat,
    exportLoading,
    showExportSuccessToast,
    openExportModal,
    closeExportModal,
    executeExport,
  }
}
