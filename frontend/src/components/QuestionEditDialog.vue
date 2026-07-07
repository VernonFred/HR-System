<script lang="ts">
/**
 * 题目编辑弹窗组件
 *
 * 功能：
 * 1. 创建新题目
 * 2. 编辑现有题目
 * 3. 支持多种题型（单选、多选、文本、量表等）
 */

// ===== 类型定义（需要导出供其他组件使用） =====
export interface EditorQuestion {
  id: string
  type: 'radio' | 'checkbox' | 'text' | 'textarea' | 'scale' | 'yesno' | 'choice'
  text: string
  required: boolean
  options?: { label: string; value: string; score?: number; allowCustom?: boolean; placeholder?: string }[]
  selectionRule?: 'none' | 'max' | 'min' | 'exact' | 'range' | null
  minSelections?: number | null
  maxSelections?: number | null
  scale?: { min: number; max: number; minLabel: string; maxLabel: string }
  optionA?: string
  optionB?: string
  scoreA?: number
  scoreB?: number
  // 专业测评特有字段
  dimension?: string  // 所属维度 (E/I, S/N, T/F, J/P, D/I/S/C, E/N/P/L)
  positive?: boolean  // 是否正向计分
}

// 专业测评维度配置
export const ASSESSMENT_DIMENSIONS = {
  MBTI: [
    { value: 'EI', label: 'E/I 外向/内向' },
    { value: 'SN', label: 'S/N 感觉/直觉' },
    { value: 'TF', label: 'T/F 思考/情感' },
    { value: 'JP', label: 'J/P 判断/感知' },
  ],
  DISC: [
    { value: 'D', label: 'D 支配型' },
    { value: 'I', label: 'I 影响型' },
    { value: 'S', label: 'S 稳健型' },
    { value: 'C', label: 'C 谨慎型' },
  ],
  EPQ: [
    { value: 'E', label: 'E 外向性' },
    { value: 'N', label: 'N 神经质' },
    { value: 'P', label: 'P 精神质' },
    { value: 'L', label: 'L 掩饰性' },
  ],
}
</script>

<script setup lang="ts">
import { ref, watch, computed } from 'vue'
import {
  getCheckboxSelectionRule,
  type CheckboxSelectionRuleMode,
} from '../utils/checkboxSelectionLimit'

// 控件库配置
const questionControls = [
  { type: 'radio', label: '单选题', icon: 'ri-radio-button-line' },
  { type: 'checkbox', label: '多选题', icon: 'ri-checkbox-line' },
  { type: 'text', label: '单行文本', icon: 'ri-input-field' },
  { type: 'textarea', label: '多行文本', icon: 'ri-text' },
  { type: 'scale', label: '量表题', icon: 'ri-equalizer-line' },
  { type: 'yesno', label: '是非题', icon: 'ri-question-answer-line' },
  { type: 'choice', label: '二选一', icon: 'ri-arrow-left-right-line' },
]

// ===== Props =====
const props = defineProps<{
  question: EditorQuestion | null
  isEdit: boolean
  assessmentType?: 'MBTI' | 'DISC' | 'EPQ' | null  // 专业测评类型，null表示普通问卷
}>()

// ===== Emits =====
const emit = defineEmits<{
  (e: 'close'): void
  (e: 'save', question: EditorQuestion): void
}>()

// ===== 状态 =====
const newQuestion = ref<EditorQuestion>({
  id: '',
  type: 'radio',
  text: '',
  required: true,
  options: [
    { label: '选项1', value: 'opt1' },
    { label: '选项2', value: 'opt2' },
  ],
  scale: { min: 1, max: 5, minLabel: '非常不满意', maxLabel: '非常满意' },
  optionA: '',
  optionB: '',
})

// ===== 计算属性 =====
const canSave = computed(() => {
  return newQuestion.value.text.trim() !== ''
})

const isBackdropPointerDown = ref(false)

// 是否为专业测评模式
const isProfessionalMode = computed(() => !!props.assessmentType)

// 当前测评类型的维度列表
const currentDimensions = computed(() => {
  if (!props.assessmentType) return []
  return ASSESSMENT_DIMENSIONS[props.assessmentType] || []
})

// ===== 方法 =====
const close = () => emit('close')

const isBackdropEvent = (event: Event) => event.target === event.currentTarget

const setQuestionType = (type: string) => {
  newQuestion.value.type = type as EditorQuestion['type']
}

const ensureScaleConfig = () => {
  if (!newQuestion.value.scale) {
    newQuestion.value.scale = { min: 1, max: 5, minLabel: '非常不满意', maxLabel: '非常满意' }
  }
  return newQuestion.value.scale
}

const scaleConfig = computed(() => ensureScaleConfig())
const checkboxOptionCount = computed(() => newQuestion.value.options?.length || 0)
const checkboxMaxInputMax = computed(() => Math.max(1, checkboxOptionCount.value))
const checkboxSelectionRuleOptions: { value: CheckboxSelectionRuleMode; label: string }[] = [
  { value: 'none', label: '不限制' },
  { value: 'max', label: '最多' },
  { value: 'min', label: '至少' },
  { value: 'exact', label: '必须' },
  { value: 'range', label: '范围' },
]
const checkboxRuleSliderStyle = computed(() => {
  const index = Math.max(
    0,
    checkboxSelectionRuleOptions.findIndex((rule) => rule.value === checkboxSelectionRuleMode.value),
  )
  return { '--checkbox-rule-offset': `${index * 100}%` }
})
const checkboxSelectionRuleMode = computed<CheckboxSelectionRuleMode>({
  get() {
    return getCheckboxSelectionRule(newQuestion.value).mode
  },
  set(mode) {
    newQuestion.value.selectionRule = mode
    if (mode === 'none') {
      newQuestion.value.minSelections = null
      newQuestion.value.maxSelections = null
    } else if (mode === 'max') {
      newQuestion.value.minSelections = null
    } else if (mode === 'min') {
      newQuestion.value.maxSelections = null
    } else if (mode === 'exact') {
      newQuestion.value.maxSelections = null
    }
    if (mode === 'min' || mode === 'exact' || mode === 'range') {
      newQuestion.value.required = true
    }
  },
})
const checkboxRuleRequiresAnswer = computed(() => (
  checkboxSelectionRuleMode.value === 'min'
  || checkboxSelectionRuleMode.value === 'exact'
  || checkboxSelectionRuleMode.value === 'range'
))
const setCheckboxSelectionRuleMode = (mode: CheckboxSelectionRuleMode) => {
  checkboxSelectionRuleMode.value = mode
}

const handleOverlayPressStart = (event: MouseEvent | TouchEvent) => {
  isBackdropPointerDown.value = isBackdropEvent(event)
}

const resetBackdropPointerDown = () => {
  isBackdropPointerDown.value = false
}

const handleOverlayClick = (event: MouseEvent) => {
  if (!isBackdropEvent(event)) return

  const shouldClose = isBackdropPointerDown.value
  isBackdropPointerDown.value = false

  if (shouldClose) {
    close()
  }
}

const generateId = () => {
  return `q_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
}

const initQuestion = () => {
  if (props.question) {
    // 编辑模式：复制现有题目
    newQuestion.value = JSON.parse(JSON.stringify(props.question))
  } else {
    // 新建模式：重置
    const baseQuestion: EditorQuestion = {
      id: generateId(),
      type: 'radio',
      text: '',
      required: true,
      options: [
        { label: '选项1', value: 'opt1' },
        { label: '选项2', value: 'opt2' },
      ],
      scale: { min: 1, max: 5, minLabel: '非常不满意', maxLabel: '非常满意' },
      optionA: '',
      optionB: '',
    }

    // 专业测评模式下添加维度字段
    if (props.assessmentType) {
      baseQuestion.dimension = currentDimensions.value[0]?.value || ''
      baseQuestion.positive = true
      // 专业测评默认使用是非题或二选一
      if (props.assessmentType === 'MBTI') {
        baseQuestion.type = 'choice'
      } else {
        baseQuestion.type = 'yesno'
      }
    }

    newQuestion.value = baseQuestion
  }
}

// 添加普通选项
const addQuestionOption = () => {
  if (!newQuestion.value.options) {
    newQuestion.value.options = []
  }
  const idx = newQuestion.value.options.length + 1
  newQuestion.value.options.push({
    label: `选项${idx}`,
    value: `opt${idx}`,
  })
}

// 🟢 新增：添加"其他"选项
const addOtherOption = () => {
  if (!newQuestion.value.options) {
    newQuestion.value.options = []
  }
  newQuestion.value.options.push({
    label: '其他（请注明）',
    value: 'other',
    allowCustom: true,
    placeholder: '请填写具体内容...'
  })
}

// 删除选项
const removeQuestionOption = (index: number) => {
  if (newQuestion.value.options && newQuestion.value.options.length > 2) {
    newQuestion.value.options.splice(index, 1)
  }
}

const readSelectionCount = (value: unknown) => {
  if (value === null || value === undefined || value === '') return null
  const parsed = Number(value)
  if (!Number.isFinite(parsed) || parsed < 1) return null
  return Math.floor(parsed)
}

type SelectionCountTarget = 'max' | 'min' | 'exact' | 'rangeMin' | 'rangeMax'

const clampSelectionCount = (value: unknown) => {
  const parsed = readSelectionCount(value) ?? 1
  return Math.min(Math.max(parsed, 1), checkboxMaxInputMax.value)
}

const adjustSelectionCount = (target: SelectionCountTarget, delta: number) => {
  const applyDelta = (value: unknown) => clampSelectionCount((readSelectionCount(value) ?? 1) + delta)

  if (target === 'max') {
    newQuestion.value.maxSelections = applyDelta(newQuestion.value.maxSelections)
    return
  }

  if (target === 'min' || target === 'exact') {
    newQuestion.value.minSelections = applyDelta(newQuestion.value.minSelections)
    return
  }

  if (target === 'rangeMin') {
    const minSelections = applyDelta(newQuestion.value.minSelections)
    newQuestion.value.minSelections = minSelections
    const maxSelections = clampSelectionCount(newQuestion.value.maxSelections)
    if (maxSelections < minSelections) {
      newQuestion.value.maxSelections = minSelections
    }
    return
  }

  const maxSelections = applyDelta(newQuestion.value.maxSelections)
  newQuestion.value.maxSelections = maxSelections
  const minSelections = clampSelectionCount(newQuestion.value.minSelections)
  if (minSelections > maxSelections) {
    newQuestion.value.minSelections = maxSelections
  }
}

const validateSelectionCount = (value: unknown, label: string) => {
  const parsed = readSelectionCount(value)
  if (parsed === null) {
    alert(`请设置${label}`)
    return null
  }
  if (parsed > checkboxOptionCount.value) {
    alert(`${label}不能大于当前选项数量`)
    return null
  }
  return parsed
}

const normalizeSelectionRule = () => {
  if (newQuestion.value.type !== 'checkbox') {
    delete newQuestion.value.selectionRule
    delete newQuestion.value.minSelections
    delete newQuestion.value.maxSelections
    return true
  }

  const mode = checkboxSelectionRuleMode.value
  if (mode === 'none') {
    delete newQuestion.value.selectionRule
    delete newQuestion.value.minSelections
    delete newQuestion.value.maxSelections
    return true
  }

  newQuestion.value.selectionRule = mode

  if (mode === 'max') {
    const maxSelections = validateSelectionCount(newQuestion.value.maxSelections, '最多可选数量')
    if (maxSelections === null) return false
    delete newQuestion.value.minSelections
    newQuestion.value.maxSelections = maxSelections
    return true
  }

  if (mode === 'min') {
    const minSelections = validateSelectionCount(newQuestion.value.minSelections, '至少选择数量')
    if (minSelections === null) return false
    newQuestion.value.required = true
    newQuestion.value.minSelections = minSelections
    delete newQuestion.value.maxSelections
    return true
  }

  if (mode === 'exact') {
    const exactSelections = validateSelectionCount(newQuestion.value.minSelections, '必须选择数量')
    if (exactSelections === null) return false
    newQuestion.value.required = true
    newQuestion.value.minSelections = exactSelections
    newQuestion.value.maxSelections = exactSelections
    return true
  }

  const minSelections = validateSelectionCount(newQuestion.value.minSelections, '最少选择数量')
  if (minSelections === null) return false
  const maxSelections = validateSelectionCount(newQuestion.value.maxSelections, '最多选择数量')
  if (maxSelections === null) return false
  if (minSelections > maxSelections) {
    alert('最少选择数量不能大于最多选择数量')
    return false
  }
  newQuestion.value.required = true
  newQuestion.value.minSelections = minSelections
  newQuestion.value.maxSelections = maxSelections
  return true
}

// 保存题目
const saveQuestion = () => {
  if (!canSave.value) return

  // 确保有ID
  if (!newQuestion.value.id) {
    newQuestion.value.id = generateId()
  }

  // 更新选项value
  if (newQuestion.value.options) {
    newQuestion.value.options.forEach((opt, i) => {
      opt.value = `opt${i + 1}`
    })
  }
  if (!normalizeSelectionRule()) return

  emit('save', JSON.parse(JSON.stringify(newQuestion.value)))
}

// ===== 监听 =====
watch(() => props.question, initQuestion, { immediate: true })

// 监听题目类型变化，初始化对应的数据结构
watch(() => newQuestion.value.type, (newType, oldType) => {
  if (newType === oldType) return

  // 切换到单选题或多选题时，确保有选项
  if ((newType === 'radio' || newType === 'checkbox') &&
      (!newQuestion.value.options || newQuestion.value.options.length === 0)) {
    newQuestion.value.options = [
      { label: '选项1', value: 'opt1' },
      { label: '选项2', value: 'opt2' },
    ]
  }

  // 切换到量表题时，确保有量表设置
  if (newType === 'scale' && !newQuestion.value.scale) {
    newQuestion.value.scale = { min: 1, max: 5, minLabel: '非常不满意', maxLabel: '非常满意' }
  }

  // 切换到是非题或二选一时，确保有分值设置
  if ((newType === 'yesno' || newType === 'choice') &&
      newQuestion.value.scoreA === undefined) {
    newQuestion.value.scoreA = 0
    newQuestion.value.scoreB = 0
  }

  if (newType !== 'checkbox') {
    delete newQuestion.value.selectionRule
    delete newQuestion.value.minSelections
    delete newQuestion.value.maxSelections
  }
})
</script>

<template src="./QuestionEditDialog.template.html"></template>

<style scoped>
@import './styles/question-edit-dialog.css';
</style>
