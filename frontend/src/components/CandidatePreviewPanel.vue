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
import {
  getCheckboxMaxSelections,
  toggleCheckboxSelection,
} from '../utils/checkboxSelectionLimit'

// ===== 类型定义 =====
export interface EditorQuestion {
  id: string
  type: 'radio' | 'checkbox' | 'text' | 'textarea' | 'scale' | 'yesno' | 'choice'
  text: string
  required: boolean
  options?: { label: string; value: string; score?: number }[]
  maxSelections?: number | null
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
const previewLimitReached = ref(false)

// ===== 计算属性 =====
const currentQuestion = computed(() => {
  return props.questions[previewIndex.value] || null
})

const scaleRange = computed(() => {
  if (!currentQuestion.value?.scale) return []
  const { min, max } = currentQuestion.value.scale
  return Array.from({ length: max - min + 1 }, (_, i) => min + i)
})

const currentCheckboxMaxSelections = computed(() => {
  if (currentQuestion.value?.type !== 'checkbox') return null
  return getCheckboxMaxSelections(currentQuestion.value)
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
  previewLimitReached.value = false
}

const toggleMultiOption = (value: string) => {
  const result = toggleCheckboxSelection(
    previewAnswerMulti.value,
    value,
    currentCheckboxMaxSelections.value,
  )
  previewLimitReached.value = result.limitReached
  previewAnswerMulti.value = result.selection
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
          <p v-if="currentCheckboxMaxSelections" class="cq-checkbox-limit">
            最多选择 {{ currentCheckboxMaxSelections }} 项
            <span v-if="previewLimitReached">，已达到上限</span>
          </p>
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
@import './styles/candidate-preview-panel.css';
</style>
