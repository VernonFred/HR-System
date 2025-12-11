<script setup lang="ts">
/**
 * 测评记录列表组件
 * 只显示专业测评（MBTI/DISC/EPQ），点击通知父组件打开抽屉
 */
import { ref, computed } from 'vue';
import type { AssessmentRecord, CandidateProfile } from '../../types/candidate';

const props = defineProps<{
  assessments: AssessmentRecord[];
  profile: CandidateProfile;
}>();

// 定义 emit 事件
const emit = defineEmits<{
  (e: 'open-drawer', assessment: AssessmentRecord): void;
}>();

// ⭐ 只过滤专业测评，排除问卷调查
const professionalAssessments = computed(() => {
  return props.assessments.filter(a => {
    const name = a.questionnaire_name?.toUpperCase() || '';
    return name.includes('MBTI') || name.includes('DISC') || name.includes('EPQ');
  });
});

// 分页状态
const currentPage = ref(1);
const pageSize = 4;

// 分页后的测评列表
const paginatedAssessments = computed(() => {
  const start = (currentPage.value - 1) * pageSize;
  return professionalAssessments.value.slice(start, start + pageSize);
});

// 总页数
const totalPages = computed(() => Math.ceil(professionalAssessments.value.length / pageSize));

// 点击测评记录，通知父组件打开抽屉
const handleClick = (assessment: AssessmentRecord) => {
  emit('open-drawer', assessment);
};

// 获取测评图标
const getIcon = (name: string): string => {
  if (name?.toUpperCase().includes('MBTI')) return 'ri-user-star-line';
  if (name?.toUpperCase().includes('DISC')) return 'ri-pie-chart-line';
  if (name?.toUpperCase().includes('EPQ')) return 'ri-mental-health-line';
  return 'ri-survey-line';
};

// 格式化日期
const formatDate = (dateStr: string): string => {
  if (!dateStr) return '--';
  try {
    return new Date(dateStr).toLocaleDateString('zh-CN');
  } catch {
    return '--';
  }
};

// 获取测评类型标签
const getTypeLabel = (name: string): string => {
  if (name?.toUpperCase().includes('MBTI')) return 'MBTI';
  if (name?.toUpperCase().includes('DISC')) return 'DISC';
  if (name?.toUpperCase().includes('EPQ')) return 'EPQ';
  return '测评';
};

// 切换页码
const goToPage = (page: number) => {
  if (page >= 1 && page <= totalPages.value) {
    currentPage.value = page;
  }
};
</script>

<template>
  <div class="assessment-list-container" v-if="professionalAssessments.length > 0">
    <!-- 头部 -->
    <div class="list-header">
      <div class="header-title">
        <i class="ri-file-list-3-line"></i>
        <span>专业测评记录</span>
        <span class="count-badge">{{ professionalAssessments.length }}</span>
      </div>
      <div class="header-hint">
        <i class="ri-information-line"></i>
        点击查看完整画像
      </div>
    </div>

    <!-- 测评卡片列表 -->
    <div class="assessment-cards">
      <div 
        v-for="assessment in paginatedAssessments" 
        :key="assessment.submission_id"
        class="assessment-card"
        @click="handleClick(assessment)"
      >
        <div class="card-icon">
          <i :class="getIcon(assessment.questionnaire_name)"></i>
        </div>
        <div class="card-content">
          <div class="card-name">{{ assessment.questionnaire_name }}</div>
          <div class="card-meta">
            <span class="type-tag" :class="getTypeLabel(assessment.questionnaire_name).toLowerCase()">
              {{ getTypeLabel(assessment.questionnaire_name) }}
            </span>
            <span class="date">
              <i class="ri-calendar-event-line"></i>
              {{ formatDate(assessment.completed_at) }}
            </span>
          </div>
        </div>
        <div class="card-score" v-if="assessment.total_score !== null">
          <span class="score-value">{{ Math.round(assessment.total_score) }}</span>
          <span class="score-label">分</span>
        </div>
        <div class="card-arrow">
          <i class="ri-arrow-right-s-line"></i>
        </div>
      </div>
    </div>

    <!-- 分页器 -->
    <div v-if="totalPages > 1" class="list-pagination">
      <button class="page-btn" :disabled="currentPage === 1" @click="goToPage(currentPage - 1)">
        <i class="ri-arrow-left-s-line"></i>
      </button>
      <span class="page-info">{{ currentPage }} / {{ totalPages }}</span>
      <button class="page-btn" :disabled="currentPage === totalPages" @click="goToPage(currentPage + 1)">
        <i class="ri-arrow-right-s-line"></i>
      </button>
    </div>
  </div>

  <!-- 无专业测评时的空状态 -->
  <div class="no-assessments" v-else>
    <div class="empty-icon">
      <i class="ri-file-search-line"></i>
    </div>
    <p class="empty-text">暂无专业测评记录</p>
    <p class="empty-hint">完成 MBTI、DISC 或 EPQ 测评后，将在此显示画像分析</p>
  </div>
</template>

<style scoped>
.assessment-list-container {
  background: #f8fafc;
  border-radius: 16px;
  padding: 1.25rem;
  margin: 1rem 1.5rem;
}

.list-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 1rem;
}

.header-title {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-weight: 600;
  color: #374151;
  font-size: 0.9375rem;
}

.header-title i { color: #6366f1; }

.count-badge {
  background: linear-gradient(135deg, #6366f1, #8b5cf6);
  color: white;
  font-size: 0.75rem;
  padding: 0.125rem 0.5rem;
  border-radius: 10px;
  font-weight: 600;
}

.header-hint {
  display: flex;
  align-items: center;
  gap: 0.375rem;
  font-size: 0.75rem;
  color: #9ca3af;
}

.header-hint i { font-size: 0.875rem; }

/* 测评卡片 */
.assessment-cards {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.assessment-card {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 1rem 1.25rem;
  background: white;
  border: 1px solid #e5e7eb;
  border-radius: 14px;
  cursor: pointer;
  transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
}

.assessment-card:hover {
  border-color: #6366f1;
  box-shadow: 0 4px 16px rgba(99, 102, 241, 0.15);
  transform: translateX(4px);
}

.card-icon {
  width: 48px;
  height: 48px;
  border-radius: 12px;
  background: linear-gradient(135deg, #6366f1, #8b5cf6);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.card-icon i { color: white; font-size: 1.375rem; }

.card-content { flex: 1; min-width: 0; }

.card-name {
  font-weight: 600;
  color: #1f2937;
  font-size: 0.9375rem;
  margin-bottom: 0.375rem;
}

.card-meta {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.type-tag {
  font-size: 0.6875rem;
  padding: 0.1875rem 0.5rem;
  border-radius: 4px;
  font-weight: 600;
}

.type-tag.mbti { background: #dbeafe; color: #1d4ed8; }
.type-tag.disc { background: #fef3c7; color: #d97706; }
.type-tag.epq { background: #ede9fe; color: #7c3aed; }

.date {
  display: flex;
  align-items: center;
  gap: 0.25rem;
  font-size: 0.75rem;
  color: #9ca3af;
}

.date i { font-size: 0.875rem; }

.card-score { 
  display: flex; 
  align-items: baseline; 
  gap: 0.125rem;
  padding-right: 0.5rem;
}
.score-value { font-size: 1.5rem; font-weight: 700; color: #6366f1; }
.score-label { font-size: 0.8125rem; color: #9ca3af; }

.card-arrow {
  color: #c7d2fe;
  font-size: 1.5rem;
  transition: all 0.2s;
}

.assessment-card:hover .card-arrow {
  color: #6366f1;
  transform: translateX(2px);
}

/* 分页器 */
.list-pagination {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.75rem;
  margin-top: 1rem;
  padding-top: 1rem;
  border-top: 1px solid #e5e7eb;
}

.page-btn {
  width: 32px;
  height: 32px;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  background: white;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  color: #6b7280;
  transition: all 0.2s;
}

.page-btn:hover:not(:disabled) { border-color: #6366f1; color: #6366f1; }
.page-btn:disabled { opacity: 0.4; cursor: not-allowed; }
.page-info { font-size: 0.875rem; color: #6b7280; }

/* 空状态 */
.no-assessments {
  text-align: center;
  padding: 2.5rem 2rem;
  margin: 1rem 1.5rem;
  background: #f8fafc;
  border-radius: 16px;
}

.empty-icon {
  width: 64px;
  height: 64px;
  border-radius: 50%;
  background: linear-gradient(135deg, #e0e7ff, #c7d2fe);
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto 1rem;
}

.empty-icon i {
  font-size: 1.75rem;
  color: #6366f1;
}

.empty-text {
  font-size: 1rem;
  font-weight: 600;
  color: #374151;
  margin: 0 0 0.375rem;
}

.empty-hint {
  font-size: 0.8125rem;
  color: #9ca3af;
  margin: 0;
}
</style>
