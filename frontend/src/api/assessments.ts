/**
 * 测评中心 API
 */
import { apiRequest, apiRequestWithBody } from "./client";
import { MOCK_QUESTIONNAIRES, MOCK_ASSESSMENTS, MOCK_SUBMISSIONS } from "./mocks/assessments";
import { PRESET_QUESTIONS } from "../data/preset-questions";

// ========== 问卷管理 ==========

export interface Questionnaire {
  id: number;
  name: string;
  type: string; // EPQ/DISC/MBTI
  questions_count: number;
  estimated_minutes: number;
  status: string;
  created_at: string;
  updated_at: string;
}

export interface QuestionnaireDetail extends Questionnaire {
  questions_data: any;
  scoring_rules: any;
}

export interface QuestionnaireCreate {
  name: string;
  type: string;
  description?: string;
  questions_count?: number;
  estimated_minutes?: number;
  questions_data?: any;
  scoring_rules?: any;
}

export const fetchQuestionnaires = (params?: {
  skip?: number;
  limit?: number;
  category?: string;  // professional/scored/survey
}) => {
  const search = new URLSearchParams();
  if (params?.skip) search.append("skip", String(params.skip));
  if (params?.limit) search.append("limit", String(params.limit));
  if (params?.category) search.append("category", params.category);
  const qs = search.toString();
  
  // 根据 category 过滤 Mock 数据
  const filteredMockData = filterQuestionnairesByCategory(MOCK_QUESTIONNAIRES, params?.category);
  
  return apiRequest<{ items: Questionnaire[]; total: number }>({
    path: `/api/assessments/questionnaires${qs ? `?${qs}` : ""}`,
    fallback: { items: filteredMockData, total: filteredMockData.length },
    auth: false,
  });
};

// 根据 category 过滤问卷
const filterQuestionnairesByCategory = (questionnaires: Questionnaire[], category?: string): Questionnaire[] => {
  if (!category) return questionnaires;
  
  // 专业测评类型
  const professionalTypes = ['MBTI', 'DISC', 'EPQ'];
  
  switch (category) {
    case 'professional':
      // 只返回专业测评类型（MBTI, DISC, EPQ）
      return questionnaires.filter(q => professionalTypes.includes(q.type.toUpperCase()));
    case 'scored':
      // 只返回评分问卷（CUSTOM 类型且 custom_type 为 scored）
      return questionnaires.filter(q => 
        q.type.toUpperCase() === 'CUSTOM' && 
        (q as any).custom_type === 'scored'
      );
    case 'survey':
      // 只返回普通问卷（CUSTOM 类型且 custom_type 为 non_scored 或无 custom_type）
      return questionnaires.filter(q => 
        q.type.toUpperCase() === 'CUSTOM' && 
        ((q as any).custom_type === 'non_scored' || !(q as any).custom_type)
      );
    case 'custom':
      // 返回所有自定义问卷（CUSTOM 类型）
      return questionnaires.filter(q => q.type.toUpperCase() === 'CUSTOM');
    default:
      return questionnaires;
  }
};

export const fetchQuestionnaireDetail = (id: number) => {
  return apiRequest<QuestionnaireDetail>({
    path: `/api/assessments/questionnaires/${id}`,
    fallback: {} as QuestionnaireDetail,
    auth: false,
  });
};

export const createQuestionnaire = (data: QuestionnaireCreate) => {
  return apiRequestWithBody<Questionnaire>({
    path: "/api/assessments/questionnaires",
    method: "POST",
    body: data,
    fallback: {} as Questionnaire,
    auth: false,
  });
};

export const updateQuestionnaire = (id: number, data: Partial<QuestionnaireCreate>) => {
  return apiRequestWithBody<Questionnaire>({
    path: `/api/assessments/questionnaires/${id}`,
    method: "PUT",
    body: data,
    fallback: {} as Questionnaire,
    auth: false,
  });
};

export const deleteQuestionnaire = (id: number) => {
  return apiRequestWithBody<void>({
    path: `/api/assessments/questionnaires/${id}`,
    method: "DELETE",
    auth: false,
  });
};

// ========== 测评管理 ==========

export interface Assessment {
  id: number;
  name: string;
  code: string;
  questionnaire_id: number;
  valid_from: string;
  valid_until: string;
  description?: string;
  qr_code_url?: string;
  created_at: string;
}

export interface AssessmentCreate {
  name: string;
  questionnaire_id: number;
  valid_from: string;
  valid_until: string;
  description?: string;
  form_fields?: FormField[];
  page_texts?: PageTexts;
  link_type?: string;
  allow_repeat?: boolean;
  repeat_check_by?: string;
  repeat_interval_hours?: number;
  max_submissions?: number;
}

// 表单字段配置
export interface FormField {
  id: string;
  name?: string;
  label: string;
  type: string;
  placeholder?: string;
  required: boolean;
  enabled: boolean;
  options?: string[] | Array<{ value: string; label: string }>;  // 支持两种格式
  builtin?: boolean;
}

// 页面文案配置
export interface PageTexts {
  welcomeText?: string;
  introText?: string;
  guideText?: string;
  privacyText?: string;
  successTitle?: string;
  successMessage?: string;
  resultText?: string;
  contactText?: string;
}

export const fetchAssessments = (params?: {
  skip?: number;
  limit?: number;
}) => {
  const search = new URLSearchParams();
  if (params?.skip) search.append("skip", String(params.skip));
  if (params?.limit) search.append("limit", String(params.limit));
  const qs = search.toString();
  
  return apiRequest<{ items: Assessment[]; total: number }>({
    path: `/api/assessments${qs ? `?${qs}` : ""}`,
    fallback: { items: MOCK_ASSESSMENTS, total: MOCK_ASSESSMENTS.length },
    auth: false,
  });
};

export const createAssessment = (data: AssessmentCreate) => {
  // 构建fallback：生成一个有效的Assessment对象
  const timestamp = Date.now().toString().slice(-6);
  const random = Math.random().toString(36).slice(2, 8).toUpperCase();
  const code = `ASS_${timestamp}_${random}`;
  
  const fallbackData: Assessment = {
    id: MOCK_ASSESSMENTS.length + 1,
    name: data.name,
    code: code,
    questionnaire_id: data.questionnaire_id,
    valid_from: data.valid_from,
    valid_until: data.valid_until,
    description: data.description,
    created_at: new Date().toISOString()
  };
  
  // 同时添加到Mock数据中，这样后续查询时能找到
  MOCK_ASSESSMENTS.push(fallbackData);
  
  return apiRequestWithBody<Assessment>({
    path: "/api/assessments",
    method: "POST",
    body: data,
    fallback: fallbackData,
    auth: false,
  });
};

// ⭐ 更新测评配置
export interface AssessmentUpdate {
  name?: string;
  valid_from?: string;
  valid_until?: string;
  description?: string;
  form_fields?: any[];
  page_texts?: any;
  link_type?: string;
  allow_repeat?: boolean;
  repeat_check_by?: string;
  repeat_interval_hours?: number;
  max_submissions?: number;
}

export const updateAssessment = (id: number, data: AssessmentUpdate) => {
  // 同时更新Mock数据（仅Mock模式）
  const index = MOCK_ASSESSMENTS.findIndex(a => a.id === id);
  if (index !== -1) {
    Object.assign(MOCK_ASSESSMENTS[index], data);
  }
  
  return apiRequestWithBody<Assessment>({
    path: `/api/assessments/${id}`,
    method: "PUT",
    body: data,
    fallback: MOCK_ASSESSMENTS[index] || {} as Assessment,
    auth: false,
  });
};

// ⭐ 删除测评（分发链接）
export const deleteAssessment = async (id: number, force: boolean = false): Promise<any> => {
  // 同时从Mock数据中删除（仅Mock模式）
  const index = MOCK_ASSESSMENTS.findIndex(a => a.id === id);
  if (index !== -1) {
    MOCK_ASSESSMENTS.splice(index, 1);
  }
  
  return apiRequestWithBody<any>({
    path: `/api/assessments/${id}${force ? '?force=true' : ''}`,
    method: "DELETE",
    auth: false,
  });
};

// ========== 提交记录管理 ==========

export interface Submission {
  id: number;
  code: string;
  candidate_name: string;
  candidate_phone: string;
  questionnaire_id?: number;  // ⭐ 新增：问卷ID，用于前端过滤
  questionnaire_name?: string;
  questionnaire_type?: string;
  total_score?: number;
  grade?: string;
  status: string;
  started_at: string;
  submitted_at?: string;
  result_details?: any; // 测评维度详细数据 (MBTI/DISC/EPQ等)
}

export const fetchSubmissions = (params?: {
  assessment_id?: number;
  status?: string;
  skip?: number;
  limit?: number;
  category?: string;  // ⭐ 按问卷分类过滤
}) => {
  const search = new URLSearchParams();
  if (params?.assessment_id) search.append("assessment_id", String(params.assessment_id));
  if (params?.status) search.append("status", params.status);
  if (params?.skip) search.append("skip", String(params.skip));
  if (params?.limit) search.append("limit", String(params.limit));
  if (params?.category) search.append("category", params.category);
  const qs = search.toString();
  
  // ⭐ 根据 category 过滤 Mock 数据
  const filteredSubmissions = filterSubmissionsByCategory(MOCK_SUBMISSIONS, params?.category);
  
  return apiRequest<{ items: Submission[]; total: number }>({
    path: `/api/assessments/submissions${qs ? `?${qs}` : ""}`,
    fallback: { items: filteredSubmissions, total: filteredSubmissions.length },
    auth: false,
  });
};

// ⭐ 按 category 过滤提交记录
function filterSubmissionsByCategory(submissions: Submission[], category?: string): Submission[] {
  if (!category) return submissions;
  
  // 专业测评类型
  const professionalTypes = ['MBTI', 'DISC', 'EPQ'];
  
  if (category === 'professional') {
    return submissions.filter(s => professionalTypes.includes(s.questionnaire_type?.toUpperCase() || ''));
  } else if (category === 'custom' || category === 'scored' || category === 'survey') {
    // 自定义问卷（非专业测评）
    return submissions.filter(s => !professionalTypes.includes(s.questionnaire_type?.toUpperCase() || ''));
  }
  
  return submissions;
}

export const deleteSubmission = (id: number) => {
  // 同时从Mock数据中删除（仅Mock模式）
  const index = MOCK_SUBMISSIONS.findIndex(s => s.id === id);
  if (index !== -1) {
    MOCK_SUBMISSIONS.splice(index, 1);
  }
  
  return apiRequestWithBody<void>({
    path: `/api/assessments/submissions/${id}`,
    method: "DELETE",
    auth: false,
  });
};

// ========== 统计 API ==========

export interface SubmissionStatistics {
  total_submissions: number;
  average_score: number;
  pass_rate: number;
  grade_distribution: Record<string, number>;
  grade_percentages: Record<string, number>;
  submissions: Array<{
    id: number;
    candidate_name: string;
    candidate_phone: string;
    total_score: number | null;
    grade: string | null;
    submitted_at: string | null;
  }>;
}

export const fetchSubmissionStatistics = (params?: {
  category?: string;
  questionnaire_id?: number;
}) => {
  const search = new URLSearchParams();
  if (params?.category) search.append("category", params.category);
  if (params?.questionnaire_id) search.append("questionnaire_id", String(params.questionnaire_id));
  const qs = search.toString();
  
  return apiRequest<SubmissionStatistics>({
    path: `/api/assessments/statistics${qs ? `?${qs}` : ""}`,
    fallback: {
      total_submissions: 0,
      average_score: 0,
      pass_rate: 0,
      grade_distribution: { A: 0, B: 0, C: 0, D: 0 },
      grade_percentages: { A: 0, B: 0, C: 0, D: 0 },
      submissions: []
    },
    auth: false,
  });
};

// ⭐ V42: 题目答案统计接口
export interface QuestionOptionStat {
  index: number;
  text: string;
  count: number;
  percentage: number;
}

export interface QuestionStat {
  id: string;
  index: number;
  text: string;
  type: string;  // single, multiple, text, rating
  total_answers: number;
  options: QuestionOptionStat[];
}

export interface DailyTrend {
  date: string;
  count: number;
}

export interface QuestionnaireQuestionStats {
  questionnaire_id: number;
  questionnaire_name: string;
  questionnaire_type: string;
  questionnaire_category: string;
  total_submissions: number;
  completion_rate: number;
  average_score: number | null;
  average_duration_minutes: number | null;
  questions: QuestionStat[];
  daily_trend: DailyTrend[];
  grade_distribution: Record<string, number>;
  grade_percentages: Record<string, number>;
}

export const fetchQuestionnaireQuestionStats = (questionnaireId: number) => {
  return apiRequest<QuestionnaireQuestionStats>({
    path: `/api/assessments/questionnaires/${questionnaireId}/question-stats`,
    fallback: {
      questionnaire_id: questionnaireId,
      questionnaire_name: '',
      questionnaire_type: '',
      questionnaire_category: '',
      total_submissions: 0,
      completion_rate: 0,
      average_score: null,
      average_duration_minutes: null,
      questions: [],
      daily_trend: [],
      grade_distribution: { A: 0, B: 0, C: 0, D: 0 },
      grade_percentages: { A: 0, B: 0, C: 0, D: 0 }
    },
    auth: false,
  });
};

// ========== 公开API（候选人端） ==========

export interface PublicAssessmentInfo {
  name: string;
  type: string;
  questions_count: number;
  estimated_minutes: number;
  valid: boolean;
  expired: boolean;
  description?: string;
  form_fields?: any[];
  page_texts?: {
    intro_text?: string;
    guide_text?: string;
    privacy_text?: string;
    success_title?: string;
    success_message?: string;
    success_tips?: string;
  };
  questions?: any[];  // ⭐ 问卷题目数据（用于 fallback）
  // ⭐ 重复提交配置
  allow_repeat?: boolean;
  repeat_check_by?: string;
  repeat_interval_hours?: number;
  max_submissions?: number;
}

// ⭐ 重复提交检测结果
export interface SubmitCheckResult {
  can_submit: boolean;
  reason: string;
  submission_number: number;
  previous_submissions: Array<{
    code: string;
    submitted_at: string;
    status: string;
    total_score?: number;
    grade?: string;
  }>;
}

// 检查是否可以提交
export const checkCanSubmit = (code: string, phone: string, name: string = "") => {
  return apiRequestWithBody<SubmitCheckResult>({
    path: `/api/public/assessment/${code}/check-submit`,
    method: "POST",
    body: { phone, name },
    fallback: { can_submit: true, reason: "", submission_number: 1, previous_submissions: [] },
    auth: false,
  });
}

export interface SubmissionStart {
  candidate_name: string;
  candidate_phone: string;
  candidate_email?: string;
  target_position?: string;
}

export const fetchPublicAssessment = (code: string) => {
  // 构建fallback数据
  const assessment = MOCK_ASSESSMENTS.find(a => a.code === code);
  const questionnaire = assessment 
    ? MOCK_QUESTIONNAIRES.find(q => q.id === assessment.questionnaire_id)
    : null;
  
  const now = new Date();
  const validFrom = assessment ? new Date(assessment.valid_from) : now;
  const validUntil = assessment ? new Date(assessment.valid_until) : now;
  
  const fallbackData: PublicAssessmentInfo = assessment && questionnaire ? {
    name: questionnaire.name,
    type: questionnaire.type,
    questions_count: questionnaire.questions_count,
    estimated_minutes: questionnaire.estimated_minutes,
    valid: now >= validFrom && now <= validUntil,
    expired: now > validUntil,
    description: assessment.description || questionnaire.name,
    form_fields: [
      { id: 1, name: 'candidate_name', label: '姓名', type: 'text', enabled: true, required: true, builtin: true },
      { id: 2, name: 'candidate_phone', label: '手机号', type: 'text', enabled: true, required: true, builtin: true }
    ],
    page_texts: {
      intro_text: '请认真填写以下信息',
      privacy_text: '我们将严格保护您的隐私',
      success_title: '提交成功',
      success_message: '感谢您的参与！',
      success_tips: '我们会尽快处理您的测评结果'
    }
  } : {
    name: '未找到测评',
    type: 'UNKNOWN',
    questions_count: 0,
    estimated_minutes: 0,
    valid: false,
    expired: false,
    description: '测评不存在'
  } as PublicAssessmentInfo;
  
  return apiRequest<PublicAssessmentInfo>({
    path: `/api/public/assessment/${code}`,
    fallback: fallbackData,
    auth: false,
  });
};

export const startAssessment = (code: string, data: SubmissionStart, questionnaireType?: string, questionsData?: any[]) => {
  // 构建fallback数据
  const assessment = MOCK_ASSESSMENTS.find(a => a.code === code);
  const questionnaire = assessment 
    ? MOCK_QUESTIONNAIRES.find(q => q.id === assessment.questionnaire_id)
    : null;
  
  // 生成submission code
  const timestamp = Date.now().toString().slice(-6);
  const random = Math.random().toString(36).slice(2, 8).toUpperCase();
  const submissionCode = `SUB_${timestamp}_${random}`;
  
  // ⭐ 获取正确的题目列表
  // 优先级：1. 传入的实际题目数据 2. 根据类型获取预设题目 3. 示例题目
  let questions: any[];
  if (questionsData && questionsData.length > 0) {
    // 使用传入的实际问卷题目数据
    questions = questionsData;
    console.log('[startAssessment] Using actual questions data:', questions.length);
  } else {
    // 使用预设题目或示例题目
    questions = getQuestionsForQuestionnaireType(questionnaireType || questionnaire?.type);
    console.log('[startAssessment] Using preset/sample questions:', questions.length);
  }
  
  const fallbackData = {
    submission_code: submissionCode,
    questions: questions
  };
  
  // ⭐ 调试日志
  console.log('[startAssessment] code:', code);
  console.log('[startAssessment] questionnaireType:', questionnaireType);
  console.log('[startAssessment] fallback questions count:', questions.length);
  
  // ⚠️ 重要：开始测评操作不使用fallback，确保失败时能正确抛出错误
  // 如果使用fallback，会创建一个假的submission_code，后续提交会失败
  return apiRequestWithBody<{ submission_code: string; questions: any[] }>({
    path: `/api/public/assessment/${code}/start`,
    method: "POST",
    body: { ...data, assessment_code: code },
    // 不提供fallback，确保API失败时抛出错误
    auth: false,
  });
};

// ⭐ 根据问卷类型字符串获取题目列表
function getQuestionsForQuestionnaireType(typeStr: string | null | undefined): any[] {
  if (!typeStr) return [];
  
  const type = typeStr.toUpperCase();
  
  // 专业测评使用预设题目
  if (type === 'EPQ') {
    return PRESET_QUESTIONS.EPQ.map(q => ({
      id: q.id,
      type: q.type,
      text: q.text,
      required: q.required,
      dimension: q.dimension,
      positive: q.positive,
      options: q.type === 'yesno' ? [
        { label: '是', text: '是', value: 'yes' },
        { label: '否', text: '否', value: 'no' }
      ] : q.options?.map(o => ({ label: o.value, text: o.label, value: o.value }))
    }));
  }
  
  if (type === 'DISC') {
    return PRESET_QUESTIONS.DISC.map(q => ({
      id: q.id,
      type: q.type,
      text: q.text,
      required: q.required,
      dimension: q.dimension,
      options: q.options?.map(o => ({ label: o.value, text: o.label, value: o.value }))
    }));
  }
  
  if (type === 'MBTI') {
    return PRESET_QUESTIONS.MBTI.map(q => ({
      id: q.id,
      type: q.type,
      text: q.text,
      required: q.required,
      dimension: q.dimension,
      optionA: q.optionA,
      optionB: q.optionB,
      options: q.type === 'choice' ? [
        { label: 'A', text: q.optionA, value: 'A' },
        { label: 'B', text: q.optionB, value: 'B' }
      ] : undefined
    }));
  }
  
  // 自定义问卷返回示例题目
  return [
    { id: '1', type: 'radio', text: '示例题目1', required: true, options: [
      { label: 'A', text: '选项A', value: 'A' },
      { label: 'B', text: '选项B', value: 'B' },
      { label: 'C', text: '选项C', value: 'C' }
    ]},
    { id: '2', type: 'radio', text: '示例题目2', required: true, options: [
      { label: 'A', text: '选项A', value: 'A' },
      { label: 'B', text: '选项B', value: 'B' },
      { label: 'C', text: '选项C', value: 'C' }
    ]}
  ];
}

// ⭐ 根据问卷对象获取题目列表（保留旧函数以兼容）
function getQuestionsForQuestionnaire(questionnaire: Questionnaire | null | undefined): any[] {
  if (!questionnaire) return [];
  
  const type = questionnaire.type?.toUpperCase();
  
  // 专业测评使用预设题目
  if (type === 'EPQ') {
    return PRESET_QUESTIONS.EPQ.map(q => ({
      id: q.id,
      type: q.type,
      text: q.text,
      required: q.required,
      dimension: q.dimension,
      positive: q.positive,
      options: q.type === 'yesno' ? [
        { label: '是', text: '是', value: 'yes' },
        { label: '否', text: '否', value: 'no' }
      ] : q.options?.map(o => ({ label: o.value, text: o.label, value: o.value }))
    }));
  }
  
  if (type === 'DISC') {
    return PRESET_QUESTIONS.DISC.map(q => ({
      id: q.id,
      type: q.type,
      text: q.text,
      required: q.required,
      dimension: q.dimension,
      options: q.options?.map(o => ({ label: o.value, text: o.label, value: o.value }))
    }));
  }
  
  if (type === 'MBTI') {
    return PRESET_QUESTIONS.MBTI.map(q => ({
      id: q.id,
      type: q.type,
      text: q.text,
      required: q.required,
      dimension: q.dimension,
      optionA: q.optionA,
      optionB: q.optionB,
      options: q.type === 'choice' ? [
        { label: 'A', text: q.optionA, value: 'A' },
        { label: 'B', text: q.optionB, value: 'B' }
      ] : undefined
    }));
  }
  
  // 自定义问卷返回示例题目
  return [
    { id: '1', type: 'radio', text: `${questionnaire.name} - 示例题目1`, required: true, options: [
      { label: 'A', text: '选项A', value: 'A' },
      { label: 'B', text: '选项B', value: 'B' },
      { label: 'C', text: '选项C', value: 'C' }
    ]},
    { id: '2', type: 'radio', text: `${questionnaire.name} - 示例题目2`, required: true, options: [
      { label: 'A', text: '选项A', value: 'A' },
      { label: 'B', text: '选项B', value: 'B' },
      { label: 'C', text: '选项C', value: 'C' }
    ]}
  ];
}

export const submitAnswers = (submissionCode: string, answers: Record<string, any>) => {
  // 构建fallback：模拟成功提交并创建submission记录
  const timestamp = new Date().toISOString();
  
  // 尝试添加到MOCK_SUBMISSIONS（如果是mock环境）
  try {
    // 生成一个新的submission记录
    const newSubmission: Submission = {
      id: MOCK_SUBMISSIONS.length + 1,
      code: submissionCode,
      candidate_name: answers.candidate_name || '测试候选人',
      candidate_phone: answers.candidate_phone || '13800138000',
      questionnaire_name: '测试问卷',
      questionnaire_type: 'CUSTOM',
      total_score: undefined,
      grade: undefined,
      status: 'completed',
      started_at: new Date(Date.now() - 30 * 60 * 1000).toISOString(),
      submitted_at: timestamp,
      result_details: {
        custom_type: 'non_scored',
        answers: Object.entries(answers)
          .filter(([key]) => !['candidate_name', 'candidate_phone'].includes(key))
          .map(([questionId, answer], index) => ({
            question_id: questionId,
            question_title: `问题 ${index + 1}`,
            question_type: typeof answer === 'number' ? 'scale' : 'short_text',
            answer: typeof answer === 'number' ? { value: answer } : { value: String(answer) },
            scoring: null
          }))
      }
    };
    
    // 添加到mock数组（仅在mock模式下）
    MOCK_SUBMISSIONS.push(newSubmission);
    console.log('✅ Mock提交成功，已添加到MOCK_SUBMISSIONS:', newSubmission);
  } catch (e) {
    console.log('Mock提交处理:', e);
  }
  
  // ⚠️ 重要：提交操作不使用fallback，确保失败时能正确抛出错误
  return apiRequestWithBody<{ success: boolean; submission_code: string; submitted_at: string }>({
    path: `/api/public/assessment/submission/${submissionCode}/submit`,
    method: "POST",
    body: { submission_code: submissionCode, answers },
    // 不提供fallback，确保API失败时抛出错误
    auth: false,
  });
};


// ========== V43: 问卷导入 ==========

export interface QuestionnaireImportResponse {
  success: boolean;
  message: string;
  metadata: {
    name?: string;
    description?: string;
    estimated_minutes?: number;
  };
  questions: Array<{
    id: string;
    text: string;
    type: string;
    options: Array<{
      id: string;
      text: string;
      score: number;
    }>;
    required: boolean;
    score?: number;
  }>;
}

/**
 * 导入问卷文件
 * 支持格式：JSON、Excel、Word、纯文本
 * 
 * V45: 支持AI智能解析
 * @param file 问卷文件
 * @param useAI 是否使用AI智能解析（默认true）
 */
export const importQuestionnaire = async (
  file: File, 
  useAI: boolean = true
): Promise<QuestionnaireImportResponse> => {
  const formData = new FormData();
  formData.append('file', file);
  
  // V45: 添加use_ai参数
  const url = `/api/assessments/questionnaires/import?use_ai=${useAI}`;
  
  const response = await fetch(url, {
    method: 'POST',
    body: formData,
  });
  
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: '导入失败' }));
    throw new Error(error.detail || '导入失败');
  }
  
  return response.json();
};

