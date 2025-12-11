<script setup lang="ts">
/**
 * 提交列表面板组件
 * 
 * 用于显示左侧的提交人列表（分组折叠展开）
 * 
 * 注意：为降低迁移风险，状态由父组件管理，本组件只负责展示和事件转发
 */
import { computed } from 'vue'
import { formatDateTime, getGradeClass } from '../utils'

interface Submission {
  id: number
  candidate_name: string
  candidate_phone: string
  total_score?: number
  grade?: string
  submitted_at: string
  questionnaire_id: number
  questionnaire_name?: string
}

interface GroupedSubmission {
  name: string
  phone: string
  latestSubmission: Submission
  submissions: Submission[]
  totalSubmissions: number
  highestScore?: number
  latestGrade?: string
}

const props = defineProps<{
  groupedSubmissions: GroupedSubmission[]
  expandedCandidates: Set<string>
  selectedSubmissionId?: number | null
  selectedSubmissionPhone?: string | null
  category?: string
  searchQuery: string
}>()

const emit = defineEmits<{
  (e: 'select', submission: Submission): void
  (e: 'delete', submission: Submission): void
  (e: 'toggle-expand', key: string): void
  (e: 'update:searchQuery', value: string): void
}>()

// 判断分组是否激活
function isGroupActive(group: GroupedSubmission): boolean {
  return props.selectedSubmissionPhone === group.phone
}

// 判断提交是否选中
function isSelected(submission: Submission): boolean {
  return props.selectedSubmissionId === submission.id
}

// 处理分组点击
function handleGroupClick(group: GroupedSubmission) {
  if (group.totalSubmissions === 1) {
    emit('select', group.latestSubmission)
  } else {
    emit('toggle-expand', group.phone || group.name)
  }
}

// 选择提交记录
function selectSubmission(submission: Submission) {
  emit('select', submission)
}

// 删除提交记录
function handleDelete(submission: Submission) {
  emit('delete', submission)
}

// 更新搜索关键词
function updateSearchQuery(value: string) {
  emit('update:searchQuery', value)
}

// 清空搜索
function clearSearch() {
  emit('update:searchQuery', '')
}

// 获取展开图标类
function getExpandIconClass(group: GroupedSubmission): string {
  const key = group.phone || group.name
  return props.expandedCandidates.has(key) ? 'ri-arrow-up-s-line' : 'ri-arrow-down-s-line'
}

// 判断是否展开
function isExpanded(group: GroupedSubmission): boolean {
  const key = group.phone || group.name
  return props.expandedCandidates.has(key)
}
</script>

<template>
  <div class="submissions-list-panel">
    <div class="panel-header">
      <h3>提交列表</h3>
      <span class="submission-count">共 {{ groupedSubmissions.length }} 人</span>
    </div>
    
    <div class="search-input-wrapper">
      <i class="ri-search-line"></i>
      <input 
        :value="searchQuery"
        @input="updateSearchQuery(($event.target as HTMLInputElement).value)"
        type="text" 
        placeholder="搜索姓名/电话..." 
        class="search-input"
      />
      <button v-if="searchQuery" class="clear-btn" @click="clearSearch">
        <i class="ri-close-line"></i>
      </button>
    </div>
    
    <div class="submissions-scroll">
      <div v-if="groupedSubmissions.length === 0" class="empty-list">
        <i class="ri-inbox-line"></i>
        <p>暂无提交记录</p>
      </div>
      
      <!-- 按用户分组的列表 -->
      <div 
        v-for="group in groupedSubmissions" 
        :key="group.phone || group.name" 
        class="submission-group"
      >
        <!-- 分组头部（多条记录时展开/收起，单条记录时直接选中） -->
        <div 
          class="group-header"
          :class="{ expanded: isExpanded(group), active: isGroupActive(group) }"
          @click="handleGroupClick(group)"
        >
          <div class="group-avatar">
            {{ group.name?.charAt(0) || '?' }}
          </div>
          <div class="group-info">
            <div class="group-name">{{ group.name }}</div>
            <div class="group-phone">{{ group.phone }}</div>
          </div>
          <div class="group-meta">
            <span v-if="group.totalSubmissions > 1" class="submissions-badge">
              {{ group.totalSubmissions }}份
            </span>
            <span v-if="category === 'scored' && group.latestSubmission" class="score-badge">
              {{ group.latestSubmission.total_score || 0 }}分
            </span>
          </div>
          <i 
            v-if="group.totalSubmissions > 1" 
            :class="getExpandIconClass(group)" 
            class="expand-icon"
          ></i>
        </div>
        
        <!-- 展开后显示该用户所有提交记录 -->
        <div v-if="isExpanded(group) && group.totalSubmissions > 1" class="group-submissions">
          <div 
            v-for="sub in group.submissions" 
            :key="sub.id"
            class="submission-item sub-item"
            :class="{ active: isSelected(sub) }"
            @click.stop="selectSubmission(sub)"
          >
            <div class="sub-time">
              <i class="ri-time-line"></i>
              {{ formatDateTime(sub.submitted_at) }}
            </div>
            <div class="sub-score" v-if="category === 'scored'">
              {{ sub.total_score || 0 }}分
              <span class="sub-grade" :class="getGradeClass(sub.grade)">{{ sub.grade || '-' }}</span>
            </div>
            <button class="submission-delete-btn" @click.stop="handleDelete(sub)" title="删除">
              <i class="ri-delete-bin-line"></i>
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
/* 左侧列表面板 */
.submissions-list-panel {
  background: white;
  border-radius: 16px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px;
  border-bottom: 1px solid #f0f0f0;
}

.panel-header h3 {
  font-size: 16px;
  font-weight: 600;
  margin: 0;
}

.submission-count {
  font-size: 13px;
  color: #888;
  background: #f5f5f5;
  padding: 4px 10px;
  border-radius: 12px;
}

/* 搜索框 */
.search-input-wrapper {
  display: flex;
  align-items: center;
  padding: 12px 16px;
  border-bottom: 1px solid #f0f0f0;
  background: #fafafa;
  gap: 8px;
}

.search-input-wrapper > i:first-child {
  color: #999;
  font-size: 16px;
  flex-shrink: 0;
}

.search-input {
  flex: 1;
  border: none;
  background: transparent;
  font-size: 14px;
  outline: none;
  min-width: 0;
}

.search-input::placeholder {
  color: #bbb;
}

.clear-btn {
  width: 24px;
  height: 24px;
  border: none;
  background: #eee;
  border-radius: 50%;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #888;
  transition: all 0.2s;
}

.clear-btn:hover {
  background: #ddd;
  color: #666;
}

/* 滚动容器 */
.submissions-scroll {
  flex: 1;
  overflow-y: auto;
  padding: 8px;
}

/* 空状态 */
.empty-list {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px 20px;
  color: #999;
}

.empty-list i {
  font-size: 48px;
  opacity: 0.3;
  margin-bottom: 12px;
}

/* 分组折叠展开样式 */
.submission-group {
  margin-bottom: 8px;
  border-radius: 12px;
  overflow: hidden;
  background: white;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.05);
  transition: all 0.2s ease;
}

.submission-group:hover {
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.group-header {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 14px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.group-header:hover {
  background: #f8fafc;
}

.group-header.active {
  background: linear-gradient(135deg, rgba(99, 102, 241, 0.1), rgba(139, 92, 246, 0.05));
  border-left: 3px solid #6366f1;
}

.group-header.expanded {
  border-bottom: 1px solid #f1f5f9;
}

.group-avatar {
  width: 40px;
  height: 40px;
  border-radius: 10px;
  background: linear-gradient(135deg, #6366f1, #8b5cf6);
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 600;
  font-size: 16px;
  flex-shrink: 0;
}

.group-info {
  flex: 1;
  min-width: 0;
}

.group-name {
  font-size: 14px;
  font-weight: 600;
  color: #1e293b;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.group-phone {
  font-size: 12px;
  color: #64748b;
  margin-top: 2px;
}

.group-meta {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 4px;
}

.submissions-badge {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 10px;
  background: linear-gradient(135deg, #e0e7ff, #c7d2fe);
  color: #4338ca;
  font-weight: 600;
}

.score-badge {
  font-size: 12px;
  font-weight: 600;
  color: #10b981;
}

.expand-icon {
  font-size: 18px;
  color: #94a3b8;
  transition: transform 0.2s ease;
}

.group-header.expanded .expand-icon {
  transform: rotate(180deg);
}

/* 展开后的子列表 */
.group-submissions {
  background: #f8fafc;
  border-top: 1px solid #e2e8f0;
}

.submission-item.sub-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 14px 10px 66px;
  cursor: pointer;
  transition: all 0.15s ease;
  border-bottom: 1px solid #f1f5f9;
}

.submission-item.sub-item:last-child {
  border-bottom: none;
}

.submission-item.sub-item:hover {
  background: #e2e8f0;
}

.submission-item.sub-item.active {
  background: rgba(99, 102, 241, 0.15);
}

.sub-time {
  flex: 1;
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: #64748b;
}

.sub-time i {
  font-size: 14px;
  color: #94a3b8;
}

.sub-score {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  font-weight: 600;
  color: #10b981;
}

.sub-grade {
  font-size: 11px;
  padding: 2px 6px;
  border-radius: 4px;
  color: white;
}

.sub-grade.grade-a { background: #10b981; }
.sub-grade.grade-b { background: #3b82f6; }
.sub-grade.grade-c { background: #f59e0b; }
.sub-grade.grade-d { background: #ef4444; }

/* 删除按钮 */
.submission-delete-btn {
  width: 28px;
  height: 28px;
  border: none;
  background: transparent;
  color: #94a3b8;
  cursor: pointer;
  border-radius: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
}

.submission-delete-btn:hover {
  background: #fee2e2;
  color: #ef4444;
}
</style>
