<script setup lang="ts">
/**
 * 问卷详情抽屉组件 - 从右侧滑出显示完整问卷详情
 * V39: 模仿画像抽屉的布局风格
 */
import { ref, computed, watch } from 'vue';

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

const props = defineProps<{
  visible: boolean;
  submission: SurveySubmission | null;
  candidateName: string;
  candidatePhone?: string;
}>();

const emit = defineEmits<{
  (e: 'close'): void;
}>();

// 分页
const currentPage = ref(1);
const pageSize = 10;

// 分页后的答题详情
const paginatedAnswers = computed(() => {
  if (!props.submission?.answers_detail) return [];
  const start = (currentPage.value - 1) * pageSize;
  const end = start + pageSize;
  return props.submission.answers_detail.slice(start, end);
});

// 总页数
const totalPages = computed(() => {
  if (!props.submission?.answers_detail) return 0;
  return Math.ceil(props.submission.answers_detail.length / pageSize);
});

// 切换页码
const goToPage = (page: number) => {
  if (page >= 1 && page <= totalPages.value) {
    currentPage.value = page;
  }
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

// 导出CSV
const exportToCSV = () => {
  if (!props.submission) return;
  
  let csvContent = '\uFEFF'; // BOM for UTF-8
  
  // 添加头部信息
  csvContent += `问卷名称,${props.submission.questionnaire_name || '未知问卷'}\n`;
  csvContent += `填写人,${props.candidateName || '未知'}\n`;
  csvContent += `手机号,${props.candidatePhone || '未填写'}\n`;
  csvContent += `提交时间,${formatDate(props.submission.submitted_at) || '未知'}\n`;
  csvContent += `状态,${getStatusText(props.submission.status)}\n`;
  
  // 如果有评分
  if (props.submission.questionnaire_category === 'scored' && props.submission.total_score !== null) {
    csvContent += `总分,${props.submission.total_score}\n`;
    csvContent += `满分,${props.submission.max_score || ''}\n`;
    csvContent += `得分率,${props.submission.score_percentage ? Math.round(props.submission.score_percentage) + '%' : ''}\n`;
    csvContent += `等级,${props.submission.grade || ''}\n`;
  }
  
  csvContent += '\n';
  
  // 添加答题详情表头
  csvContent += '题号,问题,答案';
  if (props.submission.questionnaire_category === 'scored') {
    csvContent += ',得分';
  }
  csvContent += '\n';
  
  // 添加答题详情数据
  const answers = props.submission.answers_detail || [];
  answers.forEach((answer, index) => {
    const questionText = (answer.question_text || '未知问题').replace(/"/g, '""');
    const answerText = (answer.answer_text || '未作答').replace(/"/g, '""');
    csvContent += `${index + 1},"${questionText}","${answerText}"`;
    if (props.submission?.questionnaire_category === 'scored') {
      csvContent += `,${answer.score !== null ? answer.score : ''}`;
    }
    csvContent += '\n';
  });
  
  // 生成安全的文件名
  const safeName = (props.candidateName || '问卷').replace(/[<>:"/\\|?*]/g, '_');
  const safeQuestionnaireName = (props.submission.questionnaire_name || '问卷').replace(/[<>:"/\\|?*]/g, '_');
  const dateStr = new Date().toISOString().slice(0, 10);
  const fileName = `${safeName}_${safeQuestionnaireName}_${dateStr}.csv`;
  
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
  URL.revokeObjectURL(url);
};

// 阻止滚动穿透
watch(() => props.visible, (val) => {
  document.body.style.overflow = val ? 'hidden' : '';
  // 重置分页
  if (val) {
    currentPage.value = 1;
  }
});
</script>

<template>
  <Teleport to="body">
    <Transition name="drawer">
      <div v-if="visible" class="drawer-overlay" @click.self="emit('close')">
        <div class="drawer-container">
          <!-- 抽屉头部 -->
          <div class="drawer-header">
            <button class="close-btn" @click="emit('close')" title="关闭">
              <i class="ri-close-line"></i>
            </button>
          </div>

          <!-- 抽屉内容 -->
          <div class="drawer-body" v-if="submission">
            <!-- 问卷信息头部 -->
            <div class="survey-header">
              <div class="header-bg-pattern"></div>
              <div class="header-content">
                <!-- 左侧：问卷图标和名称 -->
                <div class="header-left">
                  <div class="survey-icon">
                    <i class="ri-questionnaire-fill"></i>
                  </div>
                  <div class="survey-info">
                    <h2 class="survey-name">{{ submission.questionnaire_name }}</h2>
                    <div class="survey-meta">
                      <span class="meta-item">
                        <i class="ri-user-line"></i>
                        {{ candidateName }}
                      </span>
                      <span class="meta-item" v-if="candidatePhone">
                        <i class="ri-phone-line"></i>
                        {{ candidatePhone }}
                      </span>
                      <span class="meta-item">
                        <i class="ri-time-line"></i>
                        {{ formatDate(submission.submitted_at) }}
                      </span>
                    </div>
                  </div>
                </div>
                
                <!-- 右侧：状态和操作 -->
                <div class="header-right">
                  <span :class="['status-badge', getStatusClass(submission.status)]">
                    {{ getStatusText(submission.status) }}
                  </span>
                  <button class="export-btn" @click="exportToCSV" title="导出CSV">
                    <i class="ri-download-2-line"></i>
                    <span>导出</span>
                  </button>
                </div>
              </div>
            </div>
            
            <!-- 评分区域（如果有） -->
            <div v-if="submission.questionnaire_category === 'scored' && submission.total_score !== null" class="score-section">
              <div class="score-card">
                <div class="score-value">{{ submission.total_score }}</div>
                <div class="score-label">总分</div>
              </div>
              <div v-if="submission.max_score" class="score-card">
                <div class="score-value">{{ submission.max_score }}</div>
                <div class="score-label">满分</div>
              </div>
              <div v-if="submission.score_percentage !== null" class="score-card">
                <div class="score-value">{{ Math.round(submission.score_percentage) }}%</div>
                <div class="score-label">得分率</div>
              </div>
              <div v-if="submission.grade" class="score-card grade">
                <div class="score-value">{{ submission.grade }}</div>
                <div class="score-label">等级</div>
              </div>
            </div>
            
            <!-- 答题统计 -->
            <div class="stats-bar">
              <div class="stat-item">
                <i class="ri-list-check"></i>
                <span>共 {{ submission.answers_detail?.length || 0 }} 题</span>
              </div>
              <div class="stat-item">
                <i class="ri-file-text-line"></i>
                <span>{{ submission.questionnaire_type === 'scored' ? '计分问卷' : '普通问卷' }}</span>
              </div>
            </div>
            
            <!-- 答题详情列表 -->
            <div class="answers-section">
              <div class="section-header">
                <h3 class="section-title">
                  <i class="ri-file-list-3-line"></i>
                  答题详情
                </h3>
              </div>
              
              <div class="answers-list">
                <div 
                  v-for="(answer, index) in paginatedAnswers" 
                  :key="answer.question_id"
                  class="answer-item"
                >
                  <div class="question-number">
                    {{ (currentPage - 1) * pageSize + index + 1 }}
                  </div>
                  <div class="question-content">
                    <p class="question-text">{{ answer.question_text }}</p>
                    <div class="answer-value">
                      <i class="ri-checkbox-circle-line"></i>
                      <span>{{ answer.answer_text || '未作答' }}</span>
                      <span v-if="answer.score !== null && answer.score !== 0" class="answer-score">
                        +{{ answer.score }}分
                      </span>
                    </div>
                  </div>
                </div>
              </div>
              
              <!-- 分页 -->
              <div v-if="totalPages > 1" class="pagination">
                <button 
                  class="page-btn"
                  :disabled="currentPage === 1"
                  @click="goToPage(currentPage - 1)"
                >
                  <i class="ri-arrow-left-s-line"></i>
                </button>
                
                <div class="page-numbers">
                  <button
                    v-for="page in totalPages"
                    :key="page"
                    class="page-num"
                    :class="{ active: currentPage === page }"
                    @click="goToPage(page)"
                  >
                    {{ page }}
                  </button>
                </div>
                
                <button 
                  class="page-btn"
                  :disabled="currentPage === totalPages"
                  @click="goToPage(currentPage + 1)"
                >
                  <i class="ri-arrow-right-s-line"></i>
                </button>
                
                <span class="page-info">{{ currentPage }}/{{ totalPages }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
@import './styles/survey-drawer.css';
</style>
