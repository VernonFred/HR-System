<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import Sortable, { type SortableEvent } from 'sortablejs'
import {
  createQuestionnaireLibraryCategory,
  createQuestionnaireTag,
  fetchQuestionnaireLibraryCategories,
  fetchQuestionnaireTags,
  mergeQuestionnaireTag,
  reorderQuestionnaireLibraryCategories,
  updateQuestionnaireLibraryCategory,
  updateQuestionnaireTag,
  type QuestionnaireLibraryCategory,
  type QuestionnaireTag,
} from '../api/assessments'
import { reorderQuestionnaireLibraryItems } from '../utils/questionnaireLibrary'

const emit = defineEmits<{
  (event: 'close'): void
  (event: 'changed'): void
}>()

const activeTab = ref<'categories' | 'tags'>('categories')
const categories = ref<QuestionnaireLibraryCategory[]>([])
const tags = ref<QuestionnaireTag[]>([])
const loading = ref(false)
const saving = ref(false)
const errorMessage = ref('')
const newCategoryName = ref('')
const newTagName = ref('')
const editingCategoryId = ref<number | null>(null)
const editingTagId = ref<number | null>(null)
const editName = ref('')
const mergeSourceId = ref<number | null>(null)
const mergeTargetId = ref<number | null>(null)
const categoryListRef = ref<HTMLElement | null>(null)
let categorySortable: Sortable | null = null

const activeMergeTargets = computed(() => tags.value.filter(tag => (
  tag.is_active && tag.id !== mergeSourceId.value
)))

const getErrorMessage = (error: any) => {
  const detail = error?.detail
  if (typeof detail === 'string') return detail
  return detail?.message || error?.message || '操作失败，请重试'
}

const loadData = async () => {
  loading.value = true
  errorMessage.value = ''
  try {
    const [categoryData, tagData] = await Promise.all([
      fetchQuestionnaireLibraryCategories(),
      fetchQuestionnaireTags(),
    ])
    categories.value = [...categoryData].sort((a, b) => a.sort_order - b.sort_order || a.id - b.id)
    tags.value = tagData
  } catch (error) {
    errorMessage.value = getErrorMessage(error)
  } finally {
    loading.value = false
  }
}

const runMutation = async (mutation: () => Promise<unknown>) => {
  if (saving.value) return
  saving.value = true
  errorMessage.value = ''
  try {
    await mutation()
    await loadData()
    await initializeCategorySortable()
    emit('changed')
  } catch (error) {
    const mutationError = getErrorMessage(error)
    await loadData()
    await initializeCategorySortable()
    errorMessage.value = mutationError
  } finally {
    saving.value = false
  }
}

const addCategory = () => {
  const name = newCategoryName.value.trim()
  if (!name) return
  const nextOrder = categories.value.reduce((max, category) => Math.max(max, category.sort_order), -1) + 1
  runMutation(async () => {
    await createQuestionnaireLibraryCategory({ name, sort_order: nextOrder })
    newCategoryName.value = ''
  })
}

const addTag = () => {
  const name = newTagName.value.trim()
  if (!name) return
  runMutation(async () => {
    await createQuestionnaireTag({ name })
    newTagName.value = ''
  })
}

const beginCategoryEdit = (category: QuestionnaireLibraryCategory) => {
  if (category.is_system) return
  editingCategoryId.value = category.id
  editingTagId.value = null
  editName.value = category.name
}

const beginTagEdit = (tag: QuestionnaireTag) => {
  editingTagId.value = tag.id
  editingCategoryId.value = null
  editName.value = tag.name
}

const saveCategoryName = (category: QuestionnaireLibraryCategory) => {
  const name = editName.value.trim()
  if (!name || name === category.name) {
    editingCategoryId.value = null
    return
  }
  runMutation(async () => {
    await updateQuestionnaireLibraryCategory(category.id, { name })
    editingCategoryId.value = null
  })
}

const saveTagName = (tag: QuestionnaireTag) => {
  const name = editName.value.trim()
  if (!name || name === tag.name) {
    editingTagId.value = null
    return
  }
  runMutation(async () => {
    await updateQuestionnaireTag(tag.id, { name })
    editingTagId.value = null
  })
}

const toggleCategory = (category: QuestionnaireLibraryCategory) => {
  if (category.is_system) return
  runMutation(() => updateQuestionnaireLibraryCategory(category.id, { is_active: !category.is_active }))
}

const toggleTag = (tag: QuestionnaireTag) => {
  runMutation(() => updateQuestionnaireTag(tag.id, { is_active: !tag.is_active }))
}

const persistCategoryOrder = async (
  previous: QuestionnaireLibraryCategory[],
  next: QuestionnaireLibraryCategory[],
) => {
  categories.value = next.map((category, sortOrder) => ({
    ...category,
    sort_order: sortOrder,
  }))
  saving.value = true
  errorMessage.value = ''
  try {
    await reorderQuestionnaireLibraryCategories(categories.value.map(category => category.id))
    emit('changed')
  } catch (error) {
    categories.value = previous
    errorMessage.value = getErrorMessage(error)
  } finally {
    saving.value = false
  }
}

const moveCategory = (index: number, direction: -1 | 1) => {
  if (saving.value) return
  const targetIndex = index + direction
  const previous = [...categories.value]
  const next = reorderQuestionnaireLibraryItems(previous, index, targetIndex)
  if (next.every((category, itemIndex) => category.id === previous[itemIndex]?.id)) return
  void persistCategoryOrder(previous, next)
}

const handleCategoryDragEnd = (event: SortableEvent) => {
  const sourceIndex = event.oldIndex
  const targetIndex = event.newIndex
  if (
    sourceIndex === undefined
    || targetIndex === undefined
    || sourceIndex === targetIndex
    || saving.value
  ) return
  const previous = [...categories.value]
  const next = reorderQuestionnaireLibraryItems(previous, sourceIndex, targetIndex)
  void persistCategoryOrder(previous, next)
}

const destroyCategorySortable = () => {
  categorySortable?.destroy()
  categorySortable = null
}

const initializeCategorySortable = async () => {
  destroyCategorySortable()
  if (activeTab.value !== 'categories') return
  await nextTick()
  if (!categoryListRef.value) return
  categorySortable = new Sortable(categoryListRef.value, {
    animation: 180,
    handle: '.drag-handle',
    draggable: '.manager-row',
    forceFallback: true,
    fallbackOnBody: true,
    fallbackTolerance: 3,
    ghostClass: 'category-drag-ghost',
    chosenClass: 'category-drag-chosen',
    dragClass: 'category-dragging',
    onEnd: handleCategoryDragEnd,
  })
  categorySortable.option('disabled', saving.value)
}

const mergeTags = () => {
  if (!mergeSourceId.value || !mergeTargetId.value) return
  const sourceId = mergeSourceId.value
  const targetId = mergeTargetId.value
  runMutation(async () => {
    await mergeQuestionnaireTag(sourceId, targetId)
    mergeSourceId.value = null
    mergeTargetId.value = null
  })
}

watch(activeTab, initializeCategorySortable)
watch(saving, isSaving => categorySortable?.option('disabled', isSaving))

onMounted(async () => {
  await loadData()
  await initializeCategorySortable()
})

onBeforeUnmount(destroyCategorySortable)
</script>

<template>
  <div class="library-manager-overlay" @click.self="emit('close')">
    <section class="library-manager" role="dialog" aria-modal="true" aria-labelledby="library-manager-title">
      <header class="manager-header">
        <div>
          <h3 id="library-manager-title">分类管理</h3>
          <p>维护问卷库的主分类与共享标签</p>
        </div>
        <button type="button" class="icon-button" aria-label="关闭" @click="emit('close')">
          <i class="ri-close-line"></i>
        </button>
      </header>

      <nav class="manager-tabs" aria-label="分类管理类型">
        <button type="button" :class="{ active: activeTab === 'categories' }" @click="activeTab = 'categories'">
          主分类 <span>{{ categories.length }}</span>
        </button>
        <button type="button" :class="{ active: activeTab === 'tags' }" @click="activeTab = 'tags'">
          标签库 <span>{{ tags.length }}</span>
        </button>
      </nav>

      <p v-if="errorMessage" class="manager-error"><i class="ri-error-warning-line"></i>{{ errorMessage }}</p>
      <div v-if="loading" class="manager-loading"><i class="ri-loader-4-line"></i> 正在加载...</div>

      <div v-else-if="activeTab === 'categories'" class="manager-panel">
        <div class="create-row">
          <input v-model="newCategoryName" type="text" maxlength="40" placeholder="新增主分类名称" @keydown.enter.prevent="addCategory" />
          <button type="button" class="primary-button" :disabled="saving || !newCategoryName.trim()" @click="addCategory">
            <i class="ri-add-line"></i> 新增分类
          </button>
        </div>

        <div class="column-head category-columns">
          <span>分类名称</span><span>问卷数</span><span>状态</span><span>操作</span>
        </div>
        <div ref="categoryListRef" class="manager-list">
          <TransitionGroup name="category-order">
            <div v-for="(category, index) in categories" :key="category.id" class="manager-row category-columns">
              <div class="name-cell">
                <button
                  type="button"
                  class="drag-handle"
                  :disabled="saving"
                  :aria-label="`拖拽调整${category.name}的顺序`"
                  title="拖拽排序"
                >
                  <i class="ri-draggable"></i>
                </button>
                <input
                  v-if="editingCategoryId === category.id"
                  v-model="editName"
                  class="inline-input"
                  maxlength="40"
                  @keydown.enter.prevent="saveCategoryName(category)"
                  @keydown.esc="editingCategoryId = null"
                  @blur="saveCategoryName(category)"
                />
                <button v-else type="button" class="name-button" :disabled="category.is_system" @click="beginCategoryEdit(category)">
                  {{ category.name }}
                </button>
                <span v-if="category.is_system" class="system-label">系统</span>
              </div>
              <span class="count-cell">{{ category.questionnaire_count }}</span>
              <span :class="['status-text', category.is_active ? 'active' : 'inactive']">
                {{ category.is_active ? '启用' : '停用' }}
              </span>
              <div class="row-actions">
                <button type="button" class="icon-button small" :disabled="saving || index === 0" title="上移" @click="moveCategory(index, -1)"><i class="ri-arrow-up-line"></i></button>
                <button type="button" class="icon-button small" :disabled="saving || index === categories.length - 1" title="下移" @click="moveCategory(index, 1)"><i class="ri-arrow-down-line"></i></button>
                <button type="button" class="text-button" :disabled="saving || category.is_system" @click="toggleCategory(category)">
                  {{ category.is_active ? '停用' : '启用' }}
                </button>
              </div>
            </div>
          </TransitionGroup>
        </div>
        <p class="manager-note">“未分类”为系统分类，用于承接历史问卷，不可重命名或停用。</p>
      </div>

      <div v-else class="manager-panel">
        <div class="create-row">
          <input v-model="newTagName" type="text" maxlength="30" placeholder="新增共享标签" @keydown.enter.prevent="addTag" />
          <button type="button" class="primary-button" :disabled="saving || !newTagName.trim()" @click="addTag">
            <i class="ri-add-line"></i> 新增标签
          </button>
        </div>

        <div class="merge-row">
          <span><i class="ri-git-merge-line"></i> 合并标签</span>
          <select v-model="mergeSourceId">
            <option :value="null">选择源标签</option>
            <option v-for="tag in tags" :key="tag.id" :value="tag.id">{{ tag.name }}</option>
          </select>
          <i class="ri-arrow-right-line"></i>
          <select v-model="mergeTargetId" :disabled="!mergeSourceId">
            <option :value="null">合并到</option>
            <option v-for="tag in activeMergeTargets" :key="tag.id" :value="tag.id">{{ tag.name }}</option>
          </select>
          <button type="button" class="secondary-button" :disabled="saving || !mergeSourceId || !mergeTargetId" @click="mergeTags">确认合并</button>
        </div>

        <div class="column-head tag-columns">
          <span>标签名称</span><span>问卷数</span><span>状态</span><span>操作</span>
        </div>
        <div class="manager-list">
          <div v-for="tag in tags" :key="tag.id" class="manager-row tag-columns">
            <div class="name-cell">
              <span class="tag-dot"></span>
              <input
                v-if="editingTagId === tag.id"
                v-model="editName"
                class="inline-input"
                maxlength="30"
                @keydown.enter.prevent="saveTagName(tag)"
                @keydown.esc="editingTagId = null"
                @blur="saveTagName(tag)"
              />
              <button v-else type="button" class="name-button" @click="beginTagEdit(tag)">{{ tag.name }}</button>
            </div>
            <span class="count-cell">{{ tag.questionnaire_count }}</span>
            <span :class="['status-text', tag.is_active ? 'active' : 'inactive']">{{ tag.is_active ? '启用' : '停用' }}</span>
            <div class="row-actions">
              <button type="button" class="text-button" :disabled="saving" @click="toggleTag(tag)">{{ tag.is_active ? '停用' : '启用' }}</button>
            </div>
          </div>
          <p v-if="!tags.length" class="empty-row">暂无标签，可在上方新建。</p>
        </div>
        <p class="manager-note">合并后，源标签会停用，已有问卷关联将迁移到目标标签并自动去重。</p>
      </div>
    </section>
  </div>
</template>

<style scoped>
.library-manager-overlay { position: fixed; inset: 0; z-index: 1250; display: grid; place-items: center; padding: 24px; background: rgba(15, 23, 42, 0.42); }
.library-manager { width: min(860px, 100%); max-height: min(760px, calc(100vh - 48px)); overflow: hidden; border-radius: 12px; background: #fff; box-shadow: 0 24px 70px rgba(15, 23, 42, 0.22); color: #1e293b; }
.manager-header { display: flex; align-items: center; justify-content: space-between; padding: 22px 24px 16px; border-bottom: 1px solid #edf1f6; }
.manager-header h3 { margin: 0; font-size: 19px; font-weight: 650; }
.manager-header p { margin: 5px 0 0; color: #94a3b8; font-size: 13px; }
.icon-button { display: inline-flex; align-items: center; justify-content: center; width: 36px; height: 36px; padding: 0; border: 0; border-radius: 7px; background: transparent; color: #64748b; cursor: pointer; }
.icon-button:hover:not(:disabled) { background: #f1f5f9; color: #334155; }
.icon-button.small { width: 30px; height: 30px; }
.icon-button:disabled, button:disabled { opacity: 0.42; cursor: not-allowed; }
.manager-tabs { display: flex; gap: 24px; padding: 0 24px; border-bottom: 1px solid #edf1f6; }
.manager-tabs button { position: relative; display: inline-flex; align-items: center; gap: 7px; padding: 15px 0 13px; border: 0; background: transparent; color: #64748b; font-weight: 600; cursor: pointer; }
.manager-tabs button::after { content: ''; position: absolute; right: 0; bottom: -1px; left: 0; height: 2px; background: transparent; }
.manager-tabs button.active { color: #4f46e5; }
.manager-tabs button.active::after { background: #6366f1; }
.manager-tabs span { color: #94a3b8; font-size: 12px; font-weight: 500; }
.manager-panel { max-height: 600px; overflow-y: auto; padding: 20px 24px 24px; }
.create-row { display: grid; grid-template-columns: 1fr auto; gap: 10px; }
input, select { min-width: 0; height: 40px; padding: 0 12px; border: 1px solid #dbe3ef; border-radius: 7px; background: #fff; color: #334155; font: inherit; }
input:focus, select:focus { outline: 3px solid rgba(99, 102, 241, 0.12); border-color: #6366f1; }
.primary-button, .secondary-button { display: inline-flex; align-items: center; justify-content: center; gap: 7px; height: 40px; padding: 0 15px; border-radius: 7px; font-weight: 600; cursor: pointer; }
.primary-button { border: 1px solid #4f46e5; background: #4f46e5; color: #fff; }
.secondary-button { border: 1px solid #dbe3ef; background: #fff; color: #475569; }
.merge-row { display: grid; grid-template-columns: auto minmax(130px, 1fr) auto minmax(130px, 1fr) auto; align-items: center; gap: 9px; margin-top: 14px; padding: 12px 0; border-top: 1px solid #edf1f6; border-bottom: 1px solid #edf1f6; color: #64748b; font-size: 13px; }
.merge-row > span { display: inline-flex; align-items: center; gap: 6px; font-weight: 600; white-space: nowrap; }
.column-head, .manager-row { display: grid; align-items: center; gap: 12px; }
.category-columns, .tag-columns { grid-template-columns: minmax(220px, 1fr) 80px 72px 190px; }
.column-head { margin-top: 18px; padding: 0 12px 8px; color: #94a3b8; font-size: 12px; }
.manager-list { border-top: 1px solid #e7edf4; }
.manager-row { min-height: 58px; padding: 8px 12px; border-bottom: 1px solid #edf1f6; transition: background-color 120ms ease, box-shadow 120ms ease, opacity 120ms ease; }
.manager-row:hover { background: #fafbfc; }
.manager-row.category-drag-ghost { opacity: 0.28; background: #eef2ff; }
.manager-row.category-drag-chosen { background: #f8faff; box-shadow: inset 0 0 0 1px #c7d2fe; }
.manager-row.category-dragging { border-radius: 7px; background: #fff; box-shadow: 0 12px 28px rgba(15, 23, 42, 0.16); opacity: 0.96; }
.category-order-move { transition: transform 180ms cubic-bezier(0.22, 1, 0.36, 1); }
.name-cell { display: flex; align-items: center; gap: 8px; min-width: 0; }
.drag-handle { display: inline-flex; align-items: center; justify-content: center; width: 24px; height: 30px; flex: 0 0 auto; padding: 0; border: 0; background: transparent; color: #cbd5e1; cursor: grab; touch-action: none; }
.drag-handle:hover:not(:disabled) { color: #6366f1; }
.drag-handle:active { cursor: grabbing; }
.tag-dot { width: 8px; height: 8px; flex: 0 0 auto; border-radius: 50%; background: #818cf8; }
.name-button { min-width: 0; padding: 4px 0; overflow: hidden; border: 0; background: transparent; color: #334155; font: inherit; font-weight: 600; cursor: text; text-align: left; text-overflow: ellipsis; white-space: nowrap; }
.name-button:disabled { opacity: 1; cursor: default; }
.inline-input { width: min(260px, 100%); height: 34px; }
.system-label { padding: 2px 6px; border-radius: 4px; background: #f1f5f9; color: #64748b; font-size: 11px; }
.count-cell { color: #64748b; font-variant-numeric: tabular-nums; }
.status-text { position: relative; padding-left: 13px; font-size: 13px; }
.status-text::before { content: ''; position: absolute; left: 0; top: 50%; width: 6px; height: 6px; border-radius: 50%; transform: translateY(-50%); }
.status-text.active { color: #047857; }
.status-text.active::before { background: #10b981; }
.status-text.inactive { color: #94a3b8; }
.status-text.inactive::before { background: #cbd5e1; }
.row-actions { display: flex; align-items: center; justify-content: flex-end; gap: 3px; }
.text-button { padding: 7px 9px; border: 0; border-radius: 6px; background: transparent; color: #4f46e5; cursor: pointer; }
.text-button:hover:not(:disabled) { background: #eef2ff; }
.manager-note { margin: 14px 2px 0; color: #94a3b8; font-size: 12px; }
.manager-error, .manager-loading { margin: 16px 24px 0; }
.manager-error { display: flex; align-items: center; gap: 7px; padding: 10px 12px; border-radius: 7px; background: #fef2f2; color: #b91c1c; font-size: 13px; }
.manager-loading, .empty-row { padding: 30px; color: #94a3b8; text-align: center; }
.manager-loading i { display: inline-block; animation: manager-spin 0.8s linear infinite; }
@keyframes manager-spin { to { transform: rotate(360deg); } }
@media (max-width: 680px) {
  .library-manager-overlay { padding: 0; }
  .library-manager { width: 100%; max-height: 100vh; min-height: 100vh; border-radius: 0; }
  .manager-panel { max-height: calc(100vh - 150px); padding: 16px; }
  .column-head { display: none; }
  .category-columns, .tag-columns { grid-template-columns: 1fr auto; }
  .count-cell, .status-text { display: none; }
  .merge-row { grid-template-columns: 1fr; }
  .merge-row > i { display: none; }
  .row-actions { justify-content: flex-start; }
}
</style>
