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
})
</script>

<template>
  <div
    class="modal-overlay"
    @mousedown.stop="handleOverlayPressStart"
    @touchstart.stop="handleOverlayPressStart"
    @click.stop="handleOverlayClick"
  >
    <div
      class="modal-dialog"
      @mousedown.stop="resetBackdropPointerDown"
      @touchstart.stop="resetBackdropPointerDown"
      @click.stop
    >
      <div class="modal-header">
        <h3>
          <i :class="isEdit ? 'ri-edit-line' : 'ri-add-circle-line'"></i>
          {{ isEdit ? '编辑题目' : '添加题目' }}
        </h3>
        <button class="btn-close" @click="close">
          <i class="ri-close-line"></i>
        </button>
      </div>

      <div class="modal-body">
        <!-- 题目类型选择 -->
        <div class="form-group">
          <label class="form-label">题目类型</label>
          <div class="question-type-selector">
            <button
              v-for="qType in questionControls"
              :key="qType.type"
              :class="['type-btn', { active: newQuestion.type === qType.type }]"
              @click="newQuestion.type = qType.type as any"
            >
              <i :class="qType.icon"></i>
              <span>{{ qType.label }}</span>
            </button>
          </div>
        </div>

        <!-- 题目内容 -->
        <div class="form-group">
          <label class="form-label">题目内容 <span class="required">*</span></label>
          <textarea
            class="form-textarea"
            rows="2"
            v-model="newQuestion.text"
            placeholder="请输入题目内容，如：您对目前的工作满意度如何？"
          ></textarea>
        </div>

        <!-- 是否必答 -->
        <div class="form-group checkbox-group">
          <label class="checkbox-label">
            <input type="checkbox" v-model="newQuestion.required" />
            <span class="checkbox-custom"></span>
            <span>设为必答题</span>
          </label>
        </div>

        <!-- 选项编辑（单选/多选） -->
        <div v-if="newQuestion.type === 'radio' || newQuestion.type === 'checkbox'" class="form-group options-editor">
          <label class="form-label">选项设置</label>
          <div class="options-list">
            <div class="options-header">
              <span class="col-indicator"></span>
              <span class="col-label">选项内容</span>
              <span v-if="!isProfessionalMode" class="col-score">分值</span>
              <span class="col-custom">自定义</span>
              <span class="col-action"></span>
            </div>
            <div v-for="(opt, index) in newQuestion.options" :key="index" class="option-edit-item">
              <span class="option-indicator">{{ newQuestion.type === 'radio' ? '○' : '☐' }}</span>
              <input
                type="text"
                class="option-input"
                v-model="opt.label"
                :placeholder="`选项${index + 1}`"
              />
              <input
                v-if="!isProfessionalMode"
                type="number"
                class="score-input"
                v-model.number="opt.score"
                placeholder="0"
                min="0"
                max="100"
              />
              <!-- 🟢 新增：允许自定义输入开关 -->
              <button
                type="button"
                :class="['btn-toggle-custom', { active: opt.allowCustom }]"
                @click="opt.allowCustom = !opt.allowCustom"
                :title="opt.allowCustom ? '取消自定义输入' : '允许用户自定义输入'"
              >
                <i :class="opt.allowCustom ? 'ri-edit-fill' : 'ri-edit-line'"></i>
              </button>
              <button
                class="btn-remove-option"
                @click="removeQuestionOption(index)"
                :disabled="(newQuestion.options?.length || 0) <= 2"
                title="删除选项"
              >
                <i class="ri-close-line"></i>
              </button>
            </div>
          </div>
          <div class="option-buttons">
            <button class="btn-add-option" @click="addQuestionOption">
              <i class="ri-add-line"></i>
              添加选项
            </button>
            <button class="btn-add-other-option" @click="addOtherOption">
              <i class="ri-edit-box-line"></i>
              添加"其他"选项
            </button>
          </div>
        </div>

        <!-- 量表设置 -->
        <div v-if="newQuestion.type === 'scale'" class="form-group scale-editor">
          <label class="form-label">量表设置</label>
          <div class="scale-settings">
            <div class="scale-range">
              <div class="range-item">
                <label>最小值</label>
                <input type="number" v-model.number="newQuestion.scale!.min" min="1" max="10" />
              </div>
              <span class="range-arrow">→</span>
              <div class="range-item">
                <label>最大值</label>
                <input type="number" v-model.number="newQuestion.scale!.max" min="1" max="10" />
              </div>
            </div>
            <div class="scale-labels-edit">
              <div class="label-item">
                <label>最小值标签</label>
                <input type="text" v-model="newQuestion.scale!.minLabel" placeholder="非常不满意" />
              </div>
              <div class="label-item">
                <label>最大值标签</label>
                <input type="text" v-model="newQuestion.scale!.maxLabel" placeholder="非常满意" />
              </div>
            </div>
          </div>
        </div>

        <!-- 专业测评维度设置 -->
        <div v-if="isProfessionalMode" class="form-group dimension-editor">
          <label class="form-label">
            <i class="ri-pie-chart-line"></i>
            维度设置
          </label>
          <div class="dimension-settings">
            <div class="dimension-select-group">
              <label>所属维度</label>
              <select v-model="newQuestion.dimension" class="dimension-select">
                <option v-for="dim in currentDimensions" :key="dim.value" :value="dim.value">
                  {{ dim.label }}
                </option>
              </select>
            </div>
            <div class="direction-toggle-group">
              <label>计分方向</label>
              <div class="direction-toggle">
                <button
                  type="button"
                  :class="['direction-btn', { active: newQuestion.positive === true }]"
                  @click="newQuestion.positive = true"
                >
                  <i class="ri-arrow-up-line"></i>
                  正向
                </button>
                <button
                  type="button"
                  :class="['direction-btn', { active: newQuestion.positive === false }]"
                  @click="newQuestion.positive = false"
                >
                  <i class="ri-arrow-down-line"></i>
                  反向
                </button>
              </div>
            </div>
          </div>
          <p class="dimension-tip">
            <i class="ri-information-line"></i>
            {{ newQuestion.positive ? '正向计分：选择"是"或"A"时计入该维度' : '反向计分：选择"否"或"B"时计入该维度' }}
          </p>
        </div>

        <!-- 是非题设置 -->
        <div v-if="newQuestion.type === 'yesno'" class="form-group yesno-editor">
          <label class="form-label">选项设置</label>
          <div class="yesno-options">
            <div class="yesno-option-item">
              <span class="yesno-badge yes">是</span>
              <div v-if="!isProfessionalMode" class="yesno-score-group">
                <label>分值</label>
                <input type="number" v-model.number="newQuestion.scoreA" placeholder="0" min="0" max="100" class="yesno-score-input" />
              </div>
            </div>
            <div class="yesno-option-item">
              <span class="yesno-badge no">否</span>
              <div v-if="!isProfessionalMode" class="yesno-score-group">
                <label>分值</label>
                <input type="number" v-model.number="newQuestion.scoreB" placeholder="0" min="0" max="100" class="yesno-score-input" />
              </div>
            </div>
          </div>
        </div>

        <!-- 二选一设置 -->
        <div v-if="newQuestion.type === 'choice'" class="form-group choice-editor">
          <label class="form-label">选项设置</label>
          <div class="choice-options">
            <div class="choice-option-item">
              <span class="choice-letter-badge">A</span>
              <input type="text" v-model="newQuestion.optionA" placeholder="选项A内容" class="choice-text-input" />
              <div v-if="!isProfessionalMode" class="choice-score-group">
                <label>分值</label>
                <input type="number" v-model.number="newQuestion.scoreA" placeholder="0" min="0" max="100" class="choice-score-input" />
              </div>
            </div>
            <div class="choice-option-item">
              <span class="choice-letter-badge">B</span>
              <input type="text" v-model="newQuestion.optionB" placeholder="选项B内容" class="choice-text-input" />
              <div v-if="!isProfessionalMode" class="choice-score-group">
                <label>分值</label>
                <input type="number" v-model.number="newQuestion.scoreB" placeholder="0" min="0" max="100" class="choice-score-input" />
              </div>
            </div>
          </div>
        </div>
      </div>

      <div class="modal-footer">
        <button class="btn-cancel" @click="close">取消</button>
        <button class="btn-primary" @click="saveQuestion" :disabled="!canSave">
          <i class="ri-check-line"></i>
          {{ isEdit ? '保存修改' : '添加题目' }}
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
@import './styles/question-edit-dialog.css';
</style>
