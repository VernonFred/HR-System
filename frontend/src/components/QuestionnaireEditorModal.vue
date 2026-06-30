<script setup lang="ts">
/**
 * 问卷编辑器弹窗
 *
 * 功能：
 * 1. 创建新问卷
 * 2. 编辑现有问卷
 * 3. 题目管理（添加/编辑/删除/排序）
 * 4. 评分配置
 * 5. 候选人视角预览
 */
import { ref, computed, onMounted, watch } from 'vue'
import { useAuthStore } from '../stores/auth'
import CandidatePreviewPanel from './CandidatePreviewPanel.vue'
import QuestionEditDialog, { type EditorQuestion } from './QuestionEditDialog.vue'
import {
  createQuestionnaire,
  updateQuestionnaire,
  fetchQuestionnaireDetail,
  type Questionnaire,
  type QuestionnaireCreate,
  type QuestionnaireDetail,
  type QuestionnaireImportResponse,
} from '../api/assessments'

// ===== Props =====
const props = defineProps<{
  questionnaire: Questionnaire | null
  importedData?: QuestionnaireImportResponse | null  // V43: 导入的问卷数据
}>()

// ===== Emits =====
const emit = defineEmits<{
  (e: 'close'): void
  (e: 'save'): void
}>()

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

// ===== 状态 =====
const isEdit = computed(() => !!props.questionnaire)
const loading = ref(false)
const editorStep = ref<'info' | 'questions'>('info')
const authStore = useAuthStore()
const questionsMeta = ref<Record<string, any>>({})

// 表单数据
const form = ref({
  name: '',
  creator: '',
  type: 'CUSTOM',
  category: 'scored',
  description: '',
  estimated_minutes: 10,
  purpose: 'assessment' as 'survey' | 'assessment',
  // 评分配置
  simpleScoring: {
    totalScore: 100,
    passingScore: 60,
  },
  gradeConfig: [
    { grade: 'A', label: '优秀', minScore: 90, maxScore: 100 },
    { grade: 'B', label: '良好', minScore: 75, maxScore: 89 },
    { grade: 'C', label: '中等', minScore: 60, maxScore: 74 },
    { grade: 'D', label: '待提升', minScore: 0, maxScore: 59 },
  ],
})

const scoringEnabled = ref(true)

const setScoringEnabled = (enabled: boolean) => {
  scoringEnabled.value = enabled
  form.value.category = enabled ? 'scored' : 'survey'
  form.value.purpose = enabled ? 'assessment' : 'survey'
}

// 题目列表
const editorQuestions = ref<EditorQuestion[]>([])

// 分页状态
const questionsPageSize = ref(6)  // 每页显示数量
const questionsCurrentPage = ref(1)  // 当前页码

// 拖拽状态
const isDragOver = ref(false)

// 添加/编辑题目弹窗
const showAddQuestionModal = ref(false)
const editingQuestionIndex = ref<number | null>(null)
const editingQuestion = ref<EditorQuestion | null>(null)

// 删除题目确认弹窗
const showDeleteQuestionModal = ref(false)
const deleteQuestionIndex = ref<number | null>(null)

// 预览状态
const previewIndex = ref(0)
const previewAnswer = ref('')
const previewAnswerMulti = ref<string[]>([])
const previewScaleValue = ref<number | null>(null)
const previewYesno = ref('')
const previewChoice = ref('')

// ===== 计算属性 =====
const canGoNext = computed(() => {
  return form.value.name.trim() !== ''
})

// 分页计算
const paginatedQuestions = computed(() => {
  const start = (questionsCurrentPage.value - 1) * questionsPageSize.value
  const end = start + questionsPageSize.value
  return editorQuestions.value.slice(start, end)
})

const totalPages = computed(() => {
  return Math.ceil(editorQuestions.value.length / questionsPageSize.value) || 1
})

// 智能分页：当页数多时折叠显示
const visiblePages = computed(() => {
  const total = totalPages.value
  const current = questionsCurrentPage.value

  if (total <= 7) {
    // 页数少于7，全部显示
    return Array.from({ length: total }, (_, i) => i + 1)
  }

  const pages: (number | string)[] = []

  // 始终显示第一页
  pages.push(1)

  if (current > 3) {
    pages.push('...')
  }

  // 显示当前页附近的页码
  const start = Math.max(2, current - 1)
  const end = Math.min(total - 1, current + 1)

  for (let i = start; i <= end; i++) {
    if (!pages.includes(i)) {
      pages.push(i)
    }
  }

  if (current < total - 2) {
    pages.push('...')
  }

  // 始终显示最后一页
  if (!pages.includes(total)) {
    pages.push(total)
  }

  return pages
})

// 分页操作
const goToPage = (page: number) => {
  if (page >= 1 && page <= totalPages.value) {
    questionsCurrentPage.value = page
  }
}

// 监听题目数量变化，自动调整当前页
watch(() => editorQuestions.value.length, (newLength) => {
  const maxPage = Math.ceil(newLength / questionsPageSize.value) || 1
  if (questionsCurrentPage.value > maxPage) {
    questionsCurrentPage.value = maxPage
  }
})

// ===== 方法 =====
const close = () => {
  emit('close')
}

const goToInfoStep = () => {
  editorStep.value = 'info'
}

const goToQuestionsStep = () => {
  if (!form.value.name.trim()) return
  editorStep.value = 'questions'
}

// 获取题型名称
const getQuestionTypeName = (type: string) => {
  const ctrl = questionControls.find(c => c.type === type)
  return ctrl?.label || type
}

// 获取全局索引（基于分页）
const getGlobalIndex = (localIndex: number) => {
  return (questionsCurrentPage.value - 1) * questionsPageSize.value + localIndex
}

// 生成唯一ID
const generateId = () => {
  return `q_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
}

// 从控件添加题目
const addQuestionFromDrag = (type: EditorQuestion['type']) => {
  const question: EditorQuestion = {
    id: generateId(),
    type,
    text: `请输入${getQuestionTypeName(type)}内容`,
    required: true,
  }

  if (type === 'radio' || type === 'checkbox') {
    question.options = [
      { label: '选项1', value: 'opt1' },
      { label: '选项2', value: 'opt2' },
    ]
  } else if (type === 'scale') {
    question.scale = { min: 1, max: 5, minLabel: '非常不满意', maxLabel: '非常满意' }
  } else if (type === 'choice') {
    question.optionA = '选项A'
    question.optionB = '选项B'
  }

  editorQuestions.value.push(question)
  previewIndex.value = editorQuestions.value.length - 1
}

// 打开添加题目弹窗
const openAddQuestionModal = () => {
  editingQuestionIndex.value = null
  editingQuestion.value = null
  showAddQuestionModal.value = true
}

// 打开编辑题目弹窗
const openEditQuestionModal = (index: number) => {
  editingQuestionIndex.value = index
  editingQuestion.value = editorQuestions.value[index]
  showAddQuestionModal.value = true
}

// 保存题目（从子组件接收）
const handleSaveQuestion = (question: EditorQuestion) => {
  if (editingQuestionIndex.value !== null) {
    editorQuestions.value[editingQuestionIndex.value] = question
  } else {
    editorQuestions.value.push(question)
  }
  showAddQuestionModal.value = false
}

// 打开删除题目确认弹窗
const openDeleteQuestionModal = (index: number) => {
  deleteQuestionIndex.value = index
  showDeleteQuestionModal.value = true
}

// 确认删除题目
const confirmDeleteQuestion = () => {
  if (deleteQuestionIndex.value !== null) {
    editorQuestions.value.splice(deleteQuestionIndex.value, 1)
    if (previewIndex.value >= editorQuestions.value.length) {
      previewIndex.value = Math.max(0, editorQuestions.value.length - 1)
    }
  }
  showDeleteQuestionModal.value = false
  deleteQuestionIndex.value = null
}

// 取消删除题目
const cancelDeleteQuestion = () => {
  showDeleteQuestionModal.value = false
  deleteQuestionIndex.value = null
}

// 移动题目
const moveQuestion = (index: number, direction: 'up' | 'down') => {
  const newIndex = direction === 'up' ? index - 1 : index + 1
  if (newIndex < 0 || newIndex >= editorQuestions.value.length) return

  const temp = editorQuestions.value[index]
  editorQuestions.value[index] = editorQuestions.value[newIndex]
  editorQuestions.value[newIndex] = temp
}


// 拖拽处理
const handleControlDragStart = (e: DragEvent, type: string) => {
  if (e.dataTransfer) {
    e.dataTransfer.setData('questionType', type)
  }
}

const handleControlDragEnd = () => {
  isDragOver.value = false
}

const handleListDragOver = (e: DragEvent) => {
  isDragOver.value = true
}

const handleListDrop = (e: DragEvent) => {
  isDragOver.value = false
  if (e.dataTransfer) {
    const type = e.dataTransfer.getData('questionType') as EditorQuestion['type']
    if (type) {
      addQuestionFromDrag(type)
    }
  }
}

// 保存问卷
const save = async () => {
  if (!form.value.name.trim()) {
    alert('请输入问卷名称')
    return
  }

  loading.value = true
  try {
    // 构建问卷数据
    const questionsData = editorQuestions.value.map((q, idx) => ({
      id: q.id,
      type: q.type,
      text: q.text,
      required: q.required,
      order: idx + 1,
      // 🟢 确保选项数据包含 allow_custom 字段（后端使用蛇形命名）
      options: q.options?.map(opt => ({
        ...opt,
        allow_custom: opt.allowCustom,  // 转换为蛇形命名
      })),
      scale: q.scale,
      optionA: q.optionA,
      optionB: q.optionB,
      scoreA: q.scoreA,
      scoreB: q.scoreB,
    }))

    // 是否启用评分配置
    const category = scoringEnabled.value ? 'scored' : 'survey'
    const customType = scoringEnabled.value ? 'scored' : 'non_scored'
    const scoringConfig = scoringEnabled.value ? {
      totalScore: form.value.simpleScoring.totalScore,
      passingScore: form.value.simpleScoring.passingScore,
      gradeConfig: form.value.gradeConfig,
    } : {}

    const data: QuestionnaireCreate = {
      name: form.value.name,
      type: form.value.type,
      category: category,
      description: form.value.description,
      questions_count: editorQuestions.value.length,
      estimated_minutes: form.value.estimated_minutes,
      questions_data: {
        questions: questionsData,
        meta: {
          ...questionsMeta.value,
          creator: form.value.creator,
        },
      },
      scoring_rules: {},
      custom_type: customType,
      scoring_config: scoringConfig,
      purpose: scoringEnabled.value ? 'assessment' : 'survey',
    }

    if (isEdit.value && props.questionnaire) {
      await updateQuestionnaire(props.questionnaire.id, data)
    } else {
      await createQuestionnaire(data)
    }

    emit('save')
  } catch (error) {
    console.error('保存失败:', error)
    alert('保存失败，请重试')
  } finally {
    loading.value = false
  }
}

// ===== 生命周期 =====
onMounted(async () => {
  if (!form.value.creator) {
    form.value.creator = authStore.username || 'Admin'
  }
  // V43: 处理导入的问卷数据
  if (props.importedData && props.importedData.questions.length > 0) {
    const { metadata, questions } = props.importedData

    // 填充元数据
    form.value.name = metadata.name || '导入的问卷'
    form.value.description = metadata.description || ''
    form.value.estimated_minutes = metadata.estimated_minutes || 15
    if (metadata.creator) {
      form.value.creator = metadata.creator
    }
    questionsMeta.value = { ...(metadata || {}) }

    // 转换题目格式 - V45: 修复选项格式转换
    editorQuestions.value = questions.map((q, idx) => {
      const mappedType = mapImportedQuestionType(q.type)

      // 转换选项格式：导入的是 { id, text, score }，编辑器需要 { value, label, score }
      const mappedOptions = q.options?.map((opt, optIdx) => ({
        value: opt.id || String.fromCharCode(65 + optIdx), // A, B, C, D...
        label: opt.text,
        score: opt.score || 0,
        allowCustom: opt.allow_custom,  // 🟢 保留自定义输入标记
        placeholder: opt.placeholder,    // 🟢 保留占位符
      })) || []

      return {
      id: q.id || generateId(),
        type: mappedType as EditorQuestion['type'],
      text: q.text,
      required: q.required !== false,
        options: mappedOptions,
        // 量表题配置
        scale: mappedType === 'scale' ? { min: 1, max: 5, minLabel: '非常不满意', maxLabel: '非常满意' } : undefined,
      }
    })

    // 如果有评分题，自动切换到评分问卷模式
    const hasScoring = questions.some(q =>
      q.options?.some(opt => opt.score > 0) || q.type === 'rating'
    )
    setScoringEnabled(hasScoring)

    // 直接跳转到题目编辑步骤
    editorStep.value = 'questions'

    console.log('✅ 导入问卷数据已加载:', editorQuestions.value.length, '道题目')
    return
  }

  if (props.questionnaire) {
    // 编辑模式：加载问卷详情
    form.value.name = props.questionnaire.name
    form.value.type = props.questionnaire.type || 'CUSTOM'
    form.value.description = (props.questionnaire as any).description || ''
    form.value.estimated_minutes = props.questionnaire.estimated_minutes || 10

    // 加载详细数据
    try {
      const detail = await fetchQuestionnaireDetail(props.questionnaire.id)
      if (detail.questions_data?.questions) {
        editorQuestions.value = detail.questions_data.questions.map((q: any) => ({
          id: q.id || generateId(),
          type: q.type,
          text: q.text,
          required: q.required !== false,
          options: q.options,
          scale: q.scale,
          optionA: q.optionA,
          optionB: q.optionB,
          scoreA: q.scoreA,
          scoreB: q.scoreB,
        }))
      }

      if (detail.questions_data?.meta) {
        questionsMeta.value = { ...detail.questions_data.meta }
        if (detail.questions_data.meta.creator) {
          form.value.creator = detail.questions_data.meta.creator
        }
      }

      const scored = detail.category === 'scored' || (detail as any).custom_type === 'scored'
      setScoringEnabled(scored)

      // 加载评分配置
      const scoringConfig = (detail as any).scoring_config
      if (scored && scoringConfig) {
        if (scoringConfig.totalScore) {
          form.value.simpleScoring.totalScore = scoringConfig.totalScore
        }
        if (scoringConfig.passingScore) {
          form.value.simpleScoring.passingScore = scoringConfig.passingScore
        }
        if (scoringConfig.gradeConfig) {
          form.value.gradeConfig = scoringConfig.gradeConfig
        }
      }
    } catch (error) {
      console.error('加载问卷详情失败:', error)
    }
  }
})

// V43: 映射导入的题目类型到编辑器类型
const mapImportedQuestionType = (importType: string): string => {
  const typeMap: Record<string, string> = {
    'single': 'radio',
    'multiple': 'checkbox',
    'text': 'text',
    'textarea': 'textarea',
    'rating': 'scale',
  }
  return typeMap[importType] || 'radio'
}

// 监听预览索引变化，重置预览状态
watch(previewIndex, () => {
  previewAnswer.value = ''
  previewAnswerMulti.value = []
  previewScaleValue.value = null
  previewYesno.value = ''
  previewChoice.value = ''
})
</script>

<template>
  <div class="modal-overlay" @click="close">
    <div class="modal-dialog modal-editor" @click.stop>
      <!-- 头部 -->
      <div class="modal-header editor-header">
        <div class="editor-header-left">
          <h3><i class="ri-file-edit-line"></i> {{ isEdit ? '编辑问卷' : '创建问卷' }}</h3>
          <div class="editor-steps">
            <span :class="['step-item', { active: editorStep === 'info' }]" @click="goToInfoStep">
              <i class="ri-information-line"></i> 基本信息
            </span>
            <i class="ri-arrow-right-s-line step-arrow"></i>
            <span :class="['step-item', { active: editorStep === 'questions' }]">
              <i class="ri-list-check-2"></i> 题目编辑
            </span>
          </div>
        </div>
        <button class="btn-close" @click="close">
          <i class="ri-close-line"></i>
        </button>
      </div>

      <!-- 主体 -->
      <div class="modal-body editor-body">
        <!-- Step 1: 基本信息 -->
        <div v-if="editorStep === 'info'" class="editor-step-content">
          <div class="create-form">
            <div class="form-group">
              <label class="form-label">问卷名称 <span class="required">*</span></label>
              <input
                type="text"
                class="form-input"
                v-model="form.name"
                placeholder="请输入问卷名称"
              />
            </div>

            <div class="form-group">
              <label class="form-label">问卷创建人</label>
              <input
                type="text"
                class="form-input"
                v-model="form.creator"
                placeholder="请输入创建人（选填）"
              />
            </div>

              <div class="form-group">
                <label class="form-label">预计时长</label>
                <div class="input-with-suffix">
                  <input
                    type="number"
                    class="form-input"
                    v-model.number="form.estimated_minutes"
                    min="1"
                    max="120"
                    placeholder="10"
                  />
                  <span class="input-suffix">分钟</span>
              </div>
            </div>

            <div class="form-group">
              <label class="form-label">问卷描述</label>
              <textarea
                class="form-textarea"
                rows="3"
                v-model="form.description"
                placeholder="请输入问卷描述（选填）"
              ></textarea>
            </div>

            <!-- 评分配置 -->
            <div class="scoring-config-section">
              <div class="config-section-header">
                <h4><i class="ri-settings-4-line"></i> 评分配置</h4>
                <div class="scoring-toggle">
                  <button
                    type="button"
                    class="toggle-btn"
                    :class="{ active: scoringEnabled }"
                    @click="setScoringEnabled(true)"
                  >
                    开启
                  </button>
                  <button
                    type="button"
                    class="toggle-btn"
                    :class="{ active: !scoringEnabled }"
                    @click="setScoringEnabled(false)"
                  >
                    不开启
                  </button>
                </div>
              </div>

              <div v-if="scoringEnabled" class="scoring-config-card">
                <div class="config-row">
                  <div class="form-group">
                    <label class="form-label">满分</label>
                    <div class="input-with-suffix">
                      <input
                        type="number"
                        class="form-input"
                        v-model.number="form.simpleScoring.totalScore"
                        min="1"
                        max="1000"
                      />
                      <span class="input-suffix">分</span>
                    </div>
                  </div>
                  <div class="form-group">
                    <label class="form-label">及格分</label>
                    <div class="input-with-suffix">
                      <input
                        type="number"
                        class="form-input"
                        v-model.number="form.simpleScoring.passingScore"
                        min="0"
                        :max="form.simpleScoring.totalScore"
                      />
                      <span class="input-suffix">分</span>
                    </div>
                  </div>
                </div>

                <!-- 等级配置 -->
                <div class="grade-config">
                  <label class="form-label">等级配置</label>
                  <div class="grade-table">
                    <div class="grade-row header">
                      <span class="grade-col grade">等级</span>
                      <span class="grade-col label">标签</span>
                      <span class="grade-col range">分数范围</span>
                    </div>
                    <div
                      v-for="(g, idx) in form.gradeConfig"
                      :key="idx"
                      class="grade-row"
                      :class="`grade-${g.grade.toLowerCase()}`"
                    >
                      <span class="grade-col grade">
                        <span class="grade-badge" :class="`grade-${g.grade.toLowerCase()}`">{{ g.grade }}</span>
                      </span>
                      <span class="grade-col label">
                        <input type="text" v-model="g.label" class="grade-input" />
                      </span>
                      <span class="grade-col range">
                        <input type="number" v-model.number="g.minScore" class="grade-input small" min="0" />
                        <span class="range-sep">~</span>
                        <input type="number" v-model.number="g.maxScore" class="grade-input small" :max="form.simpleScoring.totalScore" />
                        <span class="range-unit">分</span>
                      </span>
                    </div>
                  </div>
                </div>
              </div>
              <div v-else class="scoring-config-disabled">
                已关闭评分配置，本问卷将按调查问卷处理。
              </div>
            </div>
          </div>

          <!-- 提示 -->
          <div class="custom-tip">
            <i class="ri-lightbulb-line"></i>
            <span>{{ scoringEnabled ? '请在下一步中添加题目并配置评分' : '请在下一步中添加题目' }}</span>
          </div>
        </div>

        <!-- Step 2: 题目编辑 -->
        <div v-if="editorStep === 'questions'" class="editor-step-content questions-editor">
          <div class="editor-layout-3col">
            <!-- 左侧：控件库 -->
            <div class="controls-library-panel">
              <div class="panel-header">
                <h4><i class="ri-apps-line"></i> 控件库</h4>
              </div>
              <div class="controls-list">
                <div
                  v-for="ctrl in questionControls"
                  :key="ctrl.type"
                  class="control-item"
                  draggable="true"
                  @click="addQuestionFromDrag(ctrl.type as EditorQuestion['type'])"
                  @dragstart="handleControlDragStart($event, ctrl.type)"
                  @dragend="handleControlDragEnd"
                  :title="`点击或拖拽添加${ctrl.label}`"
                >
                  <i :class="ctrl.icon"></i>
                  <span>{{ ctrl.label }}</span>
                </div>
              </div>
            </div>

            <!-- 中间：题目列表 -->
            <div
              class="questions-list-panel"
              @dragover.prevent="handleListDragOver"
              @drop="handleListDrop"
              @dragleave="isDragOver = false"
              :class="{ 'drag-over': isDragOver }"
            >
              <div class="panel-header">
                <h4><i class="ri-list-ordered"></i> 题目列表</h4>
                <span class="question-count">{{ editorQuestions.length }} 道题</span>
              </div>

              <div class="questions-list-scroll">
                <div v-if="editorQuestions.length === 0" class="empty-questions">
                  <i class="ri-file-add-line"></i>
                  <p>暂无题目</p>
                  <p class="text-muted">从左侧拖拽控件添加题目</p>
                </div>

                <div
                  v-for="(q, localIndex) in paginatedQuestions"
                  :key="q.id"
                  class="question-list-item"
                >
                  <div class="question-drag-handle">
                    <i class="ri-draggable"></i>
                  </div>
                  <div class="question-item-content">
                    <div class="question-item-header">
                      <span class="question-number">{{ (questionsCurrentPage - 1) * questionsPageSize + localIndex + 1 }}</span>
                      <span class="question-type-badge" :class="q.type">{{ getQuestionTypeName(q.type) }}</span>
                      <span v-if="q.required" class="required-badge">必答</span>
                    </div>
                    <p class="question-text-preview">{{ q.text || '未填写题目内容' }}</p>
                  </div>
                  <div class="question-item-actions">
                    <button class="btn-icon-small" @click="moveQuestion(getGlobalIndex(localIndex), 'up')" :disabled="getGlobalIndex(localIndex) === 0" title="上移">
                      <i class="ri-arrow-up-s-line"></i>
                    </button>
                    <button class="btn-icon-small" @click="moveQuestion(getGlobalIndex(localIndex), 'down')" :disabled="getGlobalIndex(localIndex) === editorQuestions.length - 1" title="下移">
                      <i class="ri-arrow-down-s-line"></i>
                    </button>
                    <button class="btn-icon-small" @click="openEditQuestionModal(getGlobalIndex(localIndex))" title="编辑">
                      <i class="ri-edit-line"></i>
                    </button>
                    <button class="btn-icon-small btn-danger" @click="openDeleteQuestionModal(getGlobalIndex(localIndex))" title="删除">
                      <i class="ri-delete-bin-line"></i>
                    </button>
                  </div>
                </div>
              </div>

              <!-- 分页控件 -->
              <div v-if="editorQuestions.length > questionsPageSize" class="questions-pagination">
                <button
                  class="pagination-btn"
                  :disabled="questionsCurrentPage === 1"
                  @click="questionsCurrentPage--"
                >
                  <i class="ri-arrow-left-s-line"></i>
                </button>

                <div class="pagination-pages">
                  <template v-for="(page, idx) in visiblePages" :key="idx">
                    <span v-if="page === '...'" class="pagination-ellipsis">...</span>
                    <button
                      v-else
                      class="pagination-page-btn"
                      :class="{ active: questionsCurrentPage === page }"
                      @click="goToPage(page as number)"
                    >
                      {{ page }}
                    </button>
                  </template>
                </div>

                <button
                  class="pagination-btn"
                  :disabled="questionsCurrentPage >= totalPages"
                  @click="questionsCurrentPage++"
                >
                  <i class="ri-arrow-right-s-line"></i>
                </button>

                <span class="pagination-info">共 {{ editorQuestions.length }} 题</span>
              </div>

              <button class="btn-add-question" @click="openAddQuestionModal">
                <i class="ri-add-line"></i>
                添加题目
              </button>
            </div>

            <!-- 右侧：候选人视角预览 -->
            <CandidatePreviewPanel :questions="editorQuestions" />
          </div>
        </div>
      </div>

      <!-- 底部 -->
      <div class="modal-footer editor-footer">
        <div class="footer-left">
          <span v-if="editorStep === 'questions'" class="questions-summary">
            <i class="ri-file-list-3-line"></i>
            共 {{ editorQuestions.length }} 道题目
          </span>
        </div>
        <div class="footer-right">
          <button v-if="editorStep === 'info'" class="btn-cancel" @click="close">取消</button>
          <button v-if="editorStep === 'questions'" class="btn-secondary" @click="goToInfoStep">
            <i class="ri-arrow-left-line"></i>
            上一步
          </button>
          <button v-if="editorStep === 'info'" class="btn-primary" @click="goToQuestionsStep" :disabled="!canGoNext">
            下一步
            <i class="ri-arrow-right-line"></i>
          </button>
          <button v-if="editorStep === 'questions'" class="btn-primary" @click="save" :disabled="loading || !form.name.trim()">
            <i v-if="loading" class="ri-loader-4-line animate-spin"></i>
            <i v-else class="ri-check-line"></i>
            {{ loading ? (isEdit ? '保存中...' : '创建中...') : (isEdit ? '保存问卷' : '创建问卷') }}
          </button>
        </div>
      </div>
    </div>
  </div>

  <!-- 添加/编辑题目弹窗 -->
  <QuestionEditDialog
    v-if="showAddQuestionModal"
    :question="editingQuestion"
    :is-edit="editingQuestionIndex !== null"
    @close="showAddQuestionModal = false"
    @save="handleSaveQuestion"
  />

  <!-- 删除题目确认弹窗 -->
  <div v-if="showDeleteQuestionModal" class="modal-overlay delete-confirm-overlay" @click="cancelDeleteQuestion">
    <div class="modal-dialog modal-confirm" @click.stop>
      <div class="modal-header confirm-header">
        <div class="confirm-icon danger">
          <i class="ri-delete-bin-line"></i>
        </div>
        <h3>确认删除</h3>
      </div>
      <div class="modal-body confirm-body">
        <p>确定要删除第 <strong>{{ deleteQuestionIndex !== null ? deleteQuestionIndex + 1 : '' }}</strong> 道题目吗？</p>
        <p class="confirm-warning">
          <i class="ri-error-warning-line"></i>
          此操作不可恢复
        </p>
      </div>
      <div class="modal-footer confirm-footer">
        <button class="btn-cancel" @click="cancelDeleteQuestion">取消</button>
        <button class="btn-danger" @click="confirmDeleteQuestion">
          <i class="ri-delete-bin-line"></i>
          确认删除
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
@import './styles/questionnaire-editor-modal.css';
</style>
