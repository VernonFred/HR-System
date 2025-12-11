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
/* 遮罩层 */
.drawer-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  backdrop-filter: blur(4px);
  z-index: 1000;
  display: flex;
  justify-content: flex-end;
}

/* 抽屉容器 */
.drawer-container {
  width: 65vw;
  max-width: 900px;
  min-width: 550px;
  height: 100vh;
  background: #f8fafc;
  display: flex;
  flex-direction: column;
  box-shadow: -8px 0 32px rgba(0, 0, 0, 0.15);
  position: relative;
}

/* 抽屉头部 */
.drawer-header {
  position: absolute;
  top: 1rem;
  right: 1rem;
  z-index: 100;
}

.close-btn {
  width: 40px;
  height: 40px;
  border: none;
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.9);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  color: #6b7280;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
}

.close-btn:hover { 
  background: white;
  color: #1f2937;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

.close-btn i { font-size: 1.5rem; }

/* 抽屉内容 */
.drawer-body {
  flex: 1;
  overflow-y: auto;
  overflow-x: hidden;
  padding: 1.5rem;
}

/* 问卷头部 */
.survey-header {
  position: relative;
  background: linear-gradient(135deg, #06b6d4 0%, #0891b2 100%);
  border-radius: 20px;
  padding: 2rem;
  margin-bottom: 1.5rem;
  overflow: hidden;
}

.header-bg-pattern {
  position: absolute;
  top: 0;
  right: 0;
  width: 300px;
  height: 100%;
  background: url("data:image/svg+xml,%3Csvg width='60' height='60' viewBox='0 0 60 60' xmlns='http://www.w3.org/2000/svg'%3E%3Cg fill='none' fill-rule='evenodd'%3E%3Cg fill='%23ffffff' fill-opacity='0.08'%3E%3Cpath d='M36 34v-4h-2v4h-4v2h4v4h2v-4h4v-2h-4zm0-30V0h-2v4h-4v2h4v4h2V6h4V4h-4zM6 34v-4H4v4H0v2h4v4h2v-4h4v-2H6zM6 4V0H4v4H0v2h4v4h2V6h4V4H6z'/%3E%3C/g%3E%3C/g%3E%3C/svg%3E");
  pointer-events: none;
}

.header-content {
  position: relative;
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  z-index: 1;
}

.header-left {
  display: flex;
  align-items: flex-start;
  gap: 1.25rem;
}

.survey-icon {
  width: 64px;
  height: 64px;
  background: rgba(255, 255, 255, 0.2);
  border-radius: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
  backdrop-filter: blur(10px);
}

.survey-icon i {
  font-size: 2rem;
  color: white;
}

.survey-info {
  flex: 1;
}

.survey-name {
  margin: 0 0 0.75rem;
  font-size: 1.5rem;
  font-weight: 700;
  color: white;
  text-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.survey-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 1rem;
}

.meta-item {
  display: flex;
  align-items: center;
  gap: 0.375rem;
  font-size: 0.875rem;
  color: rgba(255, 255, 255, 0.9);
}

.meta-item i {
  font-size: 1rem;
  color: white; /* V40: 图标改为纯白色，更明显 */
}

.header-right {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.status-badge {
  padding: 0.5rem 1rem;
  border-radius: 20px;
  font-size: 0.8rem;
  font-weight: 600;
  letter-spacing: 0.02em;
}

.status-badge.status-completed {
  background: rgba(16, 185, 129, 0.2);
  color: #d1fae5;
  border: 1px solid rgba(16, 185, 129, 0.3);
}

.status-badge.status-progress {
  background: rgba(245, 158, 11, 0.2);
  color: #fef3c7;
  border: 1px solid rgba(245, 158, 11, 0.3);
}

.status-badge.status-pending {
  background: rgba(255, 255, 255, 0.2);
  color: rgba(255, 255, 255, 0.9);
  border: 1px solid rgba(255, 255, 255, 0.3);
}

.export-btn {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.625rem 1.25rem;
  background: rgba(255, 255, 255, 0.2);
  border: 1px solid rgba(255, 255, 255, 0.3);
  border-radius: 12px;
  color: white;
  font-size: 0.875rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
  backdrop-filter: blur(10px);
}

.export-btn:hover {
  background: rgba(255, 255, 255, 0.3);
  transform: translateY(-1px);
}

.export-btn i {
  font-size: 1.125rem;
}

/* 评分区域 */
.score-section {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
  gap: 1rem;
  margin-bottom: 1.5rem;
}

.score-card {
  background: white;
  border-radius: 16px;
  padding: 1.25rem;
  text-align: center;
  border: 1px solid rgba(6, 182, 212, 0.15);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
  transition: all 0.2s;
}

.score-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 16px rgba(6, 182, 212, 0.1);
}

.score-card .score-value {
  font-size: 2rem;
  font-weight: 700;
  background: linear-gradient(135deg, #06b6d4, #0891b2);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  line-height: 1.2;
}

.score-card .score-label {
  font-size: 0.8rem;
  color: var(--text-muted);
  margin-top: 0.25rem;
}

.score-card.grade .score-value {
  background: linear-gradient(135deg, #8b5cf6, #a78bfa);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

/* 统计栏 */
.stats-bar {
  display: flex;
  gap: 1.5rem;
  padding: 1rem 1.25rem;
  background: white;
  border-radius: 12px;
  margin-bottom: 1.5rem;
  border: 1px solid rgba(6, 182, 212, 0.1);
}

.stats-bar .stat-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.875rem;
  color: var(--text-secondary);
}

.stats-bar .stat-item i {
  color: #06b6d4;
  font-size: 1.125rem;
}

/* 答题详情区域 */
.answers-section {
  background: white;
  border-radius: 16px;
  border: 1px solid rgba(6, 182, 212, 0.1);
  overflow: hidden;
}

.section-header {
  padding: 1rem 1.5rem;
  background: linear-gradient(180deg, rgba(6, 182, 212, 0.06) 0%, rgba(6, 182, 212, 0.02) 100%);
  border-bottom: 1px solid rgba(6, 182, 212, 0.1);
}

.section-title {
  display: flex;
  align-items: center;
  gap: 0.625rem;
  margin: 0;
  font-size: 1rem;
  font-weight: 600;
  color: var(--text-primary);
}

.section-title i {
  color: #06b6d4;
  font-size: 1.25rem;
}

.answers-list {
  padding: 0.5rem;
}

.answer-item {
  display: flex;
  gap: 1rem;
  padding: 1rem 1.25rem;
  margin: 0.5rem;
  background: rgba(248, 250, 252, 0.5);
  border-radius: 12px;
  border: 1px solid rgba(6, 182, 212, 0.06);
  transition: all 0.2s;
}

.answer-item:hover {
  background: rgba(6, 182, 212, 0.04);
  border-color: rgba(6, 182, 212, 0.15);
}

.question-number {
  width: 36px;
  height: 36px;
  border-radius: 10px;
  background: linear-gradient(135deg, #06b6d4, #0891b2);
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.875rem;
  font-weight: 700;
  flex-shrink: 0;
}

.question-content {
  flex: 1;
  min-width: 0;
}

.question-text {
  margin: 0 0 0.625rem;
  font-size: 0.9375rem;
  color: var(--text-primary);
  line-height: 1.6;
}

.answer-value {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.875rem;
  color: #059669;
}

.answer-value i {
  font-size: 1.125rem;
  color: #10b981;
}

.answer-score {
  margin-left: auto;
  padding: 0.25rem 0.75rem;
  background: linear-gradient(135deg, rgba(139, 92, 246, 0.12), rgba(167, 139, 250, 0.08));
  color: #7c3aed;
  border-radius: 12px;
  font-size: 0.75rem;
  font-weight: 600;
}

/* 分页 */
.pagination {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  padding: 1rem 1.5rem;
  border-top: 1px solid rgba(6, 182, 212, 0.1);
  background: linear-gradient(180deg, rgba(6, 182, 212, 0.02) 0%, rgba(6, 182, 212, 0.04) 100%);
}

.page-btn {
  width: 36px;
  height: 36px;
  border: 1px solid rgba(6, 182, 212, 0.2);
  background: white;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.2s;
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
  font-size: 1.25rem;
}

.page-numbers {
  display: flex;
  gap: 0.375rem;
}

.page-num {
  min-width: 36px;
  height: 36px;
  border: 1px solid rgba(6, 182, 212, 0.15);
  background: white;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.2s;
  font-size: 0.875rem;
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
  font-size: 0.8rem;
  color: var(--text-muted);
}

/* 动画 */
.drawer-enter-active,
.drawer-leave-active {
  transition: all 0.35s cubic-bezier(0.4, 0, 0.2, 1);
}

.drawer-enter-active .drawer-container,
.drawer-leave-active .drawer-container {
  transition: transform 0.35s cubic-bezier(0.4, 0, 0.2, 1);
}

.drawer-enter-from,
.drawer-leave-to {
  opacity: 0;
}

.drawer-enter-from .drawer-container,
.drawer-leave-to .drawer-container {
  transform: translateX(100%);
}

/* 滚动条美化 */
.drawer-body::-webkit-scrollbar {
  width: 6px;
}

.drawer-body::-webkit-scrollbar-track {
  background: transparent;
}

.drawer-body::-webkit-scrollbar-thumb {
  background: #d1d5db;
  border-radius: 3px;
}

.drawer-body::-webkit-scrollbar-thumb:hover {
  background: #9ca3af;
}

/* 响应式 */
@media (max-width: 768px) {
  .drawer-container {
    width: 100vw;
    min-width: unset;
  }
  
  .header-content {
    flex-direction: column;
    gap: 1rem;
  }
  
  .header-right {
    width: 100%;
    justify-content: space-between;
  }
}
</style>

