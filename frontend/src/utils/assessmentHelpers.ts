/**
 * 测评相关辅助函数
 */

/**
 * 获取MBTI维度标签
 */
export const getDimensionLabel = (key: string): string => {
  const labels: Record<string, string> = {
    'EI': 'E/I (外向/内向)',
    'SN': 'S/N (感觉/直觉)',
    'TF': 'T/F (思考/情感)',
    'JP': 'J/P (判断/知觉)'
  };
  return labels[key] || key;
};

/**
 * 获取DISC维度标签
 */
export const getDISCLabel = (key: string): string => {
  const labels: Record<string, string> = {
    'D': '支配型',
    'I': '影响型',
    'S': '稳健型',
    'C': '谨慎型'
  };
  return labels[key] || key;
};

/**
 * 获取状态徽章配置
 */
export const getStatusBadge = (status: string): { class: string; text: string } => {
  return status === "completed"
    ? { class: "status-completed", text: "已完成" }
    : { class: "status-progress", text: "进行中" };
};

/**
 * 获取题目类型名称（统一支持新旧两种格式）
 */
export const getQuestionTypeName = (type: string): string => {
  const names: Record<string, string> = {
    // 新格式（用于答案数据）
    'single_choice': '单选题',
    'multiple_choice': '多选题',
    'short_text': '短文本',
    'long_text': '长文本',
    'scale': '评分题',
    'nps': 'NPS题',
    'date': '日期题',
    'yes_no': '是否题',
    'choice': '二选一',
    // 旧格式（用于问卷编辑器）
    'radio': '单选题',
    'checkbox': '多选题',
    'text': '单行文本',
    'textarea': '多行文本',
    'yesno': '是非题'
  };
  return names[type] || type;
};

/**
 * 格式化答案用于Excel导出
 */
export const formatAnswerForExcel = (answer: any, questionType: string): string => {
  if (!answer) return '未填写';
  
  switch (questionType) {
    case 'single_choice':
      return answer.label || answer.value || '未选择';
    
    case 'multiple_choice':
      // 多选题可能是 {values: [...]} 或 {labels: [...]} 格式
      if (answer.labels && Array.isArray(answer.labels)) {
        return answer.labels.join('、') || '未选择';
      }
      return (answer.values || []).join('、') || '未选择';
    
    case 'scale':
    case 'nps':
      return `${answer.value || 0}分`;
    
    case 'short_text':
    case 'long_text':
      return answer.value || '未填写';
    
    case 'yes_no':
      return answer.boolean ? '是' : '否';
    
    case 'date':
      return answer.date ? new Date(answer.date).toLocaleDateString('zh-CN') : '未填写';
    
    default:
      // 通用处理
      if (typeof answer === 'string') return answer;
      if (typeof answer === 'number') return String(answer);
      if (typeof answer === 'boolean') return answer ? '是' : '否';
      if (answer.label) return answer.label;
      if (answer.value !== undefined) return String(answer.value);
      if (answer.labels && Array.isArray(answer.labels)) return answer.labels.join('、');
      if (answer.values && Array.isArray(answer.values)) return answer.values.join('、');
      return JSON.stringify(answer);
  }
};

/**
 * 获取等级对应的CSS类名
 */
export const getGradeClass = (grade: string | null | undefined): string => {
  if (!grade) return '';
  const gradeMap: Record<string, string> = {
    'A': 'grade-a',
    'B': 'grade-b',
    'C': 'grade-c',
    'D': 'grade-d',
  };
  return gradeMap[grade.toUpperCase()] || '';
};

/**
 * 格式化日期时间
 */
export const formatDateTime = (dateStr: string | null | undefined): string => {
  if (!dateStr) return '-';
  try {
    return new Date(dateStr).toLocaleString('zh-CN', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
    });
  } catch {
    return dateStr;
  }
};

/**
 * 格式化日期
 */
export const formatDate = (dateStr: string | null | undefined): string => {
  if (!dateStr) return '-';
  try {
    return new Date(dateStr).toLocaleDateString('zh-CN');
  } catch {
    return dateStr;
  }
};

