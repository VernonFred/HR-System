<script setup lang="ts">
/**
 * 问卷卡片组件
 * 
 * 用于问卷库页面展示单个问卷卡片
 */
import { ref, computed, onMounted, onUnmounted } from 'vue'

interface Questionnaire {
  id: number
  name: string
  type: string
  description?: string
  questions_count: number
  estimated_minutes: number
  status: 'active' | 'inactive'
  created_at: string
}

const props = defineProps<{
  questionnaire: Questionnaire
  category?: string
}>()

const emit = defineEmits<{
  (e: 'edit', q: Questionnaire): void
  (e: 'delete', id: number): void
  (e: 'toggle-status', q: Questionnaire): void
  (e: 'view-links', q: Questionnaire): void
  (e: 'distribute', q: Questionnaire): void
  (e: 'view-detail', q: Questionnaire): void
  (e: 'disabled-distribute-click'): void
}>()

// 菜单状态
const showMenu = ref(false)

// 计算属性
const isActive = computed(() => props.questionnaire.status === 'active')
const formattedDate = computed(() => {
  return new Date(props.questionnaire.created_at).toLocaleDateString()
})
const typeClass = computed(() => `type-${props.questionnaire.type.toLowerCase()}`)

// ⭐ 判断是否为内置测评问卷（禁止删除）
const isBuiltInAssessment = computed(() => {
  const builtInTypes = ['epq', 'disc', 'mbti']
  return builtInTypes.includes(props.questionnaire.type.toLowerCase())
})

// ⭐ 删除按钮是否禁用（内置测评问卷禁止删除）
const isDeleteDisabled = computed(() => isBuiltInAssessment.value)

// 方法
function toggleMenu() {
  showMenu.value = !showMenu.value
}

function closeMenu() {
  showMenu.value = false
}

function handleEdit() {
  closeMenu()
  emit('edit', props.questionnaire)
}

function handleDelete() {
  if (isDeleteDisabled.value) return // 内置测评问卷禁止删除
  closeMenu()
  emit('delete', props.questionnaire)
}

function handleToggleStatus() {
  emit('toggle-status', props.questionnaire)
}

function handleViewLinks() {
  emit('view-links', props.questionnaire)
}

function handleDistribute() {
  if (isActive.value) {
    emit('distribute', props.questionnaire)
  } else {
    emit('disabled-distribute-click')
  }
}

function handleCardClick() {
  // 自定义问卷（custom/scored/survey）点击卡片打开详情抽屉
  // 专业测评（professional）不响应卡片点击
  if (props.category !== 'professional') {
    emit('view-detail', props.questionnaire)
  }
}

// 点击外部关闭菜单
function handleClickOutside(event: MouseEvent) {
  const target = event.target as HTMLElement
  if (!target.closest('.card-more-menu')) {
    closeMenu()
  }
}

// 生命周期
onMounted(() => {
  document.addEventListener('click', handleClickOutside)
})

onUnmounted(() => {
  document.removeEventListener('click', handleClickOutside)
})
</script>

<template>
  <div class="questionnaire-card" @click="handleCardClick" :class="{ clickable: category !== 'professional' }">
    <!-- 卡片头部：图标 + 更多菜单 -->
    <div class="card-header-row" @click.stop>
      <div class="card-icon">
        <i class="ri-file-list-3-line"></i>
      </div>
      <div class="card-more-menu" @click.stop="toggleMenu">
        <i class="ri-more-2-fill"></i>
        <!-- 下拉菜单 -->
        <div v-if="showMenu" class="card-dropdown-menu">
          <button @click.stop="handleEdit">
            <i class="ri-edit-line"></i>
            编辑问卷
          </button>
          <button 
            class="danger" 
            :class="{ disabled: isDeleteDisabled }"
            @click.stop="handleDelete"
            :disabled="isDeleteDisabled"
            :title="isDeleteDisabled ? '内置测评问卷不可删除' : '删除此问卷'"
          >
            <i class="ri-delete-bin-line"></i>
            删除问卷
          </button>
        </div>
      </div>
    </div>
    
    <!-- 卡片主体内容 -->
    <div class="card-body">
      <h3 class="card-title">{{ questionnaire.name }}</h3>
      <span class="card-type-tag" :class="typeClass">{{ questionnaire.type }}</span>
      
      <div class="card-meta">
        <span class="meta-item">
          <i class="ri-file-list-line"></i>
          {{ questionnaire.questions_count }} 道题
        </span>
        <span class="meta-divider">|</span>
        <span class="meta-item">
          <i class="ri-time-line"></i>
          约 {{ questionnaire.estimated_minutes }} 分钟
        </span>
      </div>
      
      <p class="card-desc">{{ questionnaire.description }}</p>
      
      <div class="card-date">
        创建于 {{ formattedDate }}
      </div>
    </div>
    
    <!-- 卡片底部：操作按钮 -->
    <div class="card-footer-actions" @click.stop>
      <button 
        class="action-btn status-btn" 
        :class="{ active: isActive }"
        @click.stop="handleToggleStatus"
        :title="isActive ? '点击停用' : '点击启用'"
      >
        <i :class="isActive ? 'ri-checkbox-circle-fill' : 'ri-close-circle-fill'"></i>
        {{ isActive ? '已启用' : '已停用' }}
      </button>
      <button 
        class="action-btn links-btn" 
        @click.stop="handleViewLinks"
        title="查看链接"
      >
        <i class="ri-links-line"></i>
        链接
      </button>
      <button 
        class="action-btn distribute-btn" 
        :class="{ disabled: !isActive }"
        @click.stop="handleDistribute"
        :title="isActive ? '分发测评' : '请先启用问卷后再分发'"
      >
        <i class="ri-share-forward-line"></i>
        分发
      </button>
    </div>
  </div>
</template>

<style scoped>
/* 问卷卡片样式 */
.questionnaire-card {
  background: white;
  border-radius: 16px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
  transition: all 0.3s;
  position: relative;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

/* 可点击的卡片 */
.questionnaire-card.clickable {
  cursor: pointer;
}

.questionnaire-card.clickable:hover {
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.12);
  transform: translateY(-2px);
}

.questionnaire-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 4px;
  background: linear-gradient(90deg, #667eea, #764ba2);
}

.questionnaire-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.12);
}

/* 卡片头部 */
.card-header-row {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  padding: 1.25rem 1.25rem 0;
}

.card-icon {
  width: 48px;
  height: 48px;
  background: linear-gradient(135deg, #667eea15, #764ba225);
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.5rem;
  color: #667eea;
}

/* 更多菜单 */
.card-more-menu {
  position: relative;
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 8px;
  cursor: pointer;
  color: #9ca3af;
  transition: all 0.2s;
}

.card-more-menu:hover {
  background: #f3f4f6;
  color: #6b7280;
}

.card-more-menu i {
  font-size: 1.25rem;
}

.card-dropdown-menu {
  position: absolute;
  top: 100%;
  right: 0;
  margin-top: 4px;
  background: white;
  border-radius: 10px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
  padding: 0.5rem;
  min-width: 140px;
  z-index: 100;
}

.card-dropdown-menu button {
  display: flex;
  align-items: center;
  gap: 0.625rem;
  width: 100%;
  padding: 0.625rem 0.875rem;
  border: none;
  background: none;
  border-radius: 6px;
  font-size: 0.875rem;
  color: #374151;
  cursor: pointer;
  transition: all 0.15s;
}

.card-dropdown-menu button:hover {
  background: #f3f4f6;
}

.card-dropdown-menu button.danger {
  color: #ef4444;
}

.card-dropdown-menu button.danger:hover:not(.disabled) {
  background: #fef2f2;
}

/* ⭐ 禁用状态的删除按钮 */
.card-dropdown-menu button.danger.disabled {
  color: #9ca3af;
  cursor: not-allowed;
  opacity: 0.6;
}

.card-dropdown-menu button.danger.disabled:hover {
  background: transparent;
}

.card-dropdown-menu button i {
  font-size: 1rem;
}

/* 卡片主体 */
.card-body {
  flex: 1;
  padding: 1rem 1.25rem;
}

.card-title {
  font-size: 1.125rem;
  font-weight: 700;
  color: #1f2937;
  margin: 0 0 0.5rem;
  line-height: 1.4;
}

.card-type-tag {
  display: inline-block;
  padding: 0.25rem 0.625rem;
  border-radius: 6px;
  font-size: 0.6875rem;
  font-weight: 700;
  text-transform: uppercase;
  margin-bottom: 0.875rem;
}

.type-epq {
  background: linear-gradient(135deg, #dbeafe, #bfdbfe);
  color: #1e40af;
}

.type-disc {
  background: linear-gradient(135deg, #fce7f3, #fbcfe8);
  color: #be185d;
}

.type-mbti {
  background: linear-gradient(135deg, #fef3c7, #fde68a);
  color: #92400e;
}

.type-custom {
  background: linear-gradient(135deg, #e5e7eb, #d1d5db);
  color: #374151;
}

.card-meta {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 0.75rem;
  font-size: 0.8125rem;
  color: #6b7280;
}

.meta-item {
  display: flex;
  align-items: center;
  gap: 0.375rem;
}

.meta-item i {
  color: #9ca3af;
  font-size: 0.875rem;
}

.meta-divider {
  color: #d1d5db;
}

.card-desc {
  color: #6b7280;
  font-size: 0.8125rem;
  line-height: 1.5;
  margin: 0 0 0.75rem;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.card-date {
  font-size: 0.75rem;
  color: #9ca3af;
}

/* 卡片底部 */
.card-footer-actions {
  display: flex;
  justify-content: flex-end;
  align-items: center;
  gap: 0.5rem;
  padding: 0.875rem 1.25rem;
  background: #f9fafb;
  border-top: 1px solid #f3f4f6;
}

.action-btn {
  display: inline-flex;
  align-items: center;
  gap: 0.375rem;
  padding: 0.5rem 0.875rem;
  border: none;
  border-radius: 8px;
  font-size: 0.8125rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}

.action-btn i {
  font-size: 0.9375rem;
}

.status-btn {
  background: #f3f4f6;
  color: #6b7280;
}

.status-btn:hover {
  background: #e5e7eb;
}

.status-btn.active {
  background: linear-gradient(135deg, #d1fae5 0%, #a7f3d0 100%);
  color: #047857;
}

.links-btn {
  background: linear-gradient(135deg, #dbeafe 0%, #bfdbfe 100%);
  color: #1d4ed8;
}

.links-btn:hover {
  background: linear-gradient(135deg, #bfdbfe 0%, #93c5fd 100%);
}

.distribute-btn {
  background: linear-gradient(135deg, #7c3aed 0%, #a855f7 100%);
  color: white;
  box-shadow: 0 2px 6px rgba(124, 58, 237, 0.25);
}

.distribute-btn:hover:not(.disabled) {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(124, 58, 237, 0.35);
}

.distribute-btn.disabled {
  background: #d1d5db;
  color: #9ca3af;
  cursor: not-allowed;
  box-shadow: none;
}
</style>

