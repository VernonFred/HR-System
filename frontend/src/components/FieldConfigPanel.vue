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
                    :value="getOptionValue(opt)"
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
  options?: string[] | Array<{ value: string; label: string }>  // 支持两种格式
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

// 获取选项的显示值（兼容字符串和对象格式）
const getOptionValue = (opt: string | { value: string; label: string }): string => {
  return typeof opt === 'string' ? opt : (opt.label || opt.value)
}

// 字段选项操作
const addFieldOption = (field: FormField) => {
  if (!field.options) {
    field.options = []
  }
  const newOptionLabel = `选项${field.options.length + 1}`
  // 检查现有格式，保持一致
  const firstOption = field.options[0]
  if (firstOption && typeof firstOption === 'object') {
    field.options.push({ value: newOptionLabel, label: newOptionLabel })
  } else {
    field.options.push(newOptionLabel)
  }
  emitUpdate()
}

const updateFieldOption = (field: FormField, index: number, value: string) => {
  if (field.options && field.options[index] !== undefined) {
    const currentOption = field.options[index]
    // 根据当前格式更新
    if (typeof currentOption === 'object') {
      field.options[index] = { value, label: value }
    } else {
      field.options[index] = value
    }
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
@import './styles/field-config-panel.css';
</style>
