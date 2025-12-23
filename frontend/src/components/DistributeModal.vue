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
  type Questionnaire,
  type AssessmentCreate,
  type FormField,
  type PageTexts,
} from '../api/assessments'
import FieldConfigPanel from './FieldConfigPanel.vue'

// ===== Props =====
const props = defineProps<{
  questionnaire: Questionnaire | null
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
  description: '',
})

// 页面文案
const pageTexts = ref<PageTexts>({
  welcomeText: '欢迎参加本次测评',
  introText: '本测评旨在了解您的职业特质，帮助我们更好地为您匹配适合的岗位。',
  guideText: '请在安静的环境下完成，按照第一反应作答，没有对错之分。',
  privacyText: '您的信息将被严格保密，仅用于招聘评估目的。',
  successTitle: '测评完成！',
  successMessage: '感谢您认真完成本次测评，您的回答对我们非常重要。',
  resultText: '我们将在 1-3 个工作日内完成评估分析。',
  contactText: '届时会通过您留下的联系方式通知您，请保持电话畅通。',
})

// 表单字段 - V45: 保留姓名、手机号、性别、应聘岗位，移除邮箱
const formFields = ref<FormField[]>([
  { id: 'name', name: 'name', label: '姓名', type: 'text', placeholder: '请输入您的姓名', required: true, enabled: true, builtin: true },
  { id: 'phone', name: 'phone', label: '手机号', type: 'tel', placeholder: '请输入手机号', required: true, enabled: true, builtin: true },
  { id: 'gender', name: 'gender', label: '性别', type: 'select', placeholder: '请选择性别', required: false, enabled: true, builtin: true, options: [{ value: '男', label: '男' }, { value: '女', label: '女' }] },
  { id: 'target_position', name: 'target_position', label: '应聘岗位', type: 'text', placeholder: '请输入应聘岗位', required: false, enabled: true, builtin: true },
])

// 页面文案编辑类型
const pageEditType = ref<'entry' | 'success'>('entry')

// ===== 计算属性 =====
const enabledFields = computed(() => formFields.value.filter(f => f.enabled))

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

const validFrom = computed(() => formatLocalDateTime(new Date()))

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
      allow_repeat: form.value.allowRepeat,
      repeat_check_by: form.value.repeatCheckBy,
      repeat_interval_hours: form.value.repeatIntervalHours,
      max_submissions: form.value.maxSubmissions,
    }
    
    const result = await createAssessment(data)
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
    console.error('分发失败:', error)
    alert('分发失败，请重试')
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
  link.download = `${props.questionnaire?.name || '测评'}_二维码.png`
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
const STORAGE_KEY = 'distribute_config'

// 保存配置到 localStorage
const saveConfig = () => {
  const config = {
    form: {
      validityType: form.value.validityType,
      expiryDays: form.value.expiryDays,
      allowRepeat: form.value.allowRepeat,
      repeatCheckBy: form.value.repeatCheckBy,
      repeatIntervalHours: form.value.repeatIntervalHours,
      maxSubmissions: form.value.maxSubmissions,
    },
    formFields: formFields.value,
    pageTexts: pageTexts.value,
  }
  localStorage.setItem(STORAGE_KEY, JSON.stringify(config))
}

// 从 localStorage 加载配置
const loadConfig = () => {
  try {
    const saved = localStorage.getItem(STORAGE_KEY)
    if (saved) {
      const config = JSON.parse(saved)
      // 恢复表单配置
      if (config.form) {
        form.value.validityType = config.form.validityType || 'temporary'
        form.value.expiryDays = config.form.expiryDays || 7
        form.value.allowRepeat = config.form.allowRepeat || false
        form.value.repeatCheckBy = config.form.repeatCheckBy || 'phone'
        form.value.repeatIntervalHours = config.form.repeatIntervalHours || 24
        form.value.maxSubmissions = config.form.maxSubmissions || 0
      }
      // 恢复字段配置
      if (config.formFields && Array.isArray(config.formFields)) {
        formFields.value = config.formFields
      }
      // 恢复页面文案
      if (config.pageTexts) {
        pageTexts.value = { ...pageTexts.value, ...config.pageTexts }
      }
    }
  } catch (e) {
    console.warn('加载分发配置失败:', e)
  }
}

// 监听配置变化，自动保存
watch([form, formFields, pageTexts], () => {
  saveConfig()
}, { deep: true })

// ===== 生命周期 =====
onMounted(() => {
  // V45: 先加载上次保存的配置
  loadConfig()
  
  // 然后设置默认名称
  if (props.questionnaire) {
    form.value.name = `${props.questionnaire.name} - ${new Date().toLocaleDateString()}`
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
        <h3>分发成功</h3>
      </div>

      <!-- 内容区域 -->
      <div class="modal-body">
        <!-- 步骤1：基本设置 -->
        <div v-if="currentStep === 1" class="step-content">
          <div class="form-group">
            <label>测评名称 <span class="required">*</span></label>
            <input 
              type="text" 
              v-model="form.name" 
              class="form-input" 
              placeholder="例如：2024春季校招EPQ测评"
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

          <div class="form-group repeat-settings">
            <label><i class="ri-repeat-2-line"></i> 重复提交设置</label>
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
          </div>

          <div class="form-group">
            <label>测评说明（选填）</label>
            <textarea 
              v-model="form.description" 
              class="form-textarea" 
              rows="3"
              placeholder="请输入测评说明..."
            ></textarea>
          </div>
        </div>

        <!-- 步骤2：字段配置（左右分栏布局） -->
        <div v-if="currentStep === 2" class="step-content step-fields-config">
          <!-- 左侧：字段列表（使用公共组件） -->
          <FieldConfigPanel v-model="formFields" />

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
                  <h5>{{ form.name || '测评名称' }}</h5>
            </div>
            
            <div class="preview-form">
              <p class="preview-hint">请填写您的基本信息</p>
                  
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
                      <span>开始测评</span>
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
                    placeholder="欢迎参加本次测评"
                    maxlength="30"
                  />
                <span class="char-count">{{ pageTexts.welcomeText?.length || 0 }}/30</span>
              </div>
              <div class="form-item">
                <label><i class="ri-file-info-line"></i> 测评说明</label>
                  <textarea 
                    v-model="pageTexts.introText"
                    placeholder="本测评旨在了解您的职业特质，帮助我们更好地为您匹配适合的岗位。"
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
            </div>
            
              <!-- 完成页面配置 -->
            <div v-if="pageEditType === 'success'" class="edit-form">
              <div class="form-item">
                <label><i class="ri-trophy-line"></i> 成功标题</label>
                  <input 
                    type="text"
                    v-model="pageTexts.successTitle"
                    placeholder="测评完成！"
                    maxlength="20"
                  />
                <span class="char-count">{{ pageTexts.successTitle?.length || 0 }}/20</span>
              </div>
              <div class="form-item">
                <label><i class="ri-heart-line"></i> 感谢语</label>
                  <textarea 
                    v-model="pageTexts.successMessage"
                    placeholder="感谢您认真完成本次测评，您的回答对我们非常重要。"
                    rows="2"
                    maxlength="60"
                  ></textarea>
                <span class="char-count">{{ pageTexts.successMessage?.length || 0 }}/60</span>
              </div>
              <div class="form-item">
                <label><i class="ri-calendar-check-line"></i> 结果说明</label>
                  <textarea 
                    v-model="pageTexts.resultText"
                    placeholder="我们将在 1-3 个工作日内完成评估分析。"
                    rows="2"
                    maxlength="60"
                  ></textarea>
                <span class="char-count">{{ pageTexts.resultText?.length || 0 }}/60</span>
              </div>
              <div class="form-item">
                <label><i class="ri-phone-line"></i> 联系提示</label>
                  <textarea 
                    v-model="pageTexts.contactText"
                    placeholder="届时会通过您留下的联系方式通知您，请保持电话畅通。"
                    rows="2"
                    maxlength="60"
                  ></textarea>
                <span class="char-count">{{ pageTexts.contactText?.length || 0 }}/60</span>
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
                          <h3>{{ form.name || '测评名称' }}</h3>
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
                          <div class="form-title">请填写您的基本信息</div>
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
                          开始测评
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
                        <h2>{{ pageTexts.successTitle || '测评完成！' }}</h2>
                        <p class="success-msg">{{ pageTexts.successMessage || '感谢您完成本次测评' }}</p>
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
                      
                      <!-- 后续提示 -->
                      <div class="next-steps">
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
            <div class="confirm-label">测评名称</div>
            <div class="confirm-value">{{ form.name }}</div>
          </div>

          <div class="confirm-item">
            <div class="confirm-label">问卷类型</div>
            <div class="confirm-value">
              {{ questionnaire?.name }} ({{ questionnaire?.questions_count }}题)
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
            <h4><i class="ri-link"></i> 测评链接</h4>
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
              <img :src="qrcodeDataURL" alt="测评二维码" />
              <p>扫码开始测评</p>
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
          {{ loading ? '生成中...' : '确认分发' }}
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
