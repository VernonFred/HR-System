<script setup lang="ts">
/**
 * 题目编辑器面板
 * 包含控件库和题目列表
 */
import { ref, computed } from 'vue'

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
  questions: EditorQuestion[]
}>()

// ===== Emits =====
const emit = defineEmits<{
  (e: 'add-question', type: EditorQuestion['type']): void
  (e: 'edit-question', index: number): void
  (e: 'delete-question', index: number): void
  (e: 'move-question', index: number, direction: 'up' | 'down'): void
  (e: 'open-add-modal'): void
}>()

// ===== 状态 =====
const isDragOver = ref(false)

// ===== 方法 =====
const getQuestionTypeName = (type: string) => {
  const ctrl = questionControls.find(c => c.type === type)
  return ctrl?.label || type
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
      emit('add-question', type)
    }
  }
}

// 导出控件配置供外部使用
defineExpose({ questionControls })
</script>

<template>
  <div class="editor-layout-2col">
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
          @click="emit('add-question', ctrl.type as EditorQuestion['type'])"
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
        <span class="question-count">{{ questions.length }} 道题</span>
      </div>
      
      <div class="questions-list-scroll">
        <div v-if="questions.length === 0" class="empty-questions">
          <i class="ri-file-add-line"></i>
          <p>暂无题目</p>
          <p class="text-muted">从左侧拖拽控件添加题目</p>
        </div>
        
        <div 
          v-for="(q, index) in questions" 
          :key="q.id" 
          class="question-list-item"
        >
          <div class="question-drag-handle">
            <i class="ri-draggable"></i>
          </div>
          <div class="question-item-content">
            <div class="question-item-header">
              <span class="question-number">{{ index + 1 }}</span>
              <span class="question-type-badge" :class="q.type">{{ getQuestionTypeName(q.type) }}</span>
              <span v-if="q.required" class="required-badge">必答</span>
            </div>
            <p class="question-text-preview">{{ q.text || '未填写题目内容' }}</p>
          </div>
          <div class="question-item-actions">
            <button class="btn-icon-small" @click="emit('move-question', index, 'up')" :disabled="index === 0" title="上移">
              <i class="ri-arrow-up-s-line"></i>
            </button>
            <button class="btn-icon-small" @click="emit('move-question', index, 'down')" :disabled="index === questions.length - 1" title="下移">
              <i class="ri-arrow-down-s-line"></i>
            </button>
            <button class="btn-icon-small" @click="emit('edit-question', index)" title="编辑">
              <i class="ri-edit-line"></i>
            </button>
            <button class="btn-icon-small btn-danger" @click="emit('delete-question', index)" title="删除">
              <i class="ri-delete-bin-line"></i>
            </button>
          </div>
        </div>
      </div>
      
      <button class="btn-add-question" @click="emit('open-add-modal')">
        <i class="ri-add-line"></i>
        添加题目
      </button>
    </div>
  </div>
</template>

<style scoped>
.editor-layout-2col {
  display: grid;
  grid-template-columns: 200px 1fr;
  height: 100%;
  gap: 0;
}

/* ===== 控件库面板 ===== */
.controls-library-panel {
  background: #f8fafc;
  border-right: 1px solid #e2e8f0;
  display: flex;
  flex-direction: column;
}

.panel-header {
  padding: 16px 20px;
  border-bottom: 1px solid #e2e8f0;
}

.panel-header h4 {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  font-weight: 600;
  color: #475569;
  margin: 0;
}

.panel-header h4 i {
  color: #6366f1;
}

.controls-list {
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.control-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 16px;
  background: white;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  cursor: pointer;
  transition: all 0.2s;
  font-size: 14px;
  color: #475569;
}

.control-item:hover {
  border-color: #6366f1;
  background: #f5f3ff;
  color: #6366f1;
  transform: translateX(4px);
}

.control-item i {
  font-size: 18px;
}

/* ===== 题目列表面板 ===== */
.questions-list-panel {
  display: flex;
  flex-direction: column;
  background: white;
}

.questions-list-panel.drag-over {
  background: #f5f3ff;
}

.questions-list-panel .panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.question-count {
  padding: 4px 12px;
  background: #f1f5f9;
  border-radius: 20px;
  font-size: 13px;
  color: #64748b;
}

.questions-list-scroll {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
}

.empty-questions {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px 20px;
  color: #94a3b8;
  text-align: center;
  border: 2px dashed #e2e8f0;
  border-radius: 12px;
  margin: 20px;
}

.empty-questions i {
  font-size: 48px;
  margin-bottom: 16px;
  color: #cbd5e1;
}

.empty-questions p {
  margin: 4px 0;
}

.empty-questions .text-muted {
  font-size: 13px;
}

.question-list-item {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 16px;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  margin-bottom: 12px;
  transition: all 0.2s;
}

.question-list-item:hover {
  border-color: #c7d2fe;
  box-shadow: 0 2px 8px rgba(99, 102, 241, 0.1);
}

.question-drag-handle {
  color: #cbd5e1;
  cursor: grab;
  padding: 4px;
}

.question-item-content {
  flex: 1;
  min-width: 0;
}

.question-item-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.question-number {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 24px;
  height: 24px;
  background: linear-gradient(135deg, #6366f1, #8b5cf6);
  color: white;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 600;
}

.question-type-badge {
  padding: 2px 8px;
  background: #f1f5f9;
  border-radius: 4px;
  font-size: 12px;
  color: #64748b;
}

.required-badge {
  padding: 2px 8px;
  background: #fef3c7;
  color: #d97706;
  border-radius: 4px;
  font-size: 12px;
}

.question-text-preview {
  font-size: 14px;
  color: #334155;
  margin: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.question-item-actions {
  display: flex;
  gap: 4px;
}

.btn-icon-small {
  width: 28px;
  height: 28px;
  border: none;
  background: transparent;
  border-radius: 6px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #94a3b8;
  font-size: 16px;
  transition: all 0.2s;
}

.btn-icon-small:hover:not(:disabled) {
  background: #f1f5f9;
  color: #475569;
}

.btn-icon-small:disabled {
  opacity: 0.3;
  cursor: not-allowed;
}

.btn-icon-small.btn-danger:hover:not(:disabled) {
  background: #fee2e2;
  color: #ef4444;
}

.btn-add-question {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  width: calc(100% - 32px);
  margin: 0 16px 16px;
  padding: 14px;
  background: linear-gradient(135deg, #6366f1, #8b5cf6);
  color: white;
  border: none;
  border-radius: 10px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-add-question:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(99, 102, 241, 0.3);
}
</style>

