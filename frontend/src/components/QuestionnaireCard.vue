<script setup lang="ts">
/**
 * 问卷卡片组件
 * 
 * 用于问卷库页面展示单个问卷卡片
 */
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { getQuestionnaireCopy } from '../utils/questionnaireCopy'

interface Questionnaire {
  id: number
  name: string
  type: string
  category?: string
  custom_type?: string
  purpose?: string
  description?: string
  creator?: string
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
  (e: 'copy', q: Questionnaire): void
  (e: 'disabled-distribute-click'): void
}>()

// 菜单状态
const showMenu = ref(false)

// 计算属性
const isActive = computed(() => props.questionnaire.status === 'active')
const copy = computed(() => getQuestionnaireCopy({
  ...props.questionnaire,
  category: props.category === 'professional' ? 'professional' : props.questionnaire.category,
}))
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

function handleCopy() {
  closeMenu()
  emit('copy', props.questionnaire)
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
          <button @click.stop="handleCopy">
            <i class="ri-file-copy-line"></i>
            复制问卷
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

      <div v-if="questionnaire.creator" class="card-creator">
        创建人 {{ questionnaire.creator }}
      </div>
      
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
        :title="isActive ? copy.distributeTitle : '请先启用问卷后再分发'"
      >
        <i class="ri-share-forward-line"></i>
        分发
      </button>
    </div>
  </div>
</template>

<style scoped>
@import './styles/questionnaire-card.css';
</style>
