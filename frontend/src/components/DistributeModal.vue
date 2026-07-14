<script setup lang="ts">
/**
 * 分发问卷弹窗 - 多步骤表单
 *
 * 功能：
 * 1. 基本设置（名称、有效期、重复提交策略）
 * 2. 字段配置（候选人信息字段）
 * 3. 页面文案（入口页、完成页）
 * 4. 确认分发
 * 5. 分发结果（链接、二维码）
 */
import { ref, computed, onMounted, watch } from 'vue'
import QRCode from 'qrcode'
import {
  createAssessment,
  updateAssessment,
  fetchQuestionnaires,
  type Questionnaire,
  type Assessment,
  type AssessmentCreate,
  type DepartmentRoutingConfig,
  type FormField,
  type PageTexts,
} from '../api/assessments'
import FieldConfigPanel from './FieldConfigPanel.vue'
import { getQuestionnaireCopy } from '../utils/questionnaireCopy'
import { isPlainObject, useDistributeConfigStorage } from './distributeConfigStorage'

type RepeatCheckBy = 'phone' | 'phone_name' | 'name'

// ===== Props =====
const props = defineProps<{
  questionnaire: Questionnaire | null
  assessment?: Assessment | null
  mode?: 'create' | 'edit' | 'clone'
}>()

// ===== Emits =====
const emit = defineEmits<{
  (e: 'close'): void
  (e: 'success'): void
}>()

// ===== 步骤状态 =====
const currentStep = ref(1)
const loading = ref(false)
const generatedCode = ref('')
const generatedLink = ref('')
const qrcodeDataURL = ref('')
const showLinkCopied = ref(false)
const allQuestionnaires = ref<Questionnaire[]>([])

// ===== 表单数据 =====
const form = ref({
  name: '',
  validityType: 'temporary' as 'temporary' | 'permanent',
  expiryDays: 7,
  customExpiryDate: '',
  allowRepeat: false,
  repeatCheckBy: 'phone' as RepeatCheckBy,
  repeatIntervalHours: 24,
  maxSubmissions: 0,
  anonymousMode: false,
  description: '',
})

const buildDefaultPageTexts = (): PageTexts => ({
  ...getQuestionnaireCopy(props.questionnaire).pageTexts,
})

// 页面文案
const pageTexts = ref<PageTexts>(buildDefaultPageTexts())

// 表单字段 - V45: 保留姓名、手机号、性别、应聘岗位，移除邮箱
const formFields = ref<FormField[]>([
  { id: 'name', name: 'name', label: '姓名', type: 'text', placeholder: '请输入您的姓名', required: true, enabled: true, builtin: true },
  { id: 'phone', name: 'phone', label: '手机号', type: 'tel', placeholder: '请输入手机号', required: true, enabled: true, builtin: true },
  { id: 'gender', name: 'gender', label: '性别', type: 'select', placeholder: '请选择性别', required: false, enabled: true, builtin: true, options: [{ value: '男', label: '男' }, { value: '女', label: '女' }] },
  { id: 'target_position', name: 'target_position', label: '应聘岗位', type: 'text', placeholder: '请输入应聘岗位', required: false, enabled: true, builtin: true },
])

const routingConfig = ref<DepartmentRoutingConfig>({
  enabled: false,
  department_field: 'department',
  fallback_to_default: true,
  mappings: [],
})

// 页面文案编辑类型
const pageEditType = ref<'entry' | 'success'>('entry')
const isCloneMode = computed(() => props.mode === 'clone' && !!props.assessment?.id)
const isEditMode = computed(() => props.mode !== 'clone' && !!props.assessment?.id)
const copy = computed(() => getQuestionnaireCopy(props.questionnaire))
const modeTitle = computed(() => {
  if (isEditMode.value) return '编辑链接配置'
  if (isCloneMode.value) return '复制配置新建链接'
  return `创建${copy.value.linkLabel}`
})
const modeTip = computed(() => {
  if (isEditMode.value) return '当前为编辑模式，保存后访问码和链接地址保持不变。'
  if (isCloneMode.value) return '当前为复制模式，已带入原链接配置；保存后会生成新的访问码和链接。'
  return '同一问卷可以创建多个链接，用于长期、短期或不同人群的独立配置。'
})

// ===== 计算属性 =====
const enabledFields = computed(() => formFields.value.filter(f => f.enabled))
const departmentField = computed(() => {
  return formFields.value.find((f) => {
    const fieldName = (f.name || f.id || '').toString().trim()
    return fieldName === 'department' && f.type === 'select' && f.enabled !== false
  })
})
const departmentOptions = computed(() => {
  const options = departmentField.value?.options || []
  return options
    .map((opt) => {
      if (typeof opt === 'string') return opt.trim()
      const value = (opt?.value ?? opt?.label ?? '').toString().trim()
      return value
    })
    .filter(Boolean)
})
const availableTargetQuestionnaires = computed(() => {
  const currentId = props.questionnaire?.id
  return allQuestionnaires.value.filter((q) => q.id !== currentId)
})

const identityFieldNames = new Set(['name', 'candidate_name', 'phone', 'candidate_phone'])
const defaultIdentityFields: FormField[] = [
  { id: 'name', name: 'name', label: '姓名', type: 'text', placeholder: '请输入您的姓名', required: true, enabled: true, builtin: true },
  { id: 'phone', name: 'phone', label: '手机号', type: 'tel', placeholder: '请输入手机号', required: true, enabled: true, builtin: true },
]
const repeatCheckByValues = new Set<RepeatCheckBy>(['phone', 'phone_name', 'name'])

const getFieldKey = (field: FormField) => String(field.name || field.id || '').trim()

const isIdentityField = (field: FormField) => identityFieldNames.has(getFieldKey(field))

const normalizeRepeatCheckBy = (value: unknown): RepeatCheckBy => {
  return repeatCheckByValues.has(value as RepeatCheckBy) ? value as RepeatCheckBy : 'phone'
}

const isEnabledFieldKey = (keys: string[]) => {
  return formFields.value.some((field) => field.enabled !== false && keys.includes(getFieldKey(field)))
}

const hasEnabledNameField = computed(() => isEnabledFieldKey(['name', 'candidate_name']))
const hasEnabledPhoneField = computed(() => isEnabledFieldKey(['phone', 'candidate_phone']))
const repeatCheckByFieldHint = computed(() => {
  if (form.value.anonymousMode || !form.value.allowRepeat) return ''
  if (form.value.repeatCheckBy === 'phone' && !hasEnabledPhoneField.value) {
    return '当前未启用手机号字段，无法可靠按手机号判断重复提交。'
  }
  if (form.value.repeatCheckBy === 'phone_name' && (!hasEnabledPhoneField.value || !hasEnabledNameField.value)) {
    return '当前判断依据需要同时启用姓名和手机号字段。'
  }
  if (form.value.repeatCheckBy === 'name' && !hasEnabledNameField.value) {
    return '当前未启用姓名字段，无法按姓名判断重复提交。'
  }
  return ''
})

const applyAnonymousModeToFields = (enabled: boolean) => {
  if (enabled) {
    form.value.allowRepeat = false
    formFields.value = formFields.value.map((field) => {
      if (!isIdentityField(field)) return field
      return { ...field, enabled: false, required: false }
    })
    return
  }

  defaultIdentityFields.slice().reverse().forEach((defaultField) => {
    const existing = formFields.value.find((field) => getFieldKey(field) === defaultField.name)
    if (existing) {
      existing.enabled = true
      existing.required = true
    } else {
      formFields.value.unshift({ ...defaultField })
    }
  })
}

// ⭐ V50: 使用本地时间格式，避免 UTC 时区问题
const formatLocalDateTime = (date: Date): string => {
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  const hours = String(date.getHours()).padStart(2, '0')
  const minutes = String(date.getMinutes()).padStart(2, '0')
  const seconds = String(date.getSeconds()).padStart(2, '0')
  return `${year}-${month}-${day}T${hours}:${minutes}:${seconds}`
}

const toDateTimeLocalInput = (dateStr: string): string => {
  const date = new Date(dateStr)
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  const hours = String(date.getHours()).padStart(2, '0')
  const minutes = String(date.getMinutes()).padStart(2, '0')
  return `${year}-${month}-${day}T${hours}:${minutes}`
}

const validFrom = computed(() => {
  if (isEditMode.value && props.assessment?.valid_from) {
    return props.assessment.valid_from
  }
  return formatLocalDateTime(new Date())
})

const validUntil = computed(() => {
  if (form.value.validityType === 'permanent') {
    // 永久有效：设置为100年后
    const date = new Date()
    date.setFullYear(date.getFullYear() + 100)
    return formatLocalDateTime(date)
  }

  if (form.value.expiryDays === -1 && form.value.customExpiryDate) {
    return formatLocalDateTime(new Date(form.value.customExpiryDate))
  }

  const date = new Date()
  date.setDate(date.getDate() + form.value.expiryDays)
  return formatLocalDateTime(date)
})

const expiryOptions = [
  { value: 1, label: '1天' },
  { value: 3, label: '3天' },
  { value: 7, label: '7天' },
  { value: 14, label: '14天' },
  { value: 30, label: '30天' },
  { value: -1, label: '自定义' },
]

const repeatIntervalOptions = [
  { value: 0, label: '不限制' },
  { value: 1, label: '1小时' },
  { value: 24, label: '1天' },
  { value: 168, label: '1周' },
  { value: -1, label: '自定义' },
]

// ===== 方法 =====
const close = () => emit('close')

const nextStep = () => {
  if (currentStep.value < 4) {
    currentStep.value++
  }
}

const prevStep = () => {
  if (currentStep.value > 1) {
    currentStep.value--
  }
}

const loadAllQuestionnaires = async () => {
  try {
    const [professionalRes, scoredRes, surveyRes] = await Promise.all([
      fetchQuestionnaires({ category: 'professional', limit: 200 }),
      fetchQuestionnaires({ category: 'scored', limit: 200 }),
      fetchQuestionnaires({ category: 'survey', limit: 200 }),
    ])
    const merged = [
      ...(professionalRes.items || []),
      ...(scoredRes.items || []),
      ...(surveyRes.items || []),
    ]
    const mapById = new Map<number, Questionnaire>()
    merged.forEach((q) => mapById.set(q.id, q))
    allQuestionnaires.value = Array.from(mapById.values())
  } catch (error) {
    console.error('加载目标问卷列表失败:', error)
    allQuestionnaires.value = []
  }
}

const addDepartmentField = () => {
  if (departmentField.value) return
  formFields.value.push({
    id: 'department',
    name: 'department',
    label: '部门',
    type: 'select',
    placeholder: '请选择部门',
    required: true,
    enabled: true,
    builtin: false,
    options: ['技术部', '销售部', '人力资源部'],
  })
}

const addRoutingMapping = () => {
  routingConfig.value.mappings.push({
    department_value: '',
    questionnaire_id: 0,
  })
}

const removeRoutingMapping = (index: number) => {
  routingConfig.value.mappings.splice(index, 1)
}

const buildRoutingConfigPayload = (): DepartmentRoutingConfig => {
  if (!routingConfig.value.enabled) {
    return {
      enabled: false,
      department_field: 'department',
      fallback_to_default: true,
      mappings: [],
    }
  }

  const deduped = new Map<string, number>()
  routingConfig.value.mappings.forEach((item) => {
    const departmentValue = String(item.department_value || '').trim()
    const questionnaireId = Number(item.questionnaire_id || 0)
    if (!departmentValue || !questionnaireId) return
    deduped.set(departmentValue, questionnaireId)
  })

  return {
    enabled: true,
    department_field: 'department',
    fallback_to_default: true,
    mappings: Array.from(deduped.entries()).map(([department_value, questionnaire_id]) => ({
      department_value,
      questionnaire_id,
    })),
  }
}

const handleDistribute = async () => {
  if (!props.questionnaire) return

  loading.value = true
  try {
    const data: AssessmentCreate = {
      name: form.value.name || `${props.questionnaire.name} - ${new Date().toLocaleDateString()}`,
      questionnaire_id: props.questionnaire.id,
      valid_from: validFrom.value,
      valid_until: validUntil.value,
      description: form.value.description,
      form_fields: formFields.value.filter(f => f.enabled),
      page_texts: pageTexts.value,
      link_type: form.value.validityType,
      allow_repeat: form.value.anonymousMode ? false : form.value.allowRepeat,
      anonymous_mode: form.value.anonymousMode,
      repeat_check_by: form.value.repeatCheckBy,
      repeat_interval_hours: form.value.repeatIntervalHours,
      max_submissions: form.value.maxSubmissions,
      routing_config: buildRoutingConfigPayload(),
    }

    const result = isEditMode.value && props.assessment?.id
      ? await updateAssessment(props.assessment.id, data)
      : await createAssessment(data)
    generatedCode.value = result.code

    // 生成链接
    const baseUrl = window.location.origin
    generatedLink.value = `${baseUrl}/assessment/${result.code}`

    // 生成二维码
    try {
      qrcodeDataURL.value = await QRCode.toDataURL(generatedLink.value, {
        width: 200,
        margin: 2,
        color: { dark: '#1e293b', light: '#ffffff' }
      })
    } catch (e) {
      console.error('生成二维码失败:', e)
    }

    currentStep.value = 5
  } catch (error) {
    console.error('保存分发配置失败:', error)
    alert(isEditMode.value ? '保存配置失败，请重试' : '生成链接失败，请重试')
  } finally {
    loading.value = false
  }
}

const copyLink = async () => {
  try {
    // 优先使用 Clipboard API
    if (navigator.clipboard && window.isSecureContext) {
    await navigator.clipboard.writeText(generatedLink.value)
    } else {
      // 降级方案：使用 execCommand
      const textArea = document.createElement('textarea')
      textArea.value = generatedLink.value
      textArea.style.position = 'fixed'
      textArea.style.left = '-999999px'
      textArea.style.top = '-999999px'
      document.body.appendChild(textArea)
      textArea.focus()
      textArea.select()
      document.execCommand('copy')
      document.body.removeChild(textArea)
    }
    showLinkCopied.value = true
    setTimeout(() => { showLinkCopied.value = false }, 2000)
  } catch (error) {
    console.error('复制失败:', error)
    // 最后的降级：提示用户手动复制
    alert('自动复制失败，请手动复制链接')
  }
}

const downloadQRCode = () => {
  if (!qrcodeDataURL.value) return

  const link = document.createElement('a')
  link.download = `${props.questionnaire?.name || copy.value.qrFileFallback}_二维码.png`
  link.href = qrcodeDataURL.value
  link.click()
}

const getFieldIcon = (field: FormField) => {
  const icons: Record<string, string> = {
    text: 'ri-text',
    tel: 'ri-phone-line',
    email: 'ri-mail-line',
    select: 'ri-list-check-2',
    textarea: 'ri-file-text-line',
    number: 'ri-hashtag',
    date: 'ri-calendar-line',
  }
  return icons[field.type] || 'ri-input-field'
}


// ===== 配置持久化 =====
const storageKey = computed(() => `distribute_config_${copy.value.mode}`)

const { saveConfig, loadConfig } = useDistributeConfigStorage({
  storageKey,
  form,
  formFields,
  pageTexts,
  routingConfig,
})

const applyAssessmentToForm = () => {
  if (!props.assessment) return
  const current = props.assessment
  form.value.name = current.name || ''
  form.value.description = current.description || ''
  form.value.validityType = current.link_type === 'permanent' ? 'permanent' : 'temporary'
  if (form.value.validityType === 'temporary' && current.valid_until) {
    form.value.expiryDays = -1
    form.value.customExpiryDate = toDateTimeLocalInput(current.valid_until)
  }
  form.value.allowRepeat = !!current.allow_repeat
  form.value.anonymousMode = !!current.anonymous_mode
  form.value.repeatCheckBy = normalizeRepeatCheckBy(current.repeat_check_by)
  form.value.repeatIntervalHours = current.repeat_interval_hours ?? 24
  form.value.maxSubmissions = current.max_submissions ?? 0

  if (Array.isArray(current.form_fields)) {
    formFields.value = current.form_fields as FormField[]
  }
  if (current.page_texts && isPlainObject(current.page_texts)) {
    pageTexts.value = { ...pageTexts.value, ...current.page_texts }
  }
  if (current.routing_config && isPlainObject(current.routing_config)) {
    routingConfig.value = {
      enabled: !!current.routing_config.enabled,
      department_field: current.routing_config.department_field || 'department',
      fallback_to_default: current.routing_config.fallback_to_default !== false,
      mappings: Array.isArray(current.routing_config.mappings) ? current.routing_config.mappings : [],
    }
  }
}

watch(() => form.value.anonymousMode, (enabled) => {
  applyAnonymousModeToFields(enabled)
})

watch(formFields, () => {
  if (!form.value.anonymousMode) return
  const hasIdentityEnabled = formFields.value.some((field) => isIdentityField(field) && field.enabled)
  if (hasIdentityEnabled) {
    applyAnonymousModeToFields(true)
  }
}, { deep: true })

// 监听配置变化，自动保存
watch([form, formFields, pageTexts, routingConfig], () => {
  saveConfig()
}, { deep: true })

// ===== 生命周期 =====
onMounted(() => {
  loadAllQuestionnaires()

  if (isEditMode.value || isCloneMode.value) {
    applyAssessmentToForm()
  } else {
    pageTexts.value = buildDefaultPageTexts()
    // V45: 先加载上次保存的配置
    loadConfig()

    // 然后设置默认名称
    if (props.questionnaire) {
      form.value.name = `${props.questionnaire.name} - ${new Date().toLocaleDateString()}`
    }
  }
})
</script>

<template src="./DistributeModal.template.html"></template>


<style scoped>
@import './styles/distribute-modal.css';
</style>
