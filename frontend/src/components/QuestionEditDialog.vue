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

// 是否为专业测评模式
const isProfessionalMode = computed(() => !!props.assessmentType)

// 当前测评类型的维度列表
const currentDimensions = computed(() => {
  if (!props.assessmentType) return []
  return ASSESSMENT_DIMENSIONS[props.assessmentType] || []
})

// ===== 方法 =====
const close = () => emit('close')

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
  <div class="modal-overlay" @click="close">
    <div class="modal-dialog" @click.stop>
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
  z-index: 1100;
}

.modal-dialog {
  background: white;
  border-radius: 16px;
  width: 100%;
  max-width: 600px;
  max-height: 85vh;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.2);
}

.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 24px;
  border-bottom: 1px solid #e2e8f0;
}

.modal-header h3 {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 18px;
  font-weight: 600;
  color: #1e293b;
  margin: 0;
}

.modal-header h3 i {
  color: #6366f1;
}

.btn-close {
  width: 32px;
  height: 32px;
  border: none;
  background: #f1f5f9;
  border-radius: 8px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #64748b;
  font-size: 18px;
  transition: all 0.2s;
}

.btn-close:hover {
  background: #e2e8f0;
  color: #1e293b;
}

.modal-body {
  flex: 1;
  overflow-y: auto;
  padding: 24px;
}

.form-group {
  margin-bottom: 20px;
}

.form-label {
  display: block;
  font-size: 14px;
  font-weight: 500;
  color: #334155;
  margin-bottom: 8px;
}

.form-label .required {
  color: #ef4444;
}

.form-textarea {
  width: 100%;
  padding: 12px 14px;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  font-size: 14px;
  resize: vertical;
  transition: all 0.2s;
}

.form-textarea:focus {
  outline: none;
  border-color: #6366f1;
  box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.1);
}

/* 题目类型选择器 */
.question-type-selector {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.type-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 14px;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  font-size: 13px;
  color: #475569;
  cursor: pointer;
  transition: all 0.2s;
}

.type-btn:hover {
  background: #f1f5f9;
  border-color: #cbd5e1;
}

.type-btn.active {
  background: #eef2ff;
  border-color: #6366f1;
  color: #6366f1;
}

.type-btn i {
  font-size: 16px;
}

/* 复选框样式 */
.checkbox-group {
  margin-top: 8px;
}

.checkbox-label {
  display: flex;
  align-items: center;
  gap: 10px;
  cursor: pointer;
  font-size: 14px;
  color: #334155;
}

.checkbox-label input {
  display: none;
}

.checkbox-custom {
  width: 18px;
  height: 18px;
  border: 2px solid #cbd5e1;
  border-radius: 4px;
  position: relative;
  transition: all 0.2s;
}

.checkbox-label input:checked + .checkbox-custom {
  background: #6366f1;
  border-color: #6366f1;
}

.checkbox-label input:checked + .checkbox-custom::after {
  content: '';
  position: absolute;
  left: 5px;
  top: 1px;
  width: 5px;
  height: 10px;
  border: solid white;
  border-width: 0 2px 2px 0;
  transform: rotate(45deg);
}

/* 选项编辑器 */
.options-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-bottom: 12px;
}

.options-header {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 0 0 8px 0;
  border-bottom: 1px solid #e2e8f0;
  margin-bottom: 4px;
}

.options-header .col-indicator {
  width: 20px;
}

.options-header .col-label {
  flex: 1;
  font-size: 12px;
  color: #64748b;
  font-weight: 500;
}

.options-header .col-score {
  width: 70px;
  font-size: 12px;
  color: #64748b;
  font-weight: 500;
  text-align: center;
}

.options-header .col-custom {
  width: 36px;
  font-size: 12px;
  color: #64748b;
  font-weight: 500;
  text-align: center;
}

.options-header .col-action {
  width: 32px;
}

.option-edit-item {
  display: flex;
  align-items: center;
  gap: 10px;
}

.score-input {
  width: 70px;
  padding: 10px 8px;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  font-size: 14px;
  text-align: center;
  transition: all 0.2s;
}

.score-input:focus {
  outline: none;
  border-color: #6366f1;
  box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.1);
}

.score-input::-webkit-inner-spin-button,
.score-input::-webkit-outer-spin-button {
  -webkit-appearance: none;
  margin: 0;
}

.option-indicator {
  font-size: 16px;
  color: #94a3b8;
  width: 20px;
  text-align: center;
}

.option-input {
  flex: 1;
  padding: 10px 14px;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  font-size: 14px;
  transition: all 0.2s;
}

.option-input:focus {
  outline: none;
  border-color: #6366f1;
  box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.1);
}

.btn-remove-option {
  width: 32px;
  height: 32px;
  border: none;
  background: #fef2f2;
  border-radius: 6px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #ef4444;
  font-size: 16px;
  transition: all 0.2s;
}

.btn-remove-option:hover:not(:disabled) {
  background: #fee2e2;
}

.btn-remove-option:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

/* 🟢 新增：允许自定义输入按钮 */
.btn-toggle-custom {
  width: 36px;
  height: 32px;
  border: none;
  background: #f1f5f9;
  border-radius: 6px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #94a3b8;
  font-size: 16px;
  transition: all 0.2s;
}

.btn-toggle-custom:hover {
  background: #e2e8f0;
  color: #6366f1;
}

.btn-toggle-custom.active {
  background: linear-gradient(135deg, #6366f1, #8b5cf6);
  color: white;
}

/* 选项按钮容器 */
.option-buttons {
  display: flex;
  gap: 8px;
}

.btn-add-option {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 10px;
  background: #f8fafc;
  border: 1px dashed #cbd5e1;
  border-radius: 8px;
  font-size: 14px;
  color: #64748b;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-add-option:hover {
  background: #f1f5f9;
  border-color: #6366f1;
  color: #6366f1;
}

/* 🟢 新增："添加其他选项"按钮 */
.btn-add-other-option {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 10px;
  background: linear-gradient(135deg, #eef2ff, #e0e7ff);
  border: 1px dashed #a5b4fc;
  border-radius: 8px;
  font-size: 14px;
  color: #6366f1;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-add-other-option:hover {
  background: linear-gradient(135deg, #e0e7ff, #ddd6fe);
  border-color: #6366f1;
  border-style: solid;
}

/* 量表设置 */
.scale-settings {
  background: #f8fafc;
  padding: 16px;
  border-radius: 10px;
}

.scale-range {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 16px;
}

.range-item {
  flex: 1;
}

.range-item label {
  display: block;
  font-size: 12px;
  color: #64748b;
  margin-bottom: 6px;
}

.range-item input {
  width: 100%;
  padding: 8px 12px;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  font-size: 14px;
  text-align: center;
}

.range-arrow {
  color: #94a3b8;
  font-size: 16px;
  margin-top: 20px;
}

.scale-labels-edit {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}

.label-item label {
  display: block;
  font-size: 12px;
  color: #64748b;
  margin-bottom: 6px;
}

.label-item input {
  width: 100%;
  padding: 8px 12px;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  font-size: 14px;
}

/* 专业测评维度设置 */
.dimension-editor .form-label {
  display: flex;
  align-items: center;
  gap: 6px;
}

.dimension-editor .form-label i {
  color: #7c3aed;
}

.dimension-settings {
  display: flex;
  gap: 24px;
  padding: 16px;
  background: linear-gradient(135deg, #f5f3ff 0%, #ede9fe 100%);
  border-radius: 12px;
  border: 1px solid #ddd6fe;
}

.dimension-select-group,
.direction-toggle-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.dimension-select-group label,
.direction-toggle-group label {
  font-size: 12px;
  font-weight: 500;
  color: #6b7280;
}

.dimension-select {
  padding: 10px 14px;
  border: 1px solid #c4b5fd;
  border-radius: 8px;
  font-size: 14px;
  background: white;
  color: #374151;
  min-width: 180px;
  cursor: pointer;
}

.dimension-select:focus {
  outline: none;
  border-color: #7c3aed;
  box-shadow: 0 0 0 3px rgba(124, 58, 237, 0.15);
}

.direction-toggle {
  display: flex;
  gap: 8px;
}

.direction-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 10px 16px;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  background: white;
  font-size: 13px;
  font-weight: 500;
  color: #6b7280;
  cursor: pointer;
  transition: all 0.2s;
}

.direction-btn:hover {
  border-color: #c4b5fd;
  background: #f5f3ff;
}

.direction-btn.active {
  border-color: #7c3aed;
  background: linear-gradient(135deg, #7c3aed 0%, #6d28d9 100%);
  color: white;
}

.direction-btn i {
  font-size: 16px;
}

.dimension-tip {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-top: 8px;
  padding: 10px 14px;
  background: #fef3c7;
  border-radius: 8px;
  font-size: 12px;
  color: #92400e;
}

.dimension-tip i {
  color: #f59e0b;
  font-size: 14px;
}

/* 是非题设置 */
.yesno-options {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.yesno-option-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  background: #f8fafc;
  border-radius: 10px;
}

.yesno-badge {
  width: 40px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 600;
  font-size: 14px;
  border-radius: 6px;
}

.yesno-badge.yes {
  background: linear-gradient(135deg, #22c55e, #16a34a);
  color: white;
}

.yesno-badge.no {
  background: linear-gradient(135deg, #ef4444, #dc2626);
  color: white;
}

.yesno-score-group {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-left: auto;
}

.yesno-score-group label {
  font-size: 12px;
  color: #64748b;
  white-space: nowrap;
}

.yesno-score-input {
  width: 60px;
  padding: 8px;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  font-size: 14px;
  text-align: center;
  transition: all 0.2s;
}

.yesno-score-input:focus {
  outline: none;
  border-color: #6366f1;
  box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.1);
}

.yesno-score-input::-webkit-inner-spin-button,
.yesno-score-input::-webkit-outer-spin-button {
  -webkit-appearance: none;
  margin: 0;
}

/* 二选一设置 */
.choice-options {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.choice-option-item {
  display: flex;
  align-items: center;
  gap: 12px;
}

.choice-letter-badge {
  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #6366f1, #8b5cf6);
  color: white;
  font-weight: 600;
  font-size: 14px;
  border-radius: 6px;
}

.choice-text-input {
  flex: 1;
  padding: 10px 14px;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  font-size: 14px;
  transition: all 0.2s;
}

.choice-text-input:focus {
  outline: none;
  border-color: #6366f1;
  box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.1);
}

.choice-score-group {
  display: flex;
  align-items: center;
  gap: 8px;
}

.choice-score-group label {
  font-size: 12px;
  color: #64748b;
  white-space: nowrap;
}

.choice-score-input {
  width: 60px;
  padding: 10px 8px;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  font-size: 14px;
  text-align: center;
  transition: all 0.2s;
}

.choice-score-input:focus {
  outline: none;
  border-color: #6366f1;
  box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.1);
}

.choice-score-input::-webkit-inner-spin-button,
.choice-score-input::-webkit-outer-spin-button {
  -webkit-appearance: none;
  margin: 0;
}

/* 底部 */
.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  padding: 16px 24px;
  border-top: 1px solid #e2e8f0;
  background: #f8fafc;
}

.btn-cancel {
  padding: 10px 20px;
  background: white;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  font-size: 14px;
  color: #475569;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-cancel:hover {
  background: #f1f5f9;
}

.btn-primary {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 10px 20px;
  background: linear-gradient(135deg, #6366f1, #8b5cf6);
  color: white;
  border: none;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-primary:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(99, 102, 241, 0.3);
}

.btn-primary:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
</style>

