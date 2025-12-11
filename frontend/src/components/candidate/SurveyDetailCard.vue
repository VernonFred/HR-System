<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue';
import SurveyDrawer from './SurveyDrawer.vue';

// Props
const props = defineProps<{
  candidateId: number;
  candidateName: string;
}>();

// ⭐ V39: 抽屉状态
const drawerVisible = ref(false);
const selectedSubmission = ref<SurveySubmission | null>(null);

// 打开问卷详情抽屉
const openSurveyDrawer = (submission: SurveySubmission) => {
  selectedSubmission.value = submission;
  drawerVisible.value = true;
};

// 关闭抽屉
const closeSurveyDrawer = () => {
  drawerVisible.value = false;
};

// 类型定义
interface AnswerDetail {
  question_id: string;
  question_text: string;
  question_type: string;
  answer_value: string | number | null;
  answer_text: string | null;
  score: number | null;
}

interface SurveySubmission {
  id: number;
  code: string;
  questionnaire_id: number;
  questionnaire_name: string;
  questionnaire_type: string;
  questionnaire_category: string;
  total_score: number | null;
  max_score: number | null;
  score_percentage: number | null;
  grade: string | null;
  status: string;
  started_at: string | null;
  submitted_at: string | null;
  answers: Record<string, any>;
  answers_detail: AnswerDetail[];
  custom_data: Record<string, any>;
}

interface SurveyData {
  candidate_id: number;
  candidate_name: string;
  candidate_phone?: string;
  candidate_position?: string;
  candidate_gender?: string;
  candidate_email?: string;
  submissions: SurveySubmission[];
  total: number;
}

// 状态
const loading = ref(false);
const error = ref('');
const surveyData = ref<SurveyData | null>(null);

// ⭐ 问卷记录列表分页
const submissionListPage = ref(1);
const submissionListPageSize = 4; // 每页显示4条问卷记录

// 获取分页后的问卷记录列表
const paginatedSubmissions = computed(() => {
  if (!surveyData.value?.submissions) return [];
  const start = (submissionListPage.value - 1) * submissionListPageSize;
  const end = start + submissionListPageSize;
  return surveyData.value.submissions.slice(start, end);
});

// 问卷记录列表总页数
const submissionListTotalPages = computed(() => {
  if (!surveyData.value?.submissions) return 0;
  return Math.ceil(surveyData.value.submissions.length / submissionListPageSize);
});

// 切换问卷记录列表页码
const goToSubmissionListPage = (page: number) => {
  if (page >= 1 && page <= submissionListTotalPages.value) {
    submissionListPage.value = page;
  }
};

// ⭐ 折叠状态管理（每个问卷独立的展开/折叠状态）
const expandedSubmissions = ref<Set<number>>(new Set());

// ⭐ 每个问卷独立的分页状态
const submissionPages = ref<Map<number, number>>(new Map());
const pageSize = 5; // 每页显示5道题

// 切换问卷展开/折叠
const toggleSubmission = (submissionId: number) => {
  if (expandedSubmissions.value.has(submissionId)) {
    expandedSubmissions.value.delete(submissionId);
  } else {
    expandedSubmissions.value.add(submissionId);
    // 首次展开时初始化分页
    if (!submissionPages.value.has(submissionId)) {
      submissionPages.value.set(submissionId, 1);
    }
  }
};

// 检查问卷是否展开
const isExpanded = (submissionId: number) => {
  return expandedSubmissions.value.has(submissionId);
};

// 获取问卷的当前页码
const getSubmissionPage = (submissionId: number) => {
  return submissionPages.value.get(submissionId) || 1;
};

// 获取问卷的总页数
const getSubmissionTotalPages = (submission: SurveySubmission) => {
  return Math.ceil((submission.answers_detail?.length || 0) / pageSize);
};

// 获取问卷的分页后答题详情
const getPaginatedAnswers = (submission: SurveySubmission) => {
  const page = getSubmissionPage(submission.id);
  const start = (page - 1) * pageSize;
  const end = start + pageSize;
  return submission.answers_detail?.slice(start, end) || [];
};

// 切换问卷页码
const goToSubmissionPage = (submissionId: number, page: number, totalPages: number) => {
  if (page >= 1 && page <= totalPages) {
    submissionPages.value.set(submissionId, page);
  }
};

// 当前用于导出的问卷（最后展开的那个）
const activeSubmissionForExport = ref<SurveySubmission | null>(null);

// 设置导出问卷
const setExportSubmission = (submission: SurveySubmission) => {
  activeSubmissionForExport.value = submission;
};

// 格式化日期
const formatDate = (dateStr: string | null): string => {
  if (!dateStr) return '-';
  const date = new Date(dateStr);
  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  });
};

// 获取状态显示文本
const getStatusText = (status: string): string => {
  const statusMap: Record<string, string> = {
    'completed': '已完成',
    'in_progress': '进行中',
    'pending': '待开始'
  };
  return statusMap[status] || status;
};

// 获取状态样式类
const getStatusClass = (status: string): string => {
  const classMap: Record<string, string> = {
    'completed': 'status-completed',
    'in_progress': 'status-progress',
    'pending': 'status-pending'
  };
  return classMap[status] || '';
};

// 加载数据
const loadData = async () => {
  if (!props.candidateId) return;
  
  loading.value = true;
  error.value = '';
  
  try {
    // ⭐ 使用完整的后端API地址（添加 /api 前缀）
    const baseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:9000';
    const response = await fetch(`${baseUrl}/api/candidates/${props.candidateId}/survey-submissions`);
    if (!response.ok) {
      throw new Error('获取问卷调查数据失败');
    }
    surveyData.value = await response.json();
  } catch (e) {
    error.value = (e as Error).message || '加载失败';
    console.error('加载问卷调查数据失败:', e);
  } finally {
    loading.value = false;
  }
};

// 监听候选人ID变化
watch(() => props.candidateId, () => {
  // 重置所有状态
  expandedSubmissions.value.clear();
  submissionPages.value.clear();
  submissionListPage.value = 1; // 重置问卷记录列表分页
  loadData();
}, { immediate: true });

onMounted(() => {
  loadData();
});

// ⭐ 导出表格功能（支持导出指定问卷）
const exportToExcel = (submission?: SurveySubmission) => {
  const targetSubmission = submission || activeSubmissionForExport.value;
  if (!targetSubmission) {
    console.error('没有可导出的问卷数据');
    return;
  }
  
  console.log('开始导出问卷:', targetSubmission.questionnaire_name);
  console.log('候选人信息:', {
    name: surveyData.value?.candidate_name,
    phone: surveyData.value?.candidate_phone
  });
  
  // 构建CSV内容
  let csvContent = '\uFEFF'; // BOM for UTF-8
  
  // 添加头部信息
  csvContent += `问卷名称,${targetSubmission.questionnaire_name || '未知问卷'}\n`;
  csvContent += `填写人,${surveyData.value?.candidate_name || '未知'}\n`;
  csvContent += `手机号,${surveyData.value?.candidate_phone || '未填写'}\n`;
  csvContent += `提交时间,${formatDate(targetSubmission.submitted_at) || '未知'}\n`;
  csvContent += `状态,${getStatusText(targetSubmission.status)}\n`;
  
  // 如果有评分
  if (targetSubmission.questionnaire_category === 'scored' && targetSubmission.total_score !== null) {
    csvContent += `总分,${targetSubmission.total_score}\n`;
    csvContent += `满分,${targetSubmission.max_score || ''}\n`;
    csvContent += `得分率,${targetSubmission.score_percentage ? Math.round(targetSubmission.score_percentage) + '%' : ''}\n`;
    csvContent += `等级,${targetSubmission.grade || ''}\n`;
  }
  
  csvContent += '\n';
  
  // 添加答题详情表头
  csvContent += '题号,问题,答案';
  if (targetSubmission.questionnaire_category === 'scored') {
    csvContent += ',得分';
  }
  csvContent += '\n';
  
  // 添加答题详情数据
  const answers = targetSubmission.answers_detail || [];
  console.log('答题详情数量:', answers.length);
  
  answers.forEach((answer, index) => {
    const questionText = (answer.question_text || '未知问题').replace(/"/g, '""'); // 转义引号
    const answerText = (answer.answer_text || '未作答').replace(/"/g, '""');
    csvContent += `${index + 1},"${questionText}","${answerText}"`;
    if (targetSubmission.questionnaire_category === 'scored') {
      csvContent += `,${answer.score !== null ? answer.score : ''}`;
    }
    csvContent += '\n';
  });
  
  // 生成安全的文件名（移除特殊字符）
  const safeName = (surveyData.value?.candidate_name || '问卷').replace(/[<>:"/\\|?*]/g, '_');
  const safeQuestionnaireName = (targetSubmission.questionnaire_name || '问卷').replace(/[<>:"/\\|?*]/g, '_');
  const dateStr = new Date().toISOString().slice(0, 10);
  const fileName = `${safeName}_${safeQuestionnaireName}_${dateStr}.csv`;
  
  console.log('导出文件名:', fileName);
  
  // 创建并下载文件
  const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
  const link = document.createElement('a');
  const url = URL.createObjectURL(blob);
  link.setAttribute('href', url);
  link.setAttribute('download', fileName);
  link.style.visibility = 'hidden';
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url); // 释放URL对象
  
  console.log('导出完成');
};
</script>

<template>
  <div class="survey-detail-card">
    <!-- 加载状态 -->
    <div v-if="loading" class="loading-state">
      <div class="loading-spinner">
        <i class="ri-loader-4-line"></i>
      </div>
      <p>加载问卷调查数据...</p>
    </div>
    
    <!-- 错误状态 -->
    <div v-else-if="error" class="error-state">
      <i class="ri-error-warning-line"></i>
      <p>{{ error }}</p>
      <button @click="loadData" class="retry-btn">
        <i class="ri-refresh-line"></i>
        重试
      </button>
    </div>
    
    <!-- 无数据状态 -->
    <div v-else-if="!surveyData?.submissions.length" class="empty-state">
      <i class="ri-questionnaire-line"></i>
      <h3>暂无问卷调查记录</h3>
      <p>该人员尚未填写任何问卷调查</p>
    </div>
    
    <!-- 数据展示 -->
    <div v-else class="survey-content">
      <!-- 头部信息卡片 - 精致现代风格 -->
      <div class="profile-header-card">
        <!-- 背景装饰 -->
        <div class="header-bg-pattern"></div>
        
        <!-- 主要内容 -->
        <div class="header-main">
          <!-- 头像区域 -->
          <div class="avatar-section">
            <div class="avatar-ring">
              <div class="avatar-inner">
                <span class="avatar-text">{{ candidateName?.charAt(0) || '?' }}</span>
              </div>
            </div>
            <div class="survey-badge">
              <i class="ri-questionnaire-fill"></i>
              <span>{{ surveyData.total }}</span>
            </div>
          </div>
          
          <!-- 信息区域 -->
          <div class="info-section">
            <h2 class="person-name">{{ candidateName }}</h2>
            <div class="info-grid">
              <div class="info-item" v-if="surveyData.candidate_phone">
                <i class="ri-phone-line"></i>
                <span>{{ surveyData.candidate_phone }}</span>
              </div>
              <div class="info-item" v-if="surveyData.candidate_position && surveyData.candidate_position !== '未知岗位'">
                <i class="ri-briefcase-line"></i>
                <span>{{ surveyData.candidate_position }}</span>
              </div>
              <div class="info-item" v-if="surveyData.candidate_email">
                <i class="ri-mail-line"></i>
                <span>{{ surveyData.candidate_email }}</span>
              </div>
              <div class="info-item" v-if="surveyData.candidate_gender">
                <i :class="surveyData.candidate_gender === '男' ? 'ri-men-line' : 'ri-women-line'"></i>
                <span>{{ surveyData.candidate_gender }}</span>
              </div>
            </div>
          </div>
          
          <!-- 统计区域 -->
          <div class="stats-section">
            <div class="stat-item">
              <div class="stat-value">{{ surveyData.total }}</div>
              <div class="stat-label">问卷数量</div>
            </div>
            <div class="stat-divider"></div>
            <div class="stat-item">
              <div class="stat-value">{{ surveyData.submissions.filter(s => s.status === 'completed').length }}</div>
              <div class="stat-label">已完成</div>
            </div>
          </div>
          
        </div>
      </div>
      
      <!-- ⭐ 折叠式问卷列表区域 -->
      <div class="submissions-section">
        <div class="submissions-header">
          <h3 class="submissions-title">
            <i class="ri-file-list-3-line"></i>
            问卷记录
          </h3>
          <span class="submissions-count">{{ surveyData.submissions.length }} 份</span>
        </div>
        
        <!-- ⭐ V39: 问卷卡片列表（点击打开抽屉） -->
        <div class="submissions-list">
          <div
            v-for="sub in paginatedSubmissions"
            :key="sub.id"
            class="submission-card"
            @click="openSurveyDrawer(sub)"
          >
            <div class="submission-card-left">
                <div class="submission-icon" :class="getStatusClass(sub.status)">
                  <i class="ri-questionnaire-fill"></i>
                </div>
                <div class="submission-info">
                  <div class="submission-name">{{ sub.questionnaire_name }}</div>
                  <div class="submission-meta">
                    <span class="meta-time">
                      <i class="ri-time-line"></i>
                      {{ formatDate(sub.submitted_at) }}
                    </span>
                    <span class="meta-questions">
                      <i class="ri-list-check"></i>
                      {{ sub.answers_detail?.length || 0 }} 题
                    </span>
                  </div>
                </div>
              </div>
            <div class="submission-card-right">
                <span :class="['submission-status', getStatusClass(sub.status)]">
                  {{ getStatusText(sub.status) }}
                </span>
              <i class="ri-arrow-right-s-line view-arrow"></i>
            </div>
          </div>
        </div>
        
        <!-- ⭐ 问卷记录列表分页控件 -->
        <div v-if="submissionListTotalPages > 1" class="submissions-pagination">
          <button 
            class="page-btn prev"
            :disabled="submissionListPage === 1"
            @click="goToSubmissionListPage(submissionListPage - 1)"
          >
            <i class="ri-arrow-left-s-line"></i>
          </button>
          
          <div class="page-numbers">
            <button
              v-for="page in submissionListTotalPages"
              :key="page"
              class="page-num"
              :class="{ active: submissionListPage === page }"
              @click="goToSubmissionListPage(page)"
            >
              {{ page }}
            </button>
          </div>
          
          <button 
            class="page-btn next"
            :disabled="submissionListPage === submissionListTotalPages"
            @click="goToSubmissionListPage(submissionListPage + 1)"
          >
            <i class="ri-arrow-right-s-line"></i>
          </button>
          
          <span class="page-info">{{ submissionListPage }}/{{ submissionListTotalPages }}</span>
        </div>
      </div>
    </div>
    
    <!-- ⭐ V39: 问卷详情抽屉 -->
    <SurveyDrawer
      :visible="drawerVisible"
      :submission="selectedSubmission"
      :candidate-name="candidateName"
      :candidate-phone="surveyData?.candidate_phone"
      @close="closeSurveyDrawer"
    />
  </div>
</template>

<style scoped>
.survey-detail-card {
  background: linear-gradient(180deg, rgba(248, 250, 252, 0.95) 0%, rgba(241, 245, 249, 0.95) 100%);
  border-radius: 20px;
  border: 1px solid rgba(99, 102, 241, 0.1);
  overflow: visible; /* 允许内容溢出显示 */
  min-height: 400px;
}

/* 加载状态 */
.loading-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 4rem;
  color: var(--text-secondary);
}

.loading-spinner {
  font-size: 2.5rem;
  color: var(--primary-500);
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

/* 错误状态 */
.error-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 4rem;
  color: var(--error-500);
}

.error-state i {
  font-size: 3rem;
  margin-bottom: 1rem;
}

.retry-btn {
  margin-top: 1rem;
  padding: 0.5rem 1rem;
  background: var(--primary-500);
  color: white;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 0.5rem;
  transition: all 0.2s;
}

.retry-btn:hover {
  background: var(--primary-600);
}

/* 空状态 */
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 4rem;
  color: var(--text-secondary);
}

.empty-state i {
  font-size: 4rem;
  color: var(--text-tertiary);
  margin-bottom: 1rem;
}

.empty-state h3 {
  margin: 0;
  color: var(--text-primary);
  font-size: 1.25rem;
}

.empty-state p {
  margin: 0.5rem 0 0;
  font-size: 0.875rem;
}

/* 内容区域 */
.survey-content {
  padding: 1.25rem;
}

/* ⭐ 精致现代头部卡片 */
.profile-header-card {
  position: relative;
  background: white;
  border-radius: 16px;
  padding: 1.5rem;
  margin-bottom: 1.25rem;
  border: 1px solid rgba(6, 182, 212, 0.15);
  overflow: hidden;
  box-shadow: 0 4px 20px rgba(6, 182, 212, 0.08);
}

.header-bg-pattern {
  position: absolute;
  top: 0;
  left: 0;
  width: 150px;
  height: 100%;
  background: linear-gradient(135deg, rgba(6, 182, 212, 0.06) 0%, rgba(34, 211, 238, 0.03) 50%, transparent 100%);
  pointer-events: none;
  z-index: 0;
}

.header-main {
  position: relative;
  display: flex;
  align-items: center;
  gap: 1.5rem;
  z-index: 2;
}

/* 头像区域 */
.avatar-section {
  position: relative;
  flex-shrink: 0;
}

.avatar-ring {
  width: 72px;
  height: 72px;
  border-radius: 50%;
  background: linear-gradient(135deg, #06b6d4, #22d3ee);
  padding: 3px;
  box-shadow: 0 4px 16px rgba(6, 182, 212, 0.3);
}

.avatar-inner {
  width: 100%;
  height: 100%;
  border-radius: 50%;
  background: linear-gradient(180deg, #0891b2 0%, #06b6d4 100%);
  display: flex;
  align-items: center;
  justify-content: center;
}

.avatar-text {
  font-size: 1.75rem;
  font-weight: 700;
  color: white;
  text-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.survey-badge {
  position: absolute;
  bottom: -4px;
  right: -4px;
  display: flex;
  align-items: center;
  gap: 0.25rem;
  padding: 0.25rem 0.5rem;
  background: linear-gradient(135deg, #8b5cf6, #a78bfa);
  border-radius: 12px;
  font-size: 0.7rem;
  font-weight: 600;
  color: white;
  box-shadow: 0 2px 8px rgba(139, 92, 246, 0.4);
  border: 2px solid white;
}

.survey-badge i {
  font-size: 0.75rem;
}

/* 信息区域 */
.info-section {
  flex: 1;
  min-width: 0;
}

.person-name {
  margin: 0 0 0.75rem;
  font-size: 1.375rem;
  font-weight: 700;
  color: var(--text-primary);
  letter-spacing: -0.02em;
}

.info-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 0.75rem 1.5rem;
}

.info-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.875rem;
  color: var(--text-secondary);
}

.info-item i {
  font-size: 1rem;
  color: #06b6d4;
  opacity: 0.8;
}

/* 统计区域 */
.stats-section {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding-left: 1.25rem;
  border-left: 1px solid rgba(6, 182, 212, 0.15);
  flex-shrink: 0;
}

.stat-item {
  text-align: center;
  min-width: 60px;
}

.stat-value {
  font-size: 1.375rem;
  font-weight: 700;
  color: #06b6d4;
  line-height: 1.2;
}

.stat-label {
  font-size: 0.6875rem;
  color: var(--text-muted);
  margin-top: 0.25rem;
  white-space: nowrap;
}

.stat-divider {
  width: 1px;
  height: 28px;
  background: rgba(6, 182, 212, 0.15);
}

/* 导出按钮 */
.export-btn {
  width: 40px;
  height: 40px;
  border: 1px solid rgba(6, 182, 212, 0.2);
  background: white;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.25s ease;
  color: #06b6d4;
  margin-left: 0.75rem;
}

.export-btn:hover {
  background: linear-gradient(135deg, #06b6d4, #0891b2);
  border-color: transparent;
  color: white;
  box-shadow: 0 4px 12px rgba(6, 182, 212, 0.3);
  transform: translateY(-2px);
}

.export-btn i {
  font-size: 1.25rem;
}

/* ⭐ 问卷列表区域 */
.submissions-section {
  margin-bottom: 1.25rem;
}

.submissions-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 0.75rem;
  padding: 0 0.25rem;
}

.submissions-title {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin: 0;
  font-size: 0.9375rem;
  font-weight: 600;
  color: var(--text-primary);
}

.submissions-title i {
  color: #06b6d4;
  font-size: 1.125rem;
}

.submissions-count {
  font-size: 0.75rem;
  font-weight: 600;
  color: #06b6d4;
  background: rgba(6, 182, 212, 0.1);
  padding: 0.25rem 0.625rem;
  border-radius: 12px;
}

.submissions-list {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

/* ⭐ 折叠式问卷卡片 */
.submission-accordion {
  background: white;
  border: 1px solid rgba(6, 182, 212, 0.12);
  border-radius: 16px;
  overflow: hidden;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.submission-accordion:hover {
  border-color: rgba(6, 182, 212, 0.25);
  box-shadow: 0 4px 16px rgba(6, 182, 212, 0.08);
}

.submission-accordion.expanded {
  border-color: #06b6d4;
  box-shadow: 0 6px 24px rgba(6, 182, 212, 0.15);
}

/* 折叠头部 */
.accordion-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 1rem 1.25rem;
  cursor: pointer;
  transition: background 0.2s ease;
}

.accordion-header:hover {
  background: rgba(6, 182, 212, 0.03);
}

.submission-accordion.expanded .accordion-header {
  background: linear-gradient(135deg, rgba(6, 182, 212, 0.06) 0%, rgba(34, 211, 238, 0.03) 100%);
  border-bottom: 1px solid rgba(6, 182, 212, 0.1);
}

.accordion-left {
  display: flex;
  align-items: center;
  gap: 0.875rem;
}

.accordion-right {
  display: flex;
  align-items: center;
  gap: 0.625rem;
}

.accordion-arrow {
  font-size: 1.25rem;
  color: #06b6d4;
  transition: transform 0.3s ease;
}

.submission-accordion.expanded .accordion-arrow {
  transform: rotate(180deg);
}

/* 小导出按钮 */
.export-btn-small {
  width: 32px;
  height: 32px;
  border: 1px solid rgba(6, 182, 212, 0.2);
  background: white;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.2s ease;
  color: #06b6d4;
}

.export-btn-small:hover {
  background: #06b6d4;
  border-color: #06b6d4;
  color: white;
}

.export-btn-small i {
  font-size: 1rem;
}

/* 折叠内容区域 */
.accordion-content {
  padding: 1rem 1.25rem 1.25rem;
  background: rgba(248, 250, 252, 0.5);
  animation: slideDown 0.3s ease;
}

@keyframes slideDown {
  from {
    opacity: 0;
    transform: translateY(-10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

/* 内联评分区域 */
.score-section-inline {
  display: flex;
  gap: 1rem;
  margin-bottom: 1rem;
  padding: 0.75rem 1rem;
  background: white;
  border-radius: 12px;
  border: 1px solid rgba(6, 182, 212, 0.1);
}

.score-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.score-item .score-label {
  font-size: 0.75rem;
  color: var(--text-muted);
}

.score-item .score-value {
  font-size: 1rem;
  font-weight: 700;
  color: #06b6d4;
}

.score-item.grade .score-value {
  color: #8b5cf6;
}

/* 内联答题列表 */
.answers-inline {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.answer-item-inline {
  display: flex;
  gap: 0.75rem;
  padding: 0.75rem 1rem;
  background: white;
  border-radius: 10px;
  border: 1px solid rgba(6, 182, 212, 0.08);
}

.answer-item-inline:hover {
  border-color: rgba(6, 182, 212, 0.15);
}

/* 内联分页 */
.pagination-inline {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  margin-top: 1rem;
  padding-top: 1rem;
  border-top: 1px solid rgba(6, 182, 212, 0.1);
}

/* ⭐ 问卷记录列表分页 */
.submissions-pagination {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  margin-top: 1rem;
  padding: 0.75rem;
  background: rgba(6, 182, 212, 0.04);
  border-radius: 12px;
}

.submissions-pagination .page-btn {
  width: 32px;
  height: 32px;
  border: 1px solid rgba(6, 182, 212, 0.2);
  background: white;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.2s ease;
  color: #06b6d4;
}

.submissions-pagination .page-btn:hover:not(:disabled) {
  background: #06b6d4;
  border-color: #06b6d4;
  color: white;
}

.submissions-pagination .page-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.submissions-pagination .page-numbers {
  display: flex;
  gap: 0.25rem;
}

.submissions-pagination .page-num {
  min-width: 28px;
  height: 28px;
  border: none;
  background: transparent;
  border-radius: 6px;
  cursor: pointer;
  font-size: 0.8rem;
  font-weight: 500;
  color: var(--text-secondary);
  transition: all 0.2s ease;
}

.submissions-pagination .page-num:hover {
  background: rgba(6, 182, 212, 0.1);
  color: #06b6d4;
}

.submissions-pagination .page-num.active {
  background: #06b6d4;
  color: white;
}

.submissions-pagination .page-info {
  font-size: 0.75rem;
  color: var(--text-muted);
  margin-left: 0.5rem;
}

/* 旧的问卷卡片样式（保留兼容） */
.submission-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.875rem 1rem;
  background: white;
  border: 1px solid rgba(6, 182, 212, 0.12);
  border-radius: 14px;
  cursor: pointer;
  transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
}

.submission-card:hover {
  border-color: rgba(6, 182, 212, 0.3);
  background: rgba(6, 182, 212, 0.02);
  transform: translateX(4px);
  box-shadow: 0 4px 16px rgba(6, 182, 212, 0.1);
}

.submission-card.active {
  border-color: #06b6d4;
  background: linear-gradient(135deg, rgba(6, 182, 212, 0.08) 0%, rgba(34, 211, 238, 0.04) 100%);
  box-shadow: 0 4px 20px rgba(6, 182, 212, 0.15);
}

.submission-card-left {
  display: flex;
  align-items: center;
  gap: 0.875rem;
}

.submission-icon {
  width: 42px;
  height: 42px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.25rem;
  flex-shrink: 0;
}

.submission-icon.status-completed {
  background: linear-gradient(135deg, rgba(16, 185, 129, 0.15), rgba(16, 185, 129, 0.08));
  color: #059669;
}

.submission-icon.status-progress {
  background: linear-gradient(135deg, rgba(245, 158, 11, 0.15), rgba(245, 158, 11, 0.08));
  color: #d97706;
}

.submission-icon.status-pending {
  background: linear-gradient(135deg, rgba(107, 114, 128, 0.15), rgba(107, 114, 128, 0.08));
  color: #6b7280;
}

.submission-info {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.submission-name {
  font-size: 0.9rem;
  font-weight: 600;
  color: var(--text-primary);
  letter-spacing: -0.01em;
}

.submission-meta {
  display: flex;
  align-items: center;
  gap: 0.875rem;
  font-size: 0.75rem;
  color: var(--text-muted);
}

.submission-meta span {
  display: flex;
  align-items: center;
  gap: 0.25rem;
}

.submission-meta i {
  font-size: 0.8rem;
  opacity: 0.7;
}

.submission-card-right {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.submission-status {
  font-size: 0.7rem;
  font-weight: 600;
  padding: 0.25rem 0.625rem;
  border-radius: 10px;
  letter-spacing: 0.02em;
}

.submission-status.status-completed {
  background: rgba(16, 185, 129, 0.12);
  color: #059669;
}

.submission-status.status-progress {
  background: rgba(245, 158, 11, 0.12);
  color: #d97706;
}

.submission-status.status-pending {
  background: rgba(107, 114, 128, 0.12);
  color: #6b7280;
}

.active-arrow {
  color: #06b6d4;
  font-size: 1.25rem;
}

/* ⭐ V39: 查看箭头 */
.view-arrow {
  font-size: 1.25rem;
  color: #06b6d4;
  transition: transform 0.2s ease;
}

.submission-card:hover .view-arrow {
  transform: translateX(4px);
}

/* ⭐ 问卷头部 - 现代风格 */
.questionnaire-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 1rem;
  padding: 1rem 1.25rem;
  background: linear-gradient(135deg, rgba(6, 182, 212, 0.06) 0%, rgba(34, 211, 238, 0.03) 100%);
  border-radius: 14px;
  border: 1px solid rgba(6, 182, 212, 0.12);
}

.questionnaire-title {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.questionnaire-title i {
  font-size: 1.375rem;
  color: #06b6d4;
  background: linear-gradient(135deg, rgba(6, 182, 212, 0.15), rgba(34, 211, 238, 0.1));
  padding: 0.5rem;
  border-radius: 10px;
}

.questionnaire-title h3 {
  margin: 0;
  font-size: 1.0625rem;
  font-weight: 600;
  color: var(--text-primary);
  letter-spacing: -0.01em;
}

.questionnaire-meta {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.meta-item {
  display: flex;
  align-items: center;
  gap: 0.375rem;
  font-size: 0.8125rem;
  color: var(--text-secondary);
}

.meta-item i {
  color: #06b6d4;
  opacity: 0.7;
}

.status-badge {
  padding: 0.3rem 0.875rem;
  border-radius: 20px;
  font-size: 0.75rem;
  font-weight: 600;
  letter-spacing: 0.02em;
}

.status-completed {
  background: linear-gradient(135deg, rgba(16, 185, 129, 0.12), rgba(16, 185, 129, 0.06));
  color: #059669;
  border: 1px solid rgba(16, 185, 129, 0.2);
}

.status-progress {
  background: linear-gradient(135deg, rgba(245, 158, 11, 0.12), rgba(245, 158, 11, 0.06));
  color: #d97706;
  border: 1px solid rgba(245, 158, 11, 0.2);
}

.status-pending {
  background: linear-gradient(135deg, rgba(107, 114, 128, 0.12), rgba(107, 114, 128, 0.06));
  color: #6b7280;
  border: 1px solid rgba(107, 114, 128, 0.2);
}

/* ⭐ 评分区域 - 卡片式 */
.score-section {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(100px, 1fr));
  gap: 0.875rem;
  margin-bottom: 1.25rem;
}

.score-card {
  padding: 1rem 0.75rem;
  background: white;
  border-radius: 14px;
  border: 1px solid rgba(6, 182, 212, 0.12);
  text-align: center;
  transition: all 0.25s ease;
}

.score-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(6, 182, 212, 0.1);
}

.score-value {
  font-size: 1.625rem;
  font-weight: 700;
  background: linear-gradient(135deg, #06b6d4, #0891b2);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  margin-bottom: 0.25rem;
  line-height: 1.2;
}

.score-label {
  font-size: 0.7rem;
  color: var(--text-muted);
  letter-spacing: 0.02em;
}

.score-card.grade .score-value {
  background: linear-gradient(135deg, #8b5cf6, #a78bfa);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

/* ⭐ 答题详情 - 现代卡片式 */
.answers-section {
  background: white;
  border-radius: 16px;
  border: 1px solid rgba(6, 182, 212, 0.12);
  overflow: hidden;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.04);
}

.section-title {
  display: flex;
  align-items: center;
  gap: 0.625rem;
  margin: 0;
  padding: 1rem 1.25rem;
  font-size: 0.9375rem;
  font-weight: 600;
  color: var(--text-primary);
  background: linear-gradient(180deg, rgba(6, 182, 212, 0.06) 0%, rgba(6, 182, 212, 0.02) 100%);
  border-bottom: 1px solid rgba(6, 182, 212, 0.1);
}

.section-title i {
  color: #06b6d4;
  font-size: 1.125rem;
}

.answers-list {
  max-height: 360px;
  overflow-y: auto;
}

.answers-list::-webkit-scrollbar {
  width: 6px;
}

.answers-list::-webkit-scrollbar-track {
  background: rgba(6, 182, 212, 0.05);
}

.answers-list::-webkit-scrollbar-thumb {
  background: rgba(6, 182, 212, 0.2);
  border-radius: 3px;
}

.answers-list::-webkit-scrollbar-thumb:hover {
  background: rgba(6, 182, 212, 0.35);
}

.answer-item {
  display: flex;
  gap: 1rem;
  padding: 1rem 1.25rem;
  border-bottom: 1px solid rgba(6, 182, 212, 0.06);
  transition: all 0.2s ease;
}

.answer-item:last-child {
  border-bottom: none;
}

.answer-item:hover {
  background: rgba(6, 182, 212, 0.03);
}

.question-number {
  width: 30px;
  height: 30px;
  border-radius: 10px;
  background: linear-gradient(135deg, rgba(6, 182, 212, 0.15), rgba(34, 211, 238, 0.1));
  color: #0891b2;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.8rem;
  font-weight: 700;
  flex-shrink: 0;
}

.question-content {
  flex: 1;
  min-width: 0;
}

.question-text {
  margin: 0 0 0.5rem;
  font-size: 0.875rem;
  color: var(--text-primary);
  line-height: 1.55;
}

.answer-value {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.8125rem;
  color: #059669;
}

.answer-value i {
  font-size: 1rem;
  color: #10b981;
}

.answer-score {
  margin-left: auto;
  padding: 0.2rem 0.625rem;
  background: linear-gradient(135deg, rgba(139, 92, 246, 0.12), rgba(167, 139, 250, 0.08));
  color: #7c3aed;
  border-radius: 12px;
  font-size: 0.7rem;
  font-weight: 600;
  letter-spacing: 0.02em;
}

.answer-count {
  margin-left: auto;
  font-size: 0.75rem;
  font-weight: 500;
  color: var(--text-muted);
  background: rgba(6, 182, 212, 0.1);
  padding: 0.25rem 0.75rem;
  border-radius: 12px;
}

/* ⭐ 分页样式 */
.pagination {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  padding: 1rem 1.25rem;
  border-top: 1px solid rgba(6, 182, 212, 0.1);
  background: linear-gradient(180deg, rgba(6, 182, 212, 0.02) 0%, rgba(6, 182, 212, 0.04) 100%);
}

.page-btn {
  width: 32px;
  height: 32px;
  border: 1px solid rgba(6, 182, 212, 0.2);
  background: white;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.2s ease;
  color: var(--text-secondary);
}

.page-btn:hover:not(:disabled) {
  border-color: #06b6d4;
  color: #06b6d4;
  background: rgba(6, 182, 212, 0.05);
}

.page-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.page-btn i {
  font-size: 1.125rem;
}

.page-numbers {
  display: flex;
  gap: 0.25rem;
}

.page-num {
  min-width: 32px;
  height: 32px;
  border: 1px solid rgba(6, 182, 212, 0.15);
  background: white;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.2s ease;
  font-size: 0.8125rem;
  font-weight: 500;
  color: var(--text-secondary);
}

.page-num:hover {
  border-color: #06b6d4;
  color: #06b6d4;
}

.page-num.active {
  background: linear-gradient(135deg, #06b6d4, #0891b2);
  border-color: transparent;
  color: white;
  box-shadow: 0 2px 8px rgba(6, 182, 212, 0.3);
}

.page-info {
  margin-left: 0.75rem;
  font-size: 0.75rem;
  color: var(--text-muted);
}
</style>

