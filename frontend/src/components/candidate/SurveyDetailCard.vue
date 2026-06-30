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
    // ⭐ 生产环境使用相对路径（nginx代理）
    const baseUrl = import.meta.env.VITE_API_BASE_URL || '';
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
@import './styles/survey-detail-card.css';
</style>

