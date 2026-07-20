<script setup lang="ts">
import { computed, ref } from 'vue'
import { createQuestionnaireTag, type QuestionnaireTagSummary } from '../api/assessments'

const props = withDefaults(defineProps<{
  modelValue: number[]
  tags: QuestionnaireTagSummary[]
  max?: number
  disabled?: boolean
}>(), {
  max: 10,
  disabled: false,
})

const emit = defineEmits<{
  (event: 'update:modelValue', value: number[]): void
  (event: 'tag-created', value: QuestionnaireTagSummary): void
}>()

const open = ref(false)
const keyword = ref('')
const creating = ref(false)
const errorMessage = ref('')

const selectedTags = computed(() => props.modelValue
  .map(id => props.tags.find(tag => tag.id === id))
  .filter((tag): tag is QuestionnaireTagSummary => !!tag))

const availableTags = computed(() => {
  const normalized = keyword.value.trim().toLocaleLowerCase()
  return props.tags.filter(tag => {
    if (!tag.is_active && !props.modelValue.includes(tag.id)) return false
    return !normalized || tag.name.toLocaleLowerCase().includes(normalized)
  })
})

const canCreate = computed(() => {
  const normalized = keyword.value.trim().toLocaleLowerCase()
  return Boolean(
    normalized
      && !props.tags.some(tag => tag.name.trim().toLocaleLowerCase() === normalized)
      && props.modelValue.length < props.max,
  )
})

const toggleTag = (tag: QuestionnaireTagSummary) => {
  if (props.disabled) return
  const selected = props.modelValue.includes(tag.id)
  if (selected) {
    emit('update:modelValue', props.modelValue.filter(id => id !== tag.id))
    return
  }
  if (!tag.is_active || props.modelValue.length >= props.max) return
  emit('update:modelValue', [...props.modelValue, tag.id])
}

const createTag = async () => {
  const name = keyword.value.trim()
  if (!canCreate.value || creating.value) return
  creating.value = true
  errorMessage.value = ''
  try {
    const tag = await createQuestionnaireTag({ name })
    emit('tag-created', tag)
    emit('update:modelValue', [...props.modelValue, tag.id])
    keyword.value = ''
  } catch (error: any) {
    errorMessage.value = error?.detail || error?.message || '标签创建失败'
  } finally {
    creating.value = false
  }
}
</script>

<template>
  <div class="tag-picker" :class="{ disabled }">
    <div v-if="selectedTags.length" class="selected-tags">
      <span v-for="tag in selectedTags" :key="tag.id" class="selected-tag">
        {{ tag.name }}
        <span v-if="!tag.is_active" class="tag-history">已停用</span>
        <button type="button" :disabled="disabled" :aria-label="`移除标签 ${tag.name}`" @click="toggleTag(tag)">
          <i class="ri-close-line"></i>
        </button>
      </span>
    </div>

    <button
      type="button"
      class="picker-trigger"
      :disabled="disabled"
      :aria-expanded="open"
      @click="open = !open"
    >
      <span><i class="ri-price-tag-3-line"></i> 选择标签</span>
      <span class="picker-count">{{ modelValue.length }} / {{ max }}</span>
      <i :class="open ? 'ri-arrow-up-s-line' : 'ri-arrow-down-s-line'"></i>
    </button>

    <div v-if="open" class="picker-menu">
      <div class="picker-search">
        <i class="ri-search-line"></i>
        <input v-model="keyword" type="text" placeholder="搜索或新建标签" @keydown.enter.prevent="createTag" />
      </div>

      <div class="tag-options">
        <button
          v-for="tag in availableTags"
          :key="tag.id"
          type="button"
          class="tag-option"
          :class="{ selected: modelValue.includes(tag.id) }"
          :disabled="!tag.is_active && !modelValue.includes(tag.id)"
          @click="toggleTag(tag)"
        >
          <i :class="modelValue.includes(tag.id) ? 'ri-checkbox-circle-fill' : 'ri-checkbox-blank-circle-line'"></i>
          <span>{{ tag.name }}</span>
          <small v-if="!tag.is_active">历史标签</small>
        </button>
        <p v-if="!availableTags.length && !canCreate" class="picker-empty">没有匹配的标签</p>
      </div>

      <button v-if="canCreate" type="button" class="create-tag-button" :disabled="creating" @click="createTag">
        <i class="ri-add-line"></i>
        {{ creating ? '创建中...' : `创建“${keyword.trim()}”` }}
      </button>
      <p v-if="errorMessage" class="picker-error">{{ errorMessage }}</p>
    </div>
  </div>
</template>

<style scoped>
.tag-picker { position: relative; }
.tag-picker.disabled { opacity: 0.65; }
.selected-tags { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 10px; }
.selected-tag { display: inline-flex; align-items: center; gap: 6px; max-width: 100%; padding: 5px 8px 5px 10px; border: 1px solid #dbe3ef; border-radius: 6px; background: #f8fafc; color: #334155; font-size: 13px; }
.selected-tag button { display: inline-flex; align-items: center; justify-content: center; width: 20px; height: 20px; padding: 0; border: 0; border-radius: 4px; background: transparent; color: #94a3b8; cursor: pointer; }
.selected-tag button:hover { background: #e2e8f0; color: #475569; }
.tag-history { color: #b45309; font-size: 11px; }
.picker-trigger { display: grid; grid-template-columns: 1fr auto auto; align-items: center; gap: 10px; width: 100%; min-height: 44px; padding: 10px 13px; border: 1px solid #dbe3ef; border-radius: 8px; background: #fff; color: #475569; cursor: pointer; text-align: left; }
.picker-trigger > span:first-child { display: inline-flex; align-items: center; gap: 8px; }
.picker-trigger:focus-visible { outline: 3px solid rgba(99, 102, 241, 0.14); border-color: #6366f1; }
.picker-count { color: #94a3b8; font-size: 12px; }
.picker-menu { position: absolute; z-index: 30; top: calc(100% + 6px); left: 0; right: 0; padding: 10px; border: 1px solid #dbe3ef; border-radius: 8px; background: #fff; box-shadow: 0 14px 30px rgba(15, 23, 42, 0.12); }
.picker-search { display: flex; align-items: center; gap: 8px; padding: 0 10px; border: 1px solid #e2e8f0; border-radius: 7px; color: #94a3b8; }
.picker-search input { width: 100%; min-width: 0; padding: 9px 0; border: 0; outline: 0; color: #1e293b; font: inherit; }
.tag-options { max-height: 210px; overflow-y: auto; margin-top: 8px; }
.tag-option { display: grid; grid-template-columns: 20px 1fr auto; align-items: center; gap: 8px; width: 100%; padding: 9px 8px; border: 0; border-radius: 6px; background: transparent; color: #475569; cursor: pointer; text-align: left; }
.tag-option:hover:not(:disabled) { background: #f1f5f9; }
.tag-option.selected { color: #4f46e5; }
.tag-option small { color: #b45309; }
.create-tag-button { display: flex; align-items: center; gap: 7px; width: 100%; margin-top: 8px; padding: 9px 8px; border: 0; border-top: 1px solid #eef2f7; background: transparent; color: #4f46e5; cursor: pointer; text-align: left; }
.picker-empty, .picker-error { margin: 12px 8px; font-size: 12px; }
.picker-empty { color: #94a3b8; }
.picker-error { color: #dc2626; }
</style>
