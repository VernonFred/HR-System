<template>
  <div class="field-config-panel">
    <div class="panel-header">
      <h4><i class="ri-list-settings-line"></i> 字段配置</h4>
      <span class="field-count">{{ enabledFields.length }} 个启用</span>
    </div>
    
    <!-- 字段列表 -->
    <div class="fields-list">
      <div 
        v-for="(field, index) in modelValue" 
        :key="field.id"
        class="field-item"
        :class="{ 
          'is-disabled': !field.enabled,
          'is-editing': editingFieldId === field.id,
          'is-drag-over': dragState.dropTargetIndex === index && dragState.draggedIndex !== index
        }"
        draggable="true"
        @dragstart="handleDragStart($event, index)"
        @dragover="handleDragOver($event, index)"
        @dragleave="handleDragLeave"
        @dragend="handleDragEnd"
        @drop="handleDrop($event, index)"
      >
        <!-- 拖拽手柄 -->
        <div class="drag-handle" title="拖拽排序">
          <i class="ri-draggable"></i>
        </div>
        
        <!-- 字段主体 -->
        <div class="field-content">
          <div class="field-header">
            <div class="field-check">
              <input 
                type="checkbox" 
                :id="`field-${field.id}`"
                v-model="field.enabled"
                @change="emitUpdate"
              />
              <label :for="`field-${field.id}`">
                <i :class="getFieldIcon(field)" class="field-icon"></i>
                {{ field.label }}
              </label>
            </div>
            <span v-if="field.required" class="badge-required">必填</span>
            
            <!-- 操作按钮组 -->
            <div class="field-actions">
              <button 
                class="btn-action"
                @click="toggleFieldEdit(field.id)"
                :title="editingFieldId === field.id ? '关闭编辑' : '编辑字段'"
              >
                <i :class="editingFieldId === field.id ? 'ri-close-line' : 'ri-pencil-line'"></i>
              </button>
              <button 
                v-if="index > 0"
                class="btn-action"
                @click="moveFieldUp(index)"
                title="上移"
              >
                <i class="ri-arrow-up-line"></i>
              </button>
              <button 
                v-if="index < modelValue.length - 1"
                class="btn-action"
                @click="moveFieldDown(index)"
                title="下移"
              >
                <i class="ri-arrow-down-line"></i>
              </button>
              <button 
                class="btn-action btn-delete"
                @click="removeField(index)"
                title="删除字段"
              >
                <i class="ri-delete-bin-6-line"></i>
              </button>
            </div>
          </div>
        </div>
        
        <!-- 字段编辑面板 -->
        <div v-if="editingFieldId === field.id" class="field-edit-panel">
          <div class="edit-form">
            <!-- 基础信息行 -->
            <div class="edit-row">
              <div class="edit-field">
                <label class="edit-label">字段名称</label>
                <input 
                  type="text" 
                  v-model="field.label" 
                  class="edit-input"
                  placeholder="请输入字段名称"
                  @input="emitUpdate"
                />
              </div>
              <div class="edit-field">
                <label class="edit-label">占位文本</label>
                <input 
                  type="text" 
                  v-model="field.placeholder" 
                  class="edit-input"
                  placeholder="请输入占位文本"
                  @input="emitUpdate"
                />
              </div>
              <div class="edit-field checkbox-field">
                <label class="checkbox-label">
                  <input type="checkbox" v-model="field.required" @change="emitUpdate" />
                  <span>必填</span>
                </label>
              </div>
            </div>
            
            <!-- 选项编辑（仅对select类型） -->
            <div v-if="field.type === 'select' && field.options" class="edit-options">
              <label class="edit-label">选项设置</label>
              <div class="options-list">
                <div v-for="(opt, optIndex) in field.options" :key="optIndex" class="option-row">
                  <input 
                    type="text" 
                    :value="opt"
                    @input="updateFieldOption(field, optIndex, ($event.target as HTMLInputElement).value)"
                    class="option-input"
                    :placeholder="`选项${optIndex + 1}`"
                  />
                  <button 
                    v-if="field.options && field.options.length > 1"
                    class="btn-remove-option"
                    @click="removeFieldOption(field, optIndex)"
                    title="删除选项"
                  >
                    <i class="ri-close-line"></i>
                  </button>
                </div>
                <button class="btn-add-option" @click="addFieldOption(field)">
                  <i class="ri-add-line"></i>
                  添加选项
                </button>
              </div>
            </div>
            
            <!-- 确认按钮 -->
            <div class="edit-actions">
              <button class="btn-confirm" @click="confirmFieldEdit">
                <i class="ri-check-line"></i>
                确认
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
    
    <!-- 添加字段区域 -->
    <div class="add-field-section">
      <button class="btn-add-custom" @click="showAddFieldModal = true">
        <i class="ri-add-circle-line"></i>
        添加自定义字段
      </button>
    </div>
    
    <!-- 添加字段弹窗 -->
    <div v-if="showAddFieldModal" class="field-modal-overlay" @click="showAddFieldModal = false">
      <div class="field-modal" @click.stop>
        <div class="field-modal-header">
          <h4>添加自定义字段</h4>
          <button class="btn-close" @click="showAddFieldModal = false">
            <i class="ri-close-line"></i>
          </button>
        </div>
        <div class="field-modal-body">
          <div class="field-templates">
            <div 
              v-for="template in fieldTemplates" 
              :key="template.name"
              class="template-item"
              @click="addFieldFromTemplate(template)"
            >
              <i :class="template.icon"></i>
              <span>{{ template.label }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'

// 定义字段类型
export interface FormField {
  id: string
  name: string
  label: string
  type: 'text' | 'tel' | 'email' | 'select'
  required: boolean
  builtin: boolean
  enabled: boolean
  placeholder?: string
  options?: string[]
}

// Props
const props = defineProps<{
  modelValue: FormField[]
}>()

// Emits
const emit = defineEmits<{
  (e: 'update:modelValue', value: FormField[]): void
}>()

// 状态
const editingFieldId = ref<string | null>(null)
const showAddFieldModal = ref(false)
const dragState = ref({
  dragging: false,
  draggedIndex: -1,
  dropTargetIndex: -1
})

// 字段模板
const fieldTemplates = [
  { name: 'text', label: '单行文本', type: 'text' as const, icon: 'ri-text', placeholder: '请输入' },
  { name: 'email', label: '邮箱', type: 'email' as const, icon: 'ri-mail-line', placeholder: '请输入邮箱' },
  { name: 'tel', label: '电话', type: 'tel' as const, icon: 'ri-phone-line', placeholder: '请输入电话' },
  { name: 'select', label: '下拉选择', type: 'select' as const, icon: 'ri-arrow-down-s-line', placeholder: '请选择', options: ['选项1', '选项2'] },
]

// 计算属性
const enabledFields = computed(() => props.modelValue.filter(f => f.enabled))

// 方法
const emitUpdate = () => {
  emit('update:modelValue', [...props.modelValue])
}

const getFieldIcon = (field: FormField) => {
  const iconMap: Record<string, string> = {
    text: 'ri-text',
    tel: 'ri-phone-line',
    email: 'ri-mail-line',
    select: 'ri-arrow-down-s-line',
  }
  return iconMap[field.type] || 'ri-input-field'
}

// 切换字段编辑状态
const toggleFieldEdit = (fieldId: string) => {
  editingFieldId.value = editingFieldId.value === fieldId ? null : fieldId
}

// 确认字段编辑
const confirmFieldEdit = () => {
  editingFieldId.value = null
  emitUpdate()
}

// 删除字段
const removeField = (index: number) => {
  const field = props.modelValue[index]
  props.modelValue.splice(index, 1)
  if (editingFieldId.value === field.id) {
    editingFieldId.value = null
  }
  emitUpdate()
}

// 从模板添加字段
const addFieldFromTemplate = (template: typeof fieldTemplates[0]) => {
  const newId = `${template.name}_${Date.now()}`
  const newField: FormField = {
    id: newId,
    name: template.name,
    label: template.label,
    type: template.type,
    required: false,
    builtin: false,
    enabled: true,
    placeholder: template.placeholder,
    options: template.options ? [...template.options] : undefined,
  }
  props.modelValue.push(newField)
  showAddFieldModal.value = false
  emitUpdate()
}

// 字段选项操作
const addFieldOption = (field: FormField) => {
  if (!field.options) {
    field.options = []
  }
  field.options.push(`选项${field.options.length + 1}`)
  emitUpdate()
}

const updateFieldOption = (field: FormField, index: number, value: string) => {
  if (field.options && field.options[index] !== undefined) {
    field.options[index] = value
    emitUpdate()
  }
}

const removeFieldOption = (field: FormField, index: number) => {
  if (field.options && field.options.length > 1) {
    field.options.splice(index, 1)
    emitUpdate()
  }
}

// 拖拽排序
const handleDragStart = (e: DragEvent, index: number) => {
  dragState.value.dragging = true
  dragState.value.draggedIndex = index
  if (e.dataTransfer) {
    e.dataTransfer.effectAllowed = 'move'
    e.dataTransfer.setData('text/plain', String(index))
  }
  (e.target as HTMLElement).classList.add('is-dragging')
}

const handleDragOver = (e: DragEvent, index: number) => {
  e.preventDefault()
  if (e.dataTransfer) {
    e.dataTransfer.dropEffect = 'move'
  }
  dragState.value.dropTargetIndex = index
}

const handleDragLeave = () => {
  setTimeout(() => {
    if (dragState.value.dropTargetIndex !== -1) {
      dragState.value.dropTargetIndex = -1
    }
  }, 50)
}

const handleDragEnd = (e: DragEvent) => {
  (e.target as HTMLElement).classList.remove('is-dragging')
  dragState.value.dragging = false
  dragState.value.draggedIndex = -1
  dragState.value.dropTargetIndex = -1
}

const handleDrop = (e: DragEvent, dropIndex: number) => {
  e.preventDefault()
  const dragIndex = dragState.value.draggedIndex
  
  if (dragIndex !== -1 && dragIndex !== dropIndex) {
    const draggedItem = props.modelValue[dragIndex]
    props.modelValue.splice(dragIndex, 1)
    props.modelValue.splice(dropIndex, 0, draggedItem)
    emitUpdate()
  }
  
  dragState.value.dragging = false
  dragState.value.draggedIndex = -1
  dragState.value.dropTargetIndex = -1
}

// 上移字段
const moveFieldUp = (index: number) => {
  if (index > 0) {
    const temp = props.modelValue[index]
    props.modelValue.splice(index, 1)
    props.modelValue.splice(index - 1, 0, temp)
    emitUpdate()
  }
}

// 下移字段
const moveFieldDown = (index: number) => {
  if (index < props.modelValue.length - 1) {
    const temp = props.modelValue[index]
    props.modelValue.splice(index, 1)
    props.modelValue.splice(index + 1, 0, temp)
    emitUpdate()
  }
}
</script>

<style scoped>
.field-config-panel {
  display: flex;
  flex-direction: column;
  background: #f9fafb;
  border-radius: 12px;
  overflow: hidden;
  height: 100%;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem 1.25rem;
  background: white;
  border-bottom: 1px solid #e5e7eb;
}

.panel-header h4 {
  margin: 0;
  font-size: 0.9375rem;
  font-weight: 600;
  color: #1f2937;
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.panel-header h4 i {
  color: #7c3aed;
}

.field-count {
  font-size: 0.75rem;
  color: #6b7280;
  background: #f3f4f6;
  padding: 0.25rem 0.75rem;
  border-radius: 20px;
}

/* 字段列表 */
.fields-list {
  flex: 1;
  overflow-y: auto;
  padding: 0.75rem;
}

.field-item {
  display: flex;
  flex-direction: column;
  background: white;
  border: 1.5px solid #e5e7eb;
  border-radius: 10px;
  margin-bottom: 0.5rem;
  transition: all 0.2s ease;
}

.field-item:hover {
  border-color: #c4b5fd;
  box-shadow: 0 2px 8px rgba(124, 58, 237, 0.08);
}

.field-item.is-disabled {
  opacity: 0.5;
  background: #f9fafb;
}

.field-item.is-drag-over {
  border-color: #7c3aed;
  border-style: dashed;
  background: #f5f3ff;
}

.field-item.is-dragging {
  opacity: 0.5;
  transform: scale(0.98);
}

/* 拖拽手柄 */
.drag-handle {
  padding: 0.5rem 0.75rem;
  cursor: grab;
  color: #9ca3af;
  display: flex;
  align-items: center;
  justify-content: center;
  border-bottom: 1px solid #f3f4f6;
}

.drag-handle:hover {
  color: #7c3aed;
  background: #f5f3ff;
}

.drag-handle:active {
  cursor: grabbing;
}

/* 字段内容 */
.field-content {
  padding: 0.625rem 0.875rem;
}

.field-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
}

.field-check {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  flex: 1;
}

.field-check input[type="checkbox"] {
  width: 18px;
  height: 18px;
  cursor: pointer;
  accent-color: #7c3aed;
}

.field-check label {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-weight: 500;
  color: #374151;
  cursor: pointer;
  margin: 0;
}

.field-icon {
  color: #7c3aed;
  font-size: 1rem;
}

.badge-required {
  padding: 0.125rem 0.5rem;
  background: #fee2e2;
  color: #dc2626;
  font-size: 0.75rem;
  font-weight: 600;
  border-radius: 4px;
}

/* 字段操作按钮 */
.field-actions {
  display: flex;
  gap: 0.25rem;
}

.btn-action {
  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: transparent;
  border: none;
  color: #9ca3af;
  cursor: pointer;
  border-radius: 6px;
  transition: all 0.15s;
}

.btn-action:hover {
  background: #f3f4f6;
  color: #374151;
}

.btn-action.btn-delete:hover {
  background: #fee2e2;
  color: #dc2626;
}

/* 字段编辑面板 */
.field-edit-panel {
  width: 100%;
  padding: 1rem 1.25rem;
  background: linear-gradient(180deg, #fafbfc 0%, #f5f6f8 100%);
  border-top: 1px solid #e5e7eb;
  animation: slideDown 0.2s ease-out;
}

@keyframes slideDown {
  from {
    opacity: 0;
    transform: translateY(-8px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.edit-form {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.edit-row {
  display: flex;
  gap: 1rem;
  align-items: flex-end;
}

.edit-field {
  flex: 1;
}

.edit-label {
  display: block;
  font-size: 0.75rem;
  font-weight: 500;
  color: #6b7280;
  margin-bottom: 0.375rem;
}

.edit-input {
  width: 100%;
  padding: 0.5rem 0.75rem;
  border: 1px solid #e5e7eb;
  border-radius: 6px;
  font-size: 0.875rem;
  transition: all 0.15s;
}

.edit-input:focus {
  outline: none;
  border-color: #7c3aed;
  box-shadow: 0 0 0 3px rgba(124, 58, 237, 0.1);
}

.checkbox-field {
  flex: 0 0 auto;
}

.checkbox-label {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  cursor: pointer;
  font-size: 0.875rem;
  color: #374151;
}

.checkbox-label input {
  accent-color: #7c3aed;
}

/* 选项编辑 */
.edit-options {
  margin-top: 0.5rem;
}

.options-list {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.option-row {
  display: flex;
  gap: 0.5rem;
  align-items: center;
}

.option-input {
  flex: 1;
  padding: 0.5rem 0.75rem;
  border: 1px solid #e5e7eb;
  border-radius: 6px;
  font-size: 0.875rem;
}

.option-input:focus {
  outline: none;
  border-color: #7c3aed;
}

.btn-remove-option {
  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: transparent;
  border: none;
  color: #9ca3af;
  cursor: pointer;
  border-radius: 6px;
}

.btn-remove-option:hover {
  background: #fee2e2;
  color: #dc2626;
}

.btn-add-option {
  display: flex;
  align-items: center;
  gap: 0.25rem;
  padding: 0.375rem 0.75rem;
  background: transparent;
  border: 1px dashed #d1d5db;
  border-radius: 6px;
  color: #6b7280;
  font-size: 0.8125rem;
  cursor: pointer;
  transition: all 0.15s;
}

.btn-add-option:hover {
  border-color: #7c3aed;
  color: #7c3aed;
  background: #f5f3ff;
}

/* 编辑操作按钮 */
.edit-actions {
  display: flex;
  justify-content: flex-end;
  padding-top: 0.75rem;
  border-top: 1px solid #e5e7eb;
  margin-top: 0.5rem;
}

.btn-confirm {
  display: flex;
  align-items: center;
  gap: 0.375rem;
  padding: 0.5rem 1rem;
  background: linear-gradient(135deg, #7c3aed 0%, #6d28d9 100%);
  border: none;
  border-radius: 6px;
  color: white;
  font-size: 0.875rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-confirm:hover {
  background: linear-gradient(135deg, #6d28d9 0%, #5b21b6 100%);
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(124, 58, 237, 0.25);
}

.btn-confirm i {
  font-size: 1rem;
}

/* 添加字段区域 */
.add-field-section {
  padding: 0.75rem;
  border-top: 1px solid #e5e7eb;
  background: white;
}

.btn-add-custom {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  padding: 0.75rem;
  background: transparent;
  border: 1.5px dashed #d1d5db;
  border-radius: 8px;
  color: #6b7280;
  font-size: 0.875rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-add-custom:hover {
  border-color: #7c3aed;
  color: #7c3aed;
  background: #f5f3ff;
}

/* 添加字段弹窗 */
.field-modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1100;
}

.field-modal {
  background: white;
  border-radius: 12px;
  width: 400px;
  max-width: 90vw;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.2);
}

.field-modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem 1.25rem;
  border-bottom: 1px solid #e5e7eb;
}

.field-modal-header h4 {
  margin: 0;
  font-size: 1rem;
  font-weight: 600;
  color: #1f2937;
}

.btn-close {
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: transparent;
  border: none;
  color: #6b7280;
  cursor: pointer;
  border-radius: 6px;
}

.btn-close:hover {
  background: #f3f4f6;
  color: #1f2937;
}

.field-modal-body {
  padding: 1rem;
}

.field-templates {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 0.75rem;
}

.template-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.5rem;
  padding: 1rem;
  background: #f9fafb;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
}

.template-item:hover {
  background: #f5f3ff;
  border-color: #c4b5fd;
}

.template-item i {
  font-size: 1.5rem;
  color: #7c3aed;
}

.template-item span {
  font-size: 0.875rem;
  color: #374151;
}
</style>

