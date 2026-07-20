/**
 * 测评中心 API
 */
import { apiRequest, apiRequestWithBody } from "./client";
import { MOCK_QUESTIONNAIRES, MOCK_ASSESSMENTS, MOCK_SUBMISSIONS } from "./mocks/assessments";
import { getQuestionsForQuestionnaireType } from "./assessmentFallbacks";

import type {
  Questionnaire,
  QuestionnaireDetail,
  QuestionnaireCreate,
  QuestionnaireUpdate,
  QuestionnaireListParams,
  QuestionnaireLibraryCategory,
  QuestionnaireLibraryCategorySummary,
  QuestionnaireLibraryCategoryCreate,
  QuestionnaireLibraryCategoryUpdate,
  QuestionnaireTag,
  QuestionnaireTagSummary,
  QuestionnaireTagCreate,
  QuestionnaireTagUpdate,
  QuestionnaireBulkLibraryCategoryUpdate,
  QuestionnaireBulkLibraryCategoryResult,
  Assessment,
  DepartmentRoutingConfig,
  AssessmentCreate,
  FormField,
  PageTexts,
  AssessmentUpdate,
  Submission,
  AnswerExportOption,
  AnswerExportQuestion,
  AnswerExportSubmission,
  QuestionnaireAnswerExportData,
  SubmissionStatistics,
  QuestionOptionStat,
  TextAnswerGroup,
  TextSummary,
  ScoreSummary,
  QuestionScoreStats,
  QuestionStat,
  DailyTrend,
  QuestionnaireQuestionStats,
  PublicAssessmentInfo,
  PublicSubmissionStart,
  SubmitCheckResult,
  SubmissionStart,
  QuestionnaireImportResponse
} from './assessmentTypes';
import { buildQuestionnaireListSearch, QUESTIONNAIRE_LIBRARY_API_PATHS } from './assessmentTypes';
export { buildQuestionnaireListSearch, QUESTIONNAIRE_LIBRARY_API_PATHS } from './assessmentTypes';
export type {
  Questionnaire,
  QuestionnaireDetail,
  QuestionnaireCreate,
  QuestionnaireUpdate,
  QuestionnaireListParams,
  QuestionnaireLibraryCategorySummary,
  QuestionnaireLibraryCategory,
  QuestionnaireLibraryCategoryCreate,
  QuestionnaireLibraryCategoryUpdate,
  QuestionnaireTagSummary,
  QuestionnaireTag,
  QuestionnaireTagCreate,
  QuestionnaireTagUpdate,
  QuestionnaireBulkLibraryCategoryUpdate,
  QuestionnaireBulkLibraryCategoryResult,
  QuestionnaireLibrarySort,
  Assessment,
  DepartmentRoutingConfig,
  AssessmentCreate,
  FormField,
  PageTexts,
  AssessmentUpdate,
  Submission,
  AnswerExportOption,
  AnswerExportQuestion,
  AnswerExportSubmission,
  QuestionnaireAnswerExportData,
  SubmissionStatistics,
  QuestionOptionStat,
  TextAnswerGroup,
  TextSummary,
  ScoreSummary,
  QuestionScoreStats,
  QuestionStat,
  DailyTrend,
  QuestionnaireQuestionStats,
  PublicAssessmentInfo,
  PublicSubmissionStart,
  SubmitCheckResult,
  SubmissionStart,
  QuestionnaireImportResponse
} from './assessmentTypes';

// ========== 问卷管理 ==========




export const fetchQuestionnaires = (params?: QuestionnaireListParams) => {
  const search = buildQuestionnaireListSearch(params);
  const qs = search.toString();

  // 根据 category 过滤 Mock 数据
  const filteredMockData = filterQuestionnairesByCategory(MOCK_QUESTIONNAIRES, params?.category);

  const fallback = params?.category === 'custom'
    ? undefined
    : { items: filteredMockData, total: filteredMockData.length };

  return apiRequest<{ items: Questionnaire[]; total: number }>({
    path: `/api/assessments/questionnaires${qs ? `?${qs}` : ""}`,
    ...(fallback ? { fallback } : {}),
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

export const updateQuestionnaire = (id: number, data: QuestionnaireUpdate) => {
  return apiRequestWithBody<Questionnaire>({
    path: `/api/assessments/questionnaires/${id}`,
    method: "PUT",
    body: data,
    fallback: {} as Questionnaire,
    auth: false,
  });
};

// ========== 问卷库业务分类与标签 ==========

export const fetchQuestionnaireLibraryCategories = () => {
  return apiRequest<QuestionnaireLibraryCategory[]>({
    path: QUESTIONNAIRE_LIBRARY_API_PATHS.categories,
    fallback: [],
    auth: false,
  });
};

export const createQuestionnaireLibraryCategory = (data: QuestionnaireLibraryCategoryCreate) => {
  return apiRequestWithBody<QuestionnaireLibraryCategorySummary>({
    path: QUESTIONNAIRE_LIBRARY_API_PATHS.categories,
    method: 'POST',
    body: data,
    auth: false,
  });
};

export const updateQuestionnaireLibraryCategory = (
  categoryId: number,
  data: QuestionnaireLibraryCategoryUpdate,
) => {
  return apiRequestWithBody<QuestionnaireLibraryCategorySummary>({
    path: QUESTIONNAIRE_LIBRARY_API_PATHS.category(categoryId),
    method: 'PUT',
    body: data,
    auth: false,
  });
};

export const reorderQuestionnaireLibraryCategories = async (categoryIds: number[]) => {
  return apiRequestWithBody<QuestionnaireLibraryCategorySummary[]>({
    path: QUESTIONNAIRE_LIBRARY_API_PATHS.reorderCategories,
    method: 'PUT',
    body: { category_ids: categoryIds },
    auth: false,
  });
};

export const fetchQuestionnaireTags = () => {
  return apiRequest<QuestionnaireTag[]>({
    path: QUESTIONNAIRE_LIBRARY_API_PATHS.tags,
    fallback: [],
    auth: false,
  });
};

export const createQuestionnaireTag = (data: QuestionnaireTagCreate) => {
  return apiRequestWithBody<QuestionnaireTagSummary>({
    path: QUESTIONNAIRE_LIBRARY_API_PATHS.tags,
    method: 'POST',
    body: data,
    auth: false,
  });
};

export const updateQuestionnaireTag = (tagId: number, data: QuestionnaireTagUpdate) => {
  return apiRequestWithBody<QuestionnaireTagSummary>({
    path: QUESTIONNAIRE_LIBRARY_API_PATHS.tag(tagId),
    method: 'PUT',
    body: data,
    auth: false,
  });
};

export const mergeQuestionnaireTag = (sourceTagId: number, targetTagId: number) => {
  return apiRequestWithBody<QuestionnaireTagSummary>({
    path: QUESTIONNAIRE_LIBRARY_API_PATHS.mergeTag(sourceTagId),
    method: 'POST',
    body: { target_tag_id: targetTagId },
    auth: false,
  });
};

export const fetchQuestionnaireCreatorOptions = () => {
  return apiRequest<string[]>({
    path: QUESTIONNAIRE_LIBRARY_API_PATHS.creators,
    fallback: [],
    auth: false,
  });
};

export const bulkUpdateQuestionnaireLibraryCategory = (
  data: QuestionnaireBulkLibraryCategoryUpdate,
) => {
  return apiRequestWithBody<QuestionnaireBulkLibraryCategoryResult>({
    path: QUESTIONNAIRE_LIBRARY_API_PATHS.bulkCategory,
    method: 'PUT',
    body: data,
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

export const copyQuestionnaire = (id: number) => {
  return apiRequestWithBody<Questionnaire>({
    path: `/api/assessments/questionnaires/${id}/copy`,
    method: "POST",
    auth: false,
  });
};

export const recalculateQuestionnaireScores = (id: number) => {
  return apiRequestWithBody<{
    questionnaire_id: number;
    updated_count: number;
    skipped_count: number;
    average_score: number | null;
    score_summary?: ScoreSummary | null;
  }>({
    path: `/api/assessments/questionnaires/${id}/recalculate-scores`,
    method: "POST",
    auth: true,
  });
};

// ========== 测评管理 ==========




// 表单字段配置

// 页面文案配置

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
    anonymous_mode: data.anonymous_mode,
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






export const fetchSubmissions = (params?: {
  assessment_id?: number;
  questionnaire_id?: number;
  status?: string;
  skip?: number;
  limit?: number;
  category?: string;  // ⭐ 按问卷分类过滤
}) => {
  const search = new URLSearchParams();
  if (params?.assessment_id) search.append("assessment_id", String(params.assessment_id));
  if (params?.questionnaire_id) search.append("questionnaire_id", String(params.questionnaire_id));
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
    auth: true, // 使用真实接口，失败时回退到 mock
  });
};

export const fetchQuestionnaireAnswerExport = (questionnaireId: number) => {
  return apiRequest<QuestionnaireAnswerExportData>({
    path: `/api/assessments/questionnaires/${questionnaireId}/answer-export`,
    auth: true,
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






export const fetchQuestionnaireQuestionStats = (questionnaireId: number, range: 'week' | 'month' = 'week') => {
  const ts = Date.now();
  const search = new URLSearchParams({ range, ts: String(ts) })
  return apiRequest<QuestionnaireQuestionStats>({
    path: `/api/assessments/questionnaires/${questionnaireId}/question-stats?${search.toString()}`,
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
      grade_percentages: { A: 0, B: 0, C: 0, D: 0 },
      score_summary: null,
      scoring_enabled: false,
      score_status: 'not_scored',
      scored_submission_count: 0,
      unscored_submission_count: 0,
    },
    auth: false,
  });
};

export {
  checkCanSubmit,
  fetchPublicAssessment,
  startAssessment,
  submitAnswers,
} from './publicAssessmentApi';

export { importQuestionnaire } from './questionnaireImport';
