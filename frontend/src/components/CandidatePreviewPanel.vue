<script setup lang="ts">
/**
 * 候选人预览面板组件
 * 
 * 功能：
 * 1. 展示问卷题目的候选人视角
 * 2. 支持题目导航
 * 3. 模拟答题交互
 */
import { ref, watch, computed } from 'vue'

// ===== 类型定义 =====
export interface EditorQuestion {
  id: string
  type: 'radio' | 'checkbox' | 'text' | 'textarea' | 'scale' | 'yesno' | 'choice'
  text: string
  required: boolean
  options?: { label: string; value: string; score?: number }[]
  scale?: { min: number; max: number; minLabel: string; maxLabel: string }
  optionA?: string
  optionB?: string
  scoreA?: number
  scoreB?: number
}

// 控件库配置（用于获取题型名称）
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
  questions: EditorQuestion[]
}>()

// ===== 状态 =====
const previewIndex = ref(0)
const previewAnswer = ref('')
const previewAnswerMulti = ref<string[]>([])
const previewScaleValue = ref<number | null>(null)
const previewYesno = ref('')
const previewChoice = ref('')

// ===== 计算属性 =====
const currentQuestion = computed(() => {
  return props.questions[previewIndex.value] || null
})

const scaleRange = computed(() => {
  if (!currentQuestion.value?.scale) return []
  const { min, max } = currentQuestion.value.scale
  return Array.from({ length: max - min + 1 }, (_, i) => min + i)
})

// ===== 方法 =====
const getQuestionTypeName = (type: string) => {
  const ctrl = questionControls.find(c => c.type === type)
  return ctrl?.label || type
}

const prevQuestion = () => {
  if (previewIndex.value > 0) {
    previewIndex.value--
    resetPreviewAnswers()
  }
}

const nextQuestion = () => {
  if (previewIndex.value < props.questions.length - 1) {
    previewIndex.value++
    resetPreviewAnswers()
  }
}

const resetPreviewAnswers = () => {
  previewAnswer.value = ''
  previewAnswerMulti.value = []
  previewScaleValue.value = null
  previewYesno.value = ''
  previewChoice.value = ''
}

const toggleMultiOption = (value: string) => {
  const idx = previewAnswerMulti.value.indexOf(value)
  if (idx > -1) {
    previewAnswerMulti.value.splice(idx, 1)
  } else {
    previewAnswerMulti.value.push(value)
  }
}

// ===== 监听 =====
// V44: 监听题目数量变化，自动跳转到新添加的题目
watch(() => props.questions.length, (newLength, oldLength) => {
  if (newLength > oldLength) {
    // 新增题目时，自动跳转到最后一道题
    previewIndex.value = newLength - 1
  } else if (previewIndex.value >= newLength) {
    // 删除题目时，确保索引有效
    previewIndex.value = Math.max(0, newLength - 1)
  }
  resetPreviewAnswers()
}, { immediate: true })

// V45: 深度监听题目数组变化，确保任何变化都能触发更新
watch(() => props.questions, (newQuestions) => {
  // 确保索引在有效范围内
  if (previewIndex.value >= newQuestions.length) {
    previewIndex.value = Math.max(0, newQuestions.length - 1)
  }
}, { deep: true })
</script>

<template>
  <div class="candidate-preview-panel">
    <div class="preview-header">
      <h4><i class="ri-smartphone-line"></i> 实时预览</h4>
      <div class="preview-nav" v-if="questions.length > 0">
        <button class="preview-nav-btn" @click="prevQuestion" :disabled="previewIndex === 0">
          <i class="ri-arrow-left-s-line"></i>
        </button>
        <span class="preview-nav-info">{{ previewIndex + 1 }} / {{ questions.length }}</span>
        <button class="preview-nav-btn" @click="nextQuestion" :disabled="previewIndex >= questions.length - 1">
          <i class="ri-arrow-right-s-line"></i>
        </button>
      </div>
    </div>

    <div class="candidate-preview-body">
      <!-- 手机模拟器 -->
      <div class="phone-mockup">
        <div class="phone-frame">
          <div class="phone-speaker"></div>
          <div class="phone-screen">
      <!-- 空状态 -->
      <div v-if="questions.length === 0" class="preview-empty-state">
        <div class="empty-icon">
          <i class="ri-file-list-3-line"></i>
        </div>
        <p class="empty-title">暂无题目</p>
        <p class="empty-desc">添加题目后可实时预览效果</p>
      </div>

      <!-- 题目预览卡片 -->
      <div v-else-if="currentQuestion" class="candidate-question-card">
        <!-- 题目头部 -->
        <div class="cq-header">
          <div class="cq-number">
            <span class="num">{{ previewIndex + 1 }}</span>
            <span class="total">/ {{ questions.length }}</span>
          </div>
          <div class="cq-tags">
            <span v-if="currentQuestion.required" class="cq-tag required">必答</span>
            <span class="cq-tag type">{{ getQuestionTypeName(currentQuestion.type) }}</span>
          </div>
        </div>

        <!-- 题目内容 -->
        <h3 class="cq-text">{{ currentQuestion.text || '请输入题目内容' }}</h3>

        <!-- 单选题预览 -->
        <div v-if="currentQuestion.type === 'radio'" class="cq-options">
          <div 
            v-for="(opt, i) in (currentQuestion.options || [])" 
            :key="i" 
            class="cq-option-card"
            :class="{ 'selected': previewAnswer === opt.value }"
            @click="previewAnswer = previewAnswer === opt.value ? '' : opt.value"
          >
            <span class="cq-indicator"><span class="inner"></span></span>
            <span class="cq-option-text">{{ opt.label }}</span>
          </div>
        </div>

        <!-- 多选题预览 -->
        <div v-else-if="currentQuestion.type === 'checkbox'" class="cq-checkbox-grid">
          <div 
            v-for="(opt, i) in (currentQuestion.options || [])" 
            :key="i" 
            class="cq-checkbox-card"
            :class="{ 'selected': previewAnswerMulti.includes(opt.value) }"
            @click="toggleMultiOption(opt.value)"
          >
            <span class="cq-checkbox-indicator">
              <i v-if="previewAnswerMulti.includes(opt.value)" class="ri-check-line"></i>
            </span>
            <span class="cq-checkbox-text">{{ opt.label }}</span>
          </div>
        </div>

        <!-- 文本输入预览 -->
        <div v-else-if="currentQuestion.type === 'text'" class="cq-text-input">
          <input type="text" placeholder="请输入您的回答..." v-model="previewAnswer" />
        </div>

        <!-- 多行文本预览 -->
        <div v-else-if="currentQuestion.type === 'textarea'" class="cq-textarea-input">
          <textarea rows="4" placeholder="请输入您的详细回答..." v-model="previewAnswer"></textarea>
        </div>

        <!-- 量表题预览 -->
        <div v-else-if="currentQuestion.type === 'scale'" class="cq-scale-container">
          <div class="cq-scale-labels">
            <span class="min-label">{{ currentQuestion.scale?.minLabel || '最低' }}</span>
            <span class="max-label">{{ currentQuestion.scale?.maxLabel || '最高' }}</span>
          </div>
          <div class="cq-scale-options">
            <button 
              v-for="val in scaleRange" 
              :key="val"
              :class="['cq-scale-btn', { active: previewScaleValue === val }]"
              @click="previewScaleValue = previewScaleValue === val ? null : val"
            >
              {{ val }}
            </button>
          </div>
        </div>

        <!-- 是非题预览 -->
        <div v-else-if="currentQuestion.type === 'yesno'" class="cq-yesno-container">
          <button 
            :class="['cq-yesno-btn yes', { active: previewYesno === 'yes' }]"
            @click="previewYesno = previewYesno === 'yes' ? '' : 'yes'"
          >
            <i class="ri-check-line"></i>
            <span>是</span>
          </button>
          <button 
            :class="['cq-yesno-btn no', { active: previewYesno === 'no' }]"
            @click="previewYesno = previewYesno === 'no' ? '' : 'no'"
          >
            <i class="ri-close-line"></i>
            <span>否</span>
          </button>
        </div>

        <!-- 二选一预览 -->
        <div v-else-if="currentQuestion.type === 'choice'" class="cq-choice-container">
          <button 
            :class="['cq-choice-btn', { active: previewChoice === 'A' }]"
            @click="previewChoice = previewChoice === 'A' ? '' : 'A'"
          >
            <span class="choice-letter">A</span>
            <span class="choice-text">{{ currentQuestion.optionA || '选项A' }}</span>
          </button>
          <div class="choice-vs">VS</div>
          <button 
            :class="['cq-choice-btn', { active: previewChoice === 'B' }]"
            @click="previewChoice = previewChoice === 'B' ? '' : 'B'"
          >
            <span class="choice-letter">B</span>
            <span class="choice-text">{{ currentQuestion.optionB || '选项B' }}</span>
          </button>
        </div>
      </div>
          </div>
          <div class="phone-home-bar"></div>
        </div>
      </div>
    </div>

    <!-- 底部提示 -->
    <div class="preview-footer">
      <i class="ri-information-line"></i>
      <span>这是候选人答题时看到的效果</span>
    </div>
  </div>
</template>

<style scoped>
.candidate-preview-panel {
  display: flex;
  flex-direction: column;
  background: #f8fafc;
  border-radius: 12px;
  border: 1px solid #e2e8f0;
  overflow: hidden;
  height: 100%;
}

.preview-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 16px;
  background: white;
  border-bottom: 1px solid #e2e8f0;
}

.preview-header h4 {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  font-weight: 600;
  color: #1e293b;
  margin: 0;
}

.preview-header h4 i {
  color: #6366f1;
}

.preview-nav {
  display: flex;
  align-items: center;
  gap: 8px;
}

.preview-nav-btn {
  width: 28px;
  height: 28px;
  border: none;
  background: #f1f5f9;
  border-radius: 6px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #64748b;
  font-size: 16px;
  transition: all 0.2s;
}

.preview-nav-btn:hover:not(:disabled) {
  background: #e2e8f0;
  color: #1e293b;
}

.preview-nav-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.preview-nav-info {
  font-size: 12px;
  color: #64748b;
  min-width: 50px;
  text-align: center;
}

.candidate-preview-body {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
  display: flex;
  justify-content: center;
  align-items: flex-start;
}

/* 手机模拟器 */
.phone-mockup {
  flex-shrink: 0;
}

.phone-frame {
  width: 280px;
  background: #1f2937;
  border-radius: 36px;
  padding: 10px;
  box-shadow: 
    0 0 0 2px #374151,
    0 20px 40px -10px rgba(0, 0, 0, 0.5),
    inset 0 1px 0 rgba(255, 255, 255, 0.1);
}

.phone-speaker {
  width: 60px;
  height: 6px;
  background: #374151;
  margin: 6px auto 10px;
  border-radius: 3px;
}

.phone-screen {
  background: white;
  border-radius: 26px;
  height: 480px;
  overflow-y: auto;
  overflow-x: hidden;
  box-shadow: inset 0 1px 4px rgba(0, 0, 0, 0.1);
  padding: 16px;
}

.phone-home-bar {
  width: 100px;
  height: 4px;
  background: #4b5563;
  margin: 10px auto 4px;
  border-radius: 2px;
}

/* 空状态 */
.preview-empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  padding: 40px 20px;
  text-align: center;
}

.empty-icon {
  width: 64px;
  height: 64px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #e2e8f0;
  border-radius: 50%;
  margin-bottom: 16px;
}

.empty-icon i {
  font-size: 28px;
  color: #94a3b8;
}

.empty-title {
  font-size: 15px;
  font-weight: 500;
  color: #475569;
  margin: 0 0 8px;
}

.empty-desc {
  font-size: 13px;
  color: #94a3b8;
  margin: 0;
}

/* 题目卡片 */
.candidate-question-card {
  background: transparent;
  border-radius: 0;
  padding: 0;
  box-shadow: none;
}

.cq-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}

.cq-number {
  display: flex;
  align-items: baseline;
  gap: 4px;
}

.cq-number .num {
  font-size: 24px;
  font-weight: 700;
  color: #6366f1;
}

.cq-number .total {
  font-size: 14px;
  color: #94a3b8;
}

.cq-tags {
  display: flex;
  gap: 8px;
}

.cq-tag {
  padding: 4px 10px;
  border-radius: 12px;
  font-size: 11px;
  font-weight: 500;
}

.cq-tag.required {
  background: #fef2f2;
  color: #ef4444;
}

.cq-tag.type {
  background: #eef2ff;
  color: #6366f1;
}

.cq-text {
  font-size: 16px;
  font-weight: 500;
  color: #1e293b;
  margin: 0 0 20px;
  line-height: 1.5;
}

/* 单选题选项 */
.cq-options {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.cq-option-card {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px 16px;
  background: #f8fafc;
  border: 2px solid #e2e8f0;
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.2s;
}

.cq-option-card:hover {
  background: #f1f5f9;
  border-color: #cbd5e1;
}

.cq-option-card.selected {
  background: #eef2ff;
  border-color: #6366f1;
}

.cq-indicator {
  width: 20px;
  height: 20px;
  border: 2px solid #cbd5e1;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  transition: all 0.2s;
}

.cq-option-card.selected .cq-indicator {
  border-color: #6366f1;
}

.cq-indicator .inner {
  width: 10px;
  height: 10px;
  background: #6366f1;
  border-radius: 50%;
  opacity: 0;
  transition: opacity 0.2s;
}

.cq-option-card.selected .cq-indicator .inner {
  opacity: 1;
}

.cq-option-text {
  font-size: 14px;
  color: #334155;
}

/* 多选题 */
.cq-checkbox-grid {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.cq-checkbox-card {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px 16px;
  background: #f8fafc;
  border: 2px solid #e2e8f0;
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.2s;
}

.cq-checkbox-card:hover {
  background: #f1f5f9;
  border-color: #cbd5e1;
}

.cq-checkbox-card.selected {
  background: #eef2ff;
  border-color: #6366f1;
}

.cq-checkbox-indicator {
  width: 20px;
  height: 20px;
  border: 2px solid #cbd5e1;
  border-radius: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  transition: all 0.2s;
}

.cq-checkbox-card.selected .cq-checkbox-indicator {
  background: #6366f1;
  border-color: #6366f1;
  color: white;
}

.cq-checkbox-text {
  font-size: 14px;
  color: #334155;
}

/* 文本输入 */
.cq-text-input input,
.cq-textarea-input textarea {
  width: 100%;
  padding: 14px 16px;
  border: 2px solid #e2e8f0;
  border-radius: 12px;
  font-size: 14px;
  transition: all 0.2s;
}

.cq-text-input input:focus,
.cq-textarea-input textarea:focus {
  outline: none;
  border-color: #6366f1;
  box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.1);
}

.cq-textarea-input textarea {
  resize: vertical;
  min-height: 100px;
}

/* 量表题 */
.cq-scale-container {
  padding: 16px 0;
}

.cq-scale-labels {
  display: flex;
  justify-content: space-between;
  margin-bottom: 12px;
  font-size: 12px;
  color: #64748b;
}

.cq-scale-options {
  display: flex;
  justify-content: space-between;
  gap: 8px;
}

.cq-scale-btn {
  flex: 1;
  padding: 12px 8px;
  background: #f8fafc;
  border: 2px solid #e2e8f0;
  border-radius: 10px;
  font-size: 16px;
  font-weight: 600;
  color: #64748b;
  cursor: pointer;
  transition: all 0.2s;
}

.cq-scale-btn:hover {
  background: #f1f5f9;
  border-color: #cbd5e1;
}

.cq-scale-btn.active {
  background: #6366f1;
  border-color: #6366f1;
  color: white;
}

/* 是非题 */
.cq-yesno-container {
  display: flex;
  gap: 16px;
}

.cq-yesno-btn {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  padding: 24px 16px;
  background: #f8fafc;
  border: 2px solid #e2e8f0;
  border-radius: 16px;
  cursor: pointer;
  transition: all 0.2s;
}

.cq-yesno-btn i {
  font-size: 28px;
}

.cq-yesno-btn span {
  font-size: 15px;
  font-weight: 500;
}

.cq-yesno-btn.yes:hover {
  background: #f0fdf4;
  border-color: #86efac;
}

.cq-yesno-btn.no:hover {
  background: #fef2f2;
  border-color: #fca5a5;
}

.cq-yesno-btn.yes.active {
  background: #22c55e;
  border-color: #22c55e;
  color: white;
}

.cq-yesno-btn.no.active {
  background: #ef4444;
  border-color: #ef4444;
  color: white;
}

/* 二选一 */
.cq-choice-container {
  display: flex;
  align-items: center;
  gap: 12px;
}

.cq-choice-btn {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  padding: 20px 16px;
  background: #f8fafc;
  border: 2px solid #e2e8f0;
  border-radius: 16px;
  cursor: pointer;
  transition: all 0.2s;
}

.cq-choice-btn:hover {
  background: #f1f5f9;
  border-color: #cbd5e1;
}

.cq-choice-btn.active {
  background: #eef2ff;
  border-color: #6366f1;
}

.choice-letter {
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #6366f1, #8b5cf6);
  color: white;
  font-weight: 700;
  font-size: 16px;
  border-radius: 8px;
}

.choice-text {
  font-size: 13px;
  color: #334155;
  text-align: center;
}

.choice-vs {
  font-size: 12px;
  font-weight: 600;
  color: #94a3b8;
}

/* 底部提示 */
.preview-footer {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 12px;
  background: #f1f5f9;
  font-size: 12px;
  color: #64748b;
}

.preview-footer i {
  color: #6366f1;
}
</style>

