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
  repeatCheckBy: 'phone' as 'phone' | 'phone_name',
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

const getFieldKey = (field: FormField) => String(field.name || field.id || '').trim()

const isIdentityField = (field: FormField) => identityFieldNames.has(getFieldKey(field))

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

const isPlainObject = (value: unknown): value is Record<string, any> => {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}

// 保存配置到 localStorage
const saveConfig = () => {
  try {
    const config = {
      form: {
        validityType: form.value.validityType,
        expiryDays: form.value.expiryDays,
        allowRepeat: form.value.allowRepeat,
        repeatCheckBy: form.value.repeatCheckBy,
        repeatIntervalHours: form.value.repeatIntervalHours,
        maxSubmissions: form.value.maxSubmissions,
        anonymousMode: form.value.anonymousMode,
      },
      formFields: formFields.value,
      pageTexts: pageTexts.value,
      routingConfig: routingConfig.value,
    }
    localStorage.setItem(storageKey.value, JSON.stringify(config))
  } catch (e) {
    console.warn('保存分发配置失败:', e)
  }
}

// 从 localStorage 加载配置
const loadConfig = () => {
  try {
    const saved = localStorage.getItem(storageKey.value)
    if (saved) {
      const config = JSON.parse(saved)
      // 恢复表单配置
      if (isPlainObject(config.form)) {
        form.value.validityType = config.form.validityType || 'temporary'
        form.value.expiryDays = config.form.expiryDays || 7
        form.value.allowRepeat = config.form.allowRepeat || false
        form.value.repeatCheckBy = config.form.repeatCheckBy || 'phone'
        form.value.repeatIntervalHours = config.form.repeatIntervalHours || 24
        form.value.maxSubmissions = config.form.maxSubmissions || 0
        form.value.anonymousMode = !!config.form.anonymousMode
      }
      // 恢复字段配置
      if (config.formFields && Array.isArray(config.formFields)) {
        formFields.value = config.formFields
      }
      // 恢复页面文案
      if (isPlainObject(config.pageTexts)) {
        pageTexts.value = { ...pageTexts.value, ...config.pageTexts }
      }
      if (isPlainObject(config.routingConfig)) {
        routingConfig.value = {
          enabled: !!config.routingConfig.enabled,
          department_field: config.routingConfig.department_field || 'department',
          fallback_to_default: config.routingConfig.fallback_to_default !== false,
          mappings: Array.isArray(config.routingConfig.mappings) ? config.routingConfig.mappings : [],
        }
      }
    }
  } catch (e) {
    console.warn('加载分发配置失败:', e)
  }
}

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
  form.value.repeatCheckBy = (current.repeat_check_by as 'phone' | 'phone_name') || 'phone'
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

<template>
  <div class="modal-overlay" @click="close">
    <div class="modal-dialog modal-distribute" @click.stop>
      <!-- 顶部区域：问卷信息 + 关闭按钮 -->
      <div class="distribute-header">
        <div class="distribute-questionnaire-info">
          <span class="questionnaire-type-tag">{{ questionnaire?.type }}</span>
          <span class="questionnaire-name">{{ questionnaire?.name }}</span>
          <span class="mode-chip">{{ modeTitle }}</span>
        </div>
        <button class="btn-close-float" @click="close">
          <i class="ri-close-line"></i>
        </button>
      </div>

      <!-- 步骤指示器 -->
      <div v-if="currentStep <= 4" class="steps-indicator">
        <div :class="['step', { active: currentStep === 1, completed: currentStep > 1 }]">
          <div class="step-number">1</div>
          <div class="step-label">基本设置</div>
          </div>
        <div class="step-line" :class="{ completed: currentStep > 1 }"></div>
        <div :class="['step', { active: currentStep === 2, completed: currentStep > 2 }]">
          <div class="step-number">2</div>
          <div class="step-label">字段配置</div>
        </div>
        <div class="step-line" :class="{ completed: currentStep > 2 }"></div>
        <div :class="['step', { active: currentStep === 3, completed: currentStep > 3 }]">
          <div class="step-number">3</div>
          <div class="step-label">页面文案</div>
        </div>
        <div class="step-line" :class="{ completed: currentStep > 3 }"></div>
        <div :class="['step', { active: currentStep === 4, completed: currentStep > 4 }]">
          <div class="step-number">4</div>
          <div class="step-label">确认分发</div>
        </div>
      </div>

      <!-- 成功状态的header -->
      <div v-if="currentStep === 5" class="distribute-success-header">
        <div class="success-icon-wrapper">
          <i class="ri-checkbox-circle-fill"></i>
        </div>
        <h3>{{ isEditMode ? '保存成功，原链接不变' : '新链接生成成功' }}</h3>
      </div>

      <!-- 内容区域 -->
      <div class="modal-body">
        <!-- 步骤1：基本设置 -->
        <div v-if="currentStep === 1" class="step-content">
          <div class="mode-notice">
            <i :class="isEditMode ? 'ri-link-m' : (isCloneMode ? 'ri-file-copy-line' : 'ri-links-line')"></i>
            <span>{{ modeTip }}</span>
          </div>

          <div class="form-group">
            <label>{{ copy.titleLabel }} <span class="required">*</span></label>
            <input 
              type="text" 
              v-model="form.name" 
              class="form-input" 
              :placeholder="copy.namePlaceholder"
            />
          </div>

          <div class="form-group">
            <label>有效期类型 <span class="required">*</span></label>
            <div class="validity-options">
              <div 
                :class="['validity-option', { active: form.validityType === 'permanent' }]"
                @click="form.validityType = 'permanent'"
              >
                <i class="ri-infinity-line"></i>
                <div class="option-content">
                  <span class="option-title">长期有效</span>
                  <span class="option-desc">适合前台固定二维码</span>
                </div>
              </div>
              <div 
                :class="['validity-option', { active: form.validityType === 'temporary' }]"
                @click="form.validityType = 'temporary'"
              >
                <i class="ri-timer-line"></i>
                <div class="option-content">
                  <span class="option-title">短期有效</span>
                  <span class="option-desc">适合线上发送给特定人</span>
                </div>
              </div>
            </div>
          </div>

          <div v-if="form.validityType === 'temporary'" class="form-group">
            <label>有效时长</label>
            <div class="expiry-options">
              <button 
                v-for="opt in expiryOptions" 
                :key="opt.value"
                :class="['expiry-btn', { active: form.expiryDays === opt.value }]"
                @click="form.expiryDays = opt.value"
                type="button"
              >
                {{ opt.label }}
              </button>
            </div>
            <div v-if="form.expiryDays === -1" class="custom-expiry">
              <input 
                type="datetime-local" 
                v-model="form.customExpiryDate" 
                class="form-input"
              />
            </div>
          </div>

          <div v-if="form.validityType === 'permanent'" class="validity-tip">
            <i class="ri-information-line"></i>
            <span>长期有效的二维码不会过期，适合放在公司前台供面试者随时扫码填写</span>
          </div>

          <div class="form-group anonymous-settings">
            <label><i class="ri-shield-user-line"></i> 匿名设置</label>
            <div class="setting-row">
              <div class="setting-text">
                <span class="setting-label">匿名收集（同设备防重复）</span>
                <span class="setting-desc">开启后不收集姓名和手机号，使用浏览器设备标识限制重复提交</span>
              </div>
              <label class="toggle-switch">
                <input type="checkbox" v-model="form.anonymousMode" />
                <span class="toggle-slider"></span>
              </label>
            </div>
            <div v-if="form.anonymousMode" class="anonymous-mode-hint">
              <i class="ri-information-line"></i>
              <span>轻量防重复可以拦截同一浏览器再次提交，但清除缓存、换浏览器或换设备仍可能绕过。</span>
            </div>
          </div>

          <div class="form-group repeat-settings" :class="{ 'is-disabled': form.anonymousMode }">
            <label><i class="ri-repeat-2-line"></i> 重复提交设置</label>
            <div v-if="form.anonymousMode" class="no-repeat-hint anonymous-repeat-hint">
              <i class="ri-lock-line"></i>
              <span>匿名模式使用同设备防重复，不再使用姓名/手机号校验。</span>
            </div>
            <template v-else>
              <div class="setting-row">
                <span class="setting-label">允许同一人重复提交</span>
                <label class="toggle-switch">
                  <input type="checkbox" v-model="form.allowRepeat" />
                  <span class="toggle-slider"></span>
                </label>
              </div>
              
              <div v-if="form.allowRepeat" class="repeat-detail">
                <div class="setting-row">
                  <span class="setting-label">判断依据</span>
                  <div class="radio-group">
                    <label class="radio-item">
                      <input type="radio" v-model="form.repeatCheckBy" value="phone" />
                      <span>手机号</span>
                    </label>
                    <label class="radio-item">
                      <input type="radio" v-model="form.repeatCheckBy" value="phone_name" />
                      <span>手机号+姓名</span>
                    </label>
                  </div>
                </div>
                
                <div class="setting-row">
                  <span class="setting-label">提交间隔</span>
                  <div class="interval-options">
                    <button 
                      v-for="opt in repeatIntervalOptions" 
                      :key="opt.value"
                      type="button"
                      :class="['interval-btn', { active: form.repeatIntervalHours === opt.value }]"
                      @click="form.repeatIntervalHours = opt.value"
                    >
                      {{ opt.label }}
                    </button>
                  </div>
                </div>
                
                <div class="setting-row">
                  <span class="setting-label">最多提交次数</span>
                  <div class="max-input">
                    <input 
                      type="number" 
                      v-model="form.maxSubmissions" 
                      min="0" 
                      class="form-input small" 
                    />
                    <span class="input-hint">0 表示不限制</span>
                  </div>
                </div>
              </div>
              
              <div v-else class="no-repeat-hint">
                <i class="ri-information-line"></i>
                <span>每人只能提交一次，系统将根据手机号识别重复</span>
              </div>
            </template>
          </div>

          <div class="form-group">
            <label>{{ copy.descriptionLabel }}（选填）</label>
            <textarea 
              v-model="form.description" 
              class="form-textarea" 
              rows="3"
              :placeholder="copy.descriptionPlaceholder"
            ></textarea>
          </div>
        </div>

        <!-- 步骤2：字段配置（左右分栏布局） -->
        <div v-if="currentStep === 2" class="step-content step-fields-config">
          <div class="fields-left-column">
            <!-- 左侧：字段列表（使用公共组件） -->
            <FieldConfigPanel v-model="formFields" />

            <div class="routing-config-card">
              <div class="routing-header">
                <div class="routing-title">
                  <i class="ri-route-line"></i>
                  <span>部门路由分发</span>
                </div>
                <label class="toggle-switch">
                  <input type="checkbox" v-model="routingConfig.enabled" />
                  <span class="toggle-slider"></span>
                </label>
              </div>

              <div class="routing-content">
                <div v-if="!departmentField" class="routing-missing">
                  <i class="ri-information-line"></i>
                  <span>未检测到部门下拉字段（name = department）</span>
                  <button type="button" class="btn-add-department" @click="addDepartmentField">一键添加部门字段</button>
                </div>

                <template v-else>
                  <p class="routing-tip">员工在入口页选择部门后，将自动进入映射的目标问卷。未配置部门会回退当前问卷。</p>
                  <div v-if="routingConfig.enabled" class="routing-mappings">
                    <div class="mapping-head">
                      <span>部门</span>
                      <span>目标问卷</span>
                    </div>
                    <div
                      v-for="(mapping, index) in routingConfig.mappings"
                      :key="index"
                      class="mapping-row"
                    >
                      <select v-model="mapping.department_value" class="mapping-select">
                        <option value="">请选择部门</option>
                        <option v-for="opt in departmentOptions" :key="opt" :value="opt">{{ opt }}</option>
                      </select>
                      <select v-model.number="mapping.questionnaire_id" class="mapping-select">
                        <option :value="0">请选择问卷</option>
                        <option
                          v-for="q in availableTargetQuestionnaires"
                          :key="q.id"
                          :value="q.id"
                        >
                          {{ q.name }}（{{ q.type }}）
                        </option>
                      </select>
                      <button type="button" class="btn-remove-mapping" @click="removeRoutingMapping(index)">
                        <i class="ri-delete-bin-line"></i>
                      </button>
                    </div>
                    <button type="button" class="btn-add-mapping" @click="addRoutingMapping">
                      <i class="ri-add-line"></i>
                      添加映射
                    </button>
                  </div>
                </template>
              </div>
            </div>
          </div>

          <!-- 右侧：实时预览 -->
          <div class="preview-panel">
            <div class="panel-header">
              <h4><i class="ri-smartphone-line"></i> 候选人表单预览</h4>
            </div>
            
            <div class="preview-device">
              <div class="preview-screen">
                <div class="preview-header-bar">
                  <div class="preview-logo">
                    <i class="ri-file-list-3-fill"></i>
                </div>
                  <h5>{{ form.name || copy.nameFallback }}</h5>
            </div>
            
            <div class="preview-form">
              <p v-if="pageTexts.showBasicInfoTitle !== false" class="preview-hint">请填写您的基本信息</p>
                  
              <div 
                v-for="field in enabledFields" 
                :key="field.id"
                class="preview-field"
              >
                    <label class="preview-label">
                  <i :class="getFieldIcon(field)"></i>
                  {{ field.label }}
                  <span v-if="field.required" class="preview-required">*</span>
                </label>
                <input 
                  :type="field.type"
                      :placeholder="field.placeholder || `请输入${field.label}`"
                  class="preview-input"
                  disabled
                />
              </div>
                  
                  <div class="preview-submit">
              <button class="preview-btn" disabled>
                      <span>{{ copy.startAction }}</span>
                      <i class="ri-arrow-right-line"></i>
              </button>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- 步骤3：页面文案配置 -->
        <div v-if="currentStep === 3" class="step-content step-page-texts">
          <!-- 左侧：文案编辑 -->
          <div class="texts-edit-panel">
            <!-- Tab切换 -->
            <div class="edit-tabs">
              <button 
                :class="['edit-tab', { active: pageEditType === 'entry' }]"
                @click="pageEditType = 'entry'"
              >
                <i class="ri-door-open-line"></i>
                <span>入口页文案</span>
              </button>
              <button 
                :class="['edit-tab', { active: pageEditType === 'success' }]"
                @click="pageEditType = 'success'"
              >
                <i class="ri-checkbox-circle-line"></i>
                <span>完成页文案</span>
              </button>
            </div>
            
            <!-- 文案表单 -->
            <div class="texts-edit-scroll">
              <!-- 入口页面配置 -->
            <div v-if="pageEditType === 'entry'" class="edit-form">
              <div class="form-item">
                <label><i class="ri-hand-heart-line"></i> 欢迎语</label>
                  <input 
                    type="text"
                    v-model="pageTexts.welcomeText"
                    :placeholder="copy.pageTexts.welcomeText"
                    maxlength="30"
                  />
                <span class="char-count">{{ pageTexts.welcomeText?.length || 0 }}/30</span>
              </div>
              <div class="form-item">
                <label><i class="ri-file-info-line"></i> {{ copy.descriptionLabel }}</label>
                  <textarea 
                    v-model="pageTexts.introText"
                    :placeholder="copy.pageTexts.introText"
                    rows="2"
                    maxlength="100"
                  ></textarea>
                <span class="char-count">{{ pageTexts.introText?.length || 0 }}/100</span>
              </div>
              <div class="form-item">
                <label><i class="ri-compass-3-line"></i> 答题指导</label>
                  <textarea 
                    v-model="pageTexts.guideText"
                    placeholder="请在安静的环境下完成，按照第一反应作答，没有对错之分。"
                    rows="2"
                    maxlength="80"
                  ></textarea>
                <span class="char-count">{{ pageTexts.guideText?.length || 0 }}/80</span>
              </div>
              <div class="form-item">
                <label><i class="ri-shield-check-line"></i> 隐私声明</label>
                  <textarea 
                    v-model="pageTexts.privacyText"
                    placeholder="您的信息将被严格保密，仅用于招聘评估目的，不会向第三方泄露。"
                    rows="2"
                    maxlength="80"
                  ></textarea>
                <span class="char-count">{{ pageTexts.privacyText?.length || 0 }}/80</span>
              </div>
              <div class="form-item-group">
                <div class="group-header">
                  <label><i class="ri-information-line"></i> 基本信息提示</label>
                  <div class="toggle-switch" @click="pageTexts.showBasicInfoTitle = !pageTexts.showBasicInfoTitle">
                    <div :class="['toggle-track', { active: pageTexts.showBasicInfoTitle }]">
                      <div class="toggle-thumb"></div>
                    </div>
                    <span class="toggle-label">{{ pageTexts.showBasicInfoTitle ? '显示' : '隐藏' }}</span>
                  </div>
                </div>
              </div>
            </div>
            
              <!-- 完成页面配置 -->
            <div v-if="pageEditType === 'success'" class="edit-form">
              <div class="form-item">
                <label><i class="ri-trophy-line"></i> 成功标题</label>
                  <input 
                    type="text"
                    v-model="pageTexts.successTitle"
                    :placeholder="copy.pageTexts.successTitle"
                    maxlength="20"
                  />
                <span class="char-count">{{ pageTexts.successTitle?.length || 0 }}/20</span>
              </div>
              <div class="form-item">
                <label><i class="ri-heart-line"></i> 感谢语</label>
                  <textarea 
                    v-model="pageTexts.successMessage"
                    :placeholder="copy.pageTexts.successMessage"
                    rows="2"
                    maxlength="60"
                  ></textarea>
                <span class="char-count">{{ pageTexts.successMessage?.length || 0 }}/60</span>
              </div>
              
              <!-- "接下来"区域配置 - 带开关 -->
              <div class="form-item-group">
                <div class="group-header">
                  <label><i class="ri-information-line"></i> 接下来</label>
                  <div class="toggle-switch" @click="pageTexts.showNextSteps = !pageTexts.showNextSteps">
                    <div :class="['toggle-track', { active: pageTexts.showNextSteps }]">
                      <div class="toggle-thumb"></div>
                    </div>
                    <span class="toggle-label">{{ pageTexts.showNextSteps ? '显示' : '隐藏' }}</span>
                  </div>
                </div>
                
                <template v-if="pageTexts.showNextSteps">
                  <div class="form-item sub-item">
                    <label><i class="ri-calendar-check-line"></i> 结果说明</label>
                    <textarea 
                      v-model="pageTexts.resultText"
                      :placeholder="copy.pageTexts.resultText"
                      rows="2"
                      maxlength="60"
                    ></textarea>
                    <span class="char-count">{{ pageTexts.resultText?.length || 0 }}/60</span>
                  </div>
                  <div class="form-item sub-item">
                    <label><i class="ri-phone-line"></i> 联系提示</label>
                    <textarea 
                      v-model="pageTexts.contactText"
                      :placeholder="copy.pageTexts.contactText"
                      rows="2"
                      maxlength="60"
                    ></textarea>
                    <span class="char-count">{{ pageTexts.contactText?.length || 0 }}/60</span>
                  </div>
                </template>
              </div>
            </div>
            </div>
          </div>
          
          <!-- 右侧：页面预览 -->
          <div class="texts-preview-panel">
            <div class="preview-header">
              <div class="preview-title">
                <i class="ri-smartphone-line"></i>
                <span>{{ pageEditType === 'entry' ? '入口页预览' : '完成页预览' }}</span>
              </div>
            </div>
            
            <div class="preview-body">
              <!-- 入口页预览 -->
              <div v-if="pageEditType === 'entry'" class="phone-mockup">
                <div class="phone-frame">
                  <div class="phone-speaker"></div>
                  <div class="phone-screen">
                    <div class="screen-content entry-screen">
                      <!-- 顶部渐变背景 -->
                      <div class="entry-top-bg">
                        <div class="brand-area">
                          <div class="brand-icon"><i class="ri-file-list-3-fill"></i></div>
                          <div class="brand-name">TalentLens</div>
                          <div class="brand-slogan">人才初步画像智能工具</div>
                        </div>
                      </div>
                      
                      <!-- 测评卡片 -->
                      <div class="entry-main-card">
                        <div class="assessment-info">
                          <div class="info-icon"><i class="ri-file-text-fill"></i></div>
                          <h3>{{ form.name || copy.nameFallback }}</h3>
                          <div class="info-meta">
                            <span><i class="ri-file-list-line"></i> {{ questionnaire?.questions_count || 0 }} 题</span>
                            <span><i class="ri-time-line"></i> 约 {{ questionnaire?.estimated_minutes || 15 }} 分钟</span>
                          </div>
                        </div>
                        
                        <!-- 欢迎语 -->
                        <div v-if="pageTexts.welcomeText" class="welcome-text">
                          {{ pageTexts.welcomeText }}
                        </div>
                        
                        <!-- 说明区域 -->
                        <div class="info-boxes">
                          <div v-if="pageTexts.introText" class="info-box intro">
                            <i class="ri-lightbulb-line"></i>
                            <span>{{ pageTexts.introText }}</span>
                          </div>
                          <div v-if="pageTexts.guideText" class="info-box guide">
                            <i class="ri-compass-3-line"></i>
                            <span>{{ pageTexts.guideText }}</span>
                          </div>
                          <div v-if="pageTexts.privacyText" class="info-box privacy">
                            <i class="ri-shield-check-line"></i>
                            <span>{{ pageTexts.privacyText }}</span>
                          </div>
                        </div>
                        
                        <!-- 表单区域 -->
                        <div class="form-area">
                          <div v-if="pageTexts.showBasicInfoTitle !== false" class="form-title">请填写您的基本信息</div>
                          <div class="form-fields">
                            <div class="field-row" v-for="f in enabledFields.slice(0, 2)" :key="f.id">
                              <span class="field-label">{{ f.label }}</span>
                              <div class="field-input"></div>
                            </div>
                            <div v-if="enabledFields.length > 2" class="more-hint">
                              还有 {{ enabledFields.length - 2 }} 个字段...
                            </div>
                          </div>
                        </div>
                        
                        <button class="start-btn">
                          <i class="ri-play-circle-fill"></i>
                          {{ copy.startAction }}
                        </button>
                      </div>
                    </div>
                  </div>
                  <div class="phone-home-bar"></div>
                </div>
              </div>
              
              <!-- 完成页预览 -->
              <div v-if="pageEditType === 'success'" class="phone-mockup">
                <div class="phone-frame">
                  <div class="phone-speaker"></div>
                  <div class="phone-screen">
                    <div class="screen-content success-screen">
                      <!-- 成功动画区域 -->
                      <div class="success-hero">
                        <div class="success-circle">
                          <i class="ri-checkbox-circle-fill"></i>
                        </div>
                        <h2>{{ pageTexts.successTitle || copy.pageTexts.successTitle }}</h2>
                        <p class="success-msg">{{ pageTexts.successMessage || copy.pageTexts.successMessage }}</p>
                      </div>
                      
                      <!-- 提交信息卡片 -->
                      <div class="result-card">
                        <div class="result-row">
                          <i class="ri-file-list-line"></i>
                          <div class="result-info">
                            <span class="result-label">提交编号</span>
                            <span class="result-value">SUB20251202001</span>
                          </div>
                        </div>
                        <div class="result-row">
                          <i class="ri-time-line"></i>
                          <div class="result-info">
                            <span class="result-label">提交时间</span>
                            <span class="result-value">{{ new Date().toLocaleString('zh-CN', { month: 'numeric', day: 'numeric', hour: '2-digit', minute: '2-digit' }) }}</span>
                          </div>
                        </div>
                      </div>
                      
                      <!-- 后续提示 - 根据开关显示/隐藏 -->
                      <div v-if="pageTexts.showNextSteps" class="next-steps">
                        <div class="steps-title"><i class="ri-information-line"></i> 接下来</div>
                        <p v-if="pageTexts.resultText">{{ pageTexts.resultText }}</p>
                        <p v-if="pageTexts.contactText">{{ pageTexts.contactText }}</p>
                      </div>
                      
                      <button class="close-btn">
                        <i class="ri-close-line"></i>
                        关闭页面
                      </button>
                    </div>
                  </div>
                  <div class="phone-home-bar"></div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- 步骤4：确认分发 -->
        <div v-if="currentStep === 4" class="step-content step-confirm">
          <h4 class="confirm-title">请确认以下信息</h4>
          
          <div class="confirm-item">
            <div class="confirm-label">{{ copy.titleLabel }}</div>
            <div class="confirm-value">{{ form.name }}</div>
          </div>

          <div class="confirm-item">
            <div class="confirm-label">问卷类型</div>
            <div class="confirm-value">
              {{ questionnaire?.name }}
            </div>
          </div>

          <div class="confirm-item">
            <div class="confirm-label">有效期</div>
            <div class="confirm-value">
              {{ form.validityType === 'permanent' ? '长期有效' : 
                 `${new Date(validFrom).toLocaleDateString()} 至 ${new Date(validUntil).toLocaleDateString()}` }}
            </div>
          </div>

          <div class="confirm-item">
            <div class="confirm-label">候选人字段 ({{ enabledFields.length }}个)</div>
            <div class="confirm-value">
              <div class="fields-tags">
                <span 
                  v-for="field in enabledFields" 
                  :key="field.id"
                  class="field-tag"
                >
                  <i :class="getFieldIcon(field)"></i>
                  {{ field.label }}
                  <span v-if="field.required" class="text-red">(必填)</span>
                </span>
              </div>
            </div>
          </div>
        </div>

        <!-- 步骤5：分发结果 -->
        <div v-if="currentStep === 5" class="step-content step-result">
          <div class="result-section">
            <h4><i class="ri-link"></i> {{ copy.linkLabel }}</h4>
            <div class="link-box">
              <input type="text" :value="generatedLink" readonly />
              <button class="btn-copy" @click="copyLink">
                <i class="ri-file-copy-line"></i>
                {{ showLinkCopied ? '已复制' : '复制' }}
              </button>
            </div>
          </div>

          <div class="result-section">
            <h4><i class="ri-qr-code-line"></i> 二维码</h4>
            <div v-if="qrcodeDataURL" class="qr-container">
              <img :src="qrcodeDataURL" :alt="copy.qrAlt" />
              <p>{{ copy.qrHint }}</p>
              <button class="btn-download" @click="downloadQRCode">
                <i class="ri-download-line"></i>
                下载二维码
              </button>
            </div>
            <div v-else class="qr-loading">
              <i class="ri-loader-4-line spin"></i>
              <p>生成中...</p>
            </div>
          </div>

          <div class="result-stats">
            <div class="stat-item">
              <i class="ri-user-line"></i>
              <span>已提交：0 人</span>
            </div>
            <div class="stat-item">
              <i class="ri-calendar-line"></i>
              <span>有效期至：{{ form.validityType === 'permanent' ? '长期有效' : new Date(validUntil).toLocaleDateString() }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- 底部按钮 -->
      <div class="modal-footer">
        <button 
          v-if="currentStep === 1" 
          class="btn-cancel" 
          @click="close"
        >
          取消
        </button>
        
        <button 
          v-if="currentStep > 1 && currentStep <= 4" 
          class="btn-cancel" 
          @click="prevStep"
        >
          <i class="ri-arrow-left-line"></i>
          上一步
        </button>
        
        <button 
          v-if="currentStep === 5" 
          class="btn-cancel" 
          @click="close"
        >
          关闭
        </button>
        
        <button 
          v-if="currentStep < 4" 
          class="btn-confirm" 
          @click="nextStep"
          :disabled="currentStep === 1 && !form.name"
        >
          下一步
          <i class="ri-arrow-right-line"></i>
        </button>
        
        <button 
          v-if="currentStep === 4" 
          class="btn-confirm" 
          @click="handleDistribute"
          :disabled="loading"
        >
          <i v-if="loading" class="ri-loader-4-line animate-spin"></i>
          {{ loading ? (isEditMode ? '保存中...' : '生成中...') : (isEditMode ? '确认保存' : (isCloneMode ? '确认生成新链接' : '确认分发')) }}
        </button>
        
        <button 
          v-if="currentStep === 5" 
          class="btn-confirm" 
          @click="emit('success')"
        >
          完成
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
@import './styles/distribute-modal.css';
</style>
