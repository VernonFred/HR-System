import { ref, type Ref } from 'vue'
import {
  analyzeJDForProfile,
  analyzeMultipleResumesForProfile,
  analyzeResumeForProfile,
} from '@/api/jobProfiles'
import type { JobProfileForm } from './types'

type MessageType = 'info' | 'warning' | 'success' | 'error'

interface UseJobProfileAiGenerationOptions {
  formData: Ref<JobProfileForm>
  isNew: Ref<boolean>
  isAIGenerated: Ref<boolean>
  showImportResumeDialog: Ref<boolean>
  showImportJDDialog: Ref<boolean>
  showEditorDialog: Ref<boolean>
  showMessage: (message: string, type?: MessageType) => void
}

const readFileAsText = (file: File): Promise<string> => {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = e => resolve((e.target?.result as string) || '')
    reader.onerror = () => reject(new Error('文件读取失败'))
    reader.readAsText(file)
  })
}

export function useJobProfileAiGeneration(options: UseJobProfileAiGenerationOptions) {
  const selectedResumes = ref<File[]>([])
  const selectedJD = ref<File | null>(null)
  const aiGenerating = ref(false)
  const resumeInput = ref<HTMLInputElement | null>(null)
  const jdInput = ref<HTMLInputElement | null>(null)
  const uploadProgress = ref(0)
  const isUploading = ref(false)

  const applyGeneratedProfile = (result: any) => {
    options.formData.value = {
      name: result.name,
      department: result.department || '未知部门',
      tags: result.tags || [],
      description: result.description || '',
      dimensions: result.dimensions.map((d: any) => ({
        name: d.name,
        weight: d.weight,
        description: d.description || '',
      })),
    }
    options.isNew.value = true
    options.isAIGenerated.value = true
    options.showEditorDialog.value = true
  }

  const triggerResumeInput = () => {
    resumeInput.value?.click()
  }

  const handleResumeSelect = (event: Event) => {
    const target = event.target as HTMLInputElement
    if (target.files) {
      selectedResumes.value = [...selectedResumes.value, ...Array.from(target.files)]
      target.value = ''
    }
  }

  const removeResume = (idx: number) => {
    selectedResumes.value.splice(idx, 1)
  }

  const generateFromResumes = async () => {
    if (selectedResumes.value.length === 0 || aiGenerating.value) return

    aiGenerating.value = true
    isUploading.value = true
    uploadProgress.value = 0
    let analysisInterval: ReturnType<typeof setInterval> | null = null

    try {
      const files = selectedResumes.value
      const fileCount = files.length
      const fileName = files[0].name.replace(/\.(pdf|docx?|txt)$/i, '')
      const jobTitle = fileName.split(/[_\-]/)[0] || '未命名岗位'

      uploadProgress.value = 40
      analysisInterval = setInterval(() => {
        if (uploadProgress.value < 90) uploadProgress.value += 5
      }, 500)

      const result = fileCount === 1
        ? await analyzeResumeForProfile(files[0], jobTitle)
        : await analyzeMultipleResumesForProfile(files, jobTitle)

      uploadProgress.value = 100
      applyGeneratedProfile(result)
      options.showImportResumeDialog.value = false
      selectedResumes.value = []
      options.showMessage(
        fileCount > 1 ? `AI分析完成，已从${fileCount}份简历中提取共性特征` : 'AI分析完成，已生成岗位画像建议',
        'success',
      )
    } catch (error: any) {
      console.error('AI生成失败:', error)
      const errorMsg = error?.message || error?.detail || '服务暂时不可用，请稍后重试'
      options.showMessage(`AI生成失败：${errorMsg}`, 'error')
    } finally {
      if (analysisInterval) clearInterval(analysisInterval)
      aiGenerating.value = false
      isUploading.value = false
      uploadProgress.value = 0
    }
  }

  const triggerJDInput = () => {
    jdInput.value?.click()
  }

  const handleJDSelect = (event: Event) => {
    const target = event.target as HTMLInputElement
    if (target.files && target.files[0]) {
      selectedJD.value = target.files[0]
    }
  }

  const generateFromJD = async () => {
    if (!selectedJD.value || aiGenerating.value) return

    aiGenerating.value = true
    isUploading.value = true
    uploadProgress.value = 0
    let analysisInterval: ReturnType<typeof setInterval> | null = null

    try {
      const file = selectedJD.value
      const fileName = file.name.replace(/\.(pdf|docx?|txt)$/i, '')
      const jobTitle = fileName.split(/[_\-]/)[0] || '未命名岗位'

      uploadProgress.value = 20
      const jdText = await readFileAsText(file)
      uploadProgress.value = 40
      analysisInterval = setInterval(() => {
        if (uploadProgress.value < 90) uploadProgress.value += 5
      }, 500)

      const result = await analyzeJDForProfile(jdText, jobTitle)
      uploadProgress.value = 100
      applyGeneratedProfile(result)
      options.showImportJDDialog.value = false
      selectedJD.value = null
      options.showMessage('AI分析完成，已生成岗位画像建议', 'success')
    } catch (error: any) {
      console.error('AI生成失败:', error)
      const errorMsg = error?.message || error?.detail || '服务暂时不可用，请稍后重试'
      options.showMessage(`AI生成失败：${errorMsg}`, 'error')
    } finally {
      if (analysisInterval) clearInterval(analysisInterval)
      aiGenerating.value = false
      isUploading.value = false
      uploadProgress.value = 0
    }
  }

  return {
    selectedResumes,
    selectedJD,
    aiGenerating,
    resumeInput,
    jdInput,
    uploadProgress,
    isUploading,
    triggerResumeInput,
    handleResumeSelect,
    removeResume,
    generateFromResumes,
    triggerJDInput,
    handleJDSelect,
    generateFromJD,
  }
}
