/**
 * 问卷/测评 API 类型定义。
 */

export type QuestionnaireLibrarySort = 'updated_desc' | 'created_desc';

export const QUESTIONNAIRE_LIBRARY_API_PATHS = {
  base: '/api/assessments/library',
  categories: '/api/assessments/library/categories',
  reorderCategories: '/api/assessments/library/categories/reorder',
  category: (categoryId: number) => `/api/assessments/library/categories/${categoryId}`,
  tags: '/api/assessments/library/tags',
  tag: (tagId: number) => `/api/assessments/library/tags/${tagId}`,
  mergeTag: (sourceTagId: number) => `/api/assessments/library/tags/${sourceTagId}/merge`,
  creators: '/api/assessments/library/creators',
  bulkCategory: '/api/assessments/questionnaires/bulk-library-category',
} as const;

export interface QuestionnaireLibraryCategorySummary {
  id: number;
  name: string;
  sort_order: number;
  is_active: boolean;
  is_system: boolean;
}

export interface QuestionnaireLibraryCategory extends QuestionnaireLibraryCategorySummary {
  questionnaire_count: number;
}

export interface QuestionnaireTagSummary {
  id: number;
  name: string;
  is_active: boolean;
}

export interface QuestionnaireTag extends QuestionnaireTagSummary {
  questionnaire_count: number;
}

export interface QuestionnaireListParams {
  skip?: number;
  limit?: number;
  category?: string;
  library_category_id?: number;
  tag_ids?: number[];
  creator?: string;
  status?: string;
  custom_type?: 'scored' | 'non_scored';
  keyword?: string;
  sort?: QuestionnaireLibrarySort;
}

export interface QuestionnaireLibraryCategoryCreate {
  name: string;
  sort_order?: number;
}

export interface QuestionnaireLibraryCategoryUpdate {
  name?: string;
  sort_order?: number;
  is_active?: boolean;
}

export interface QuestionnaireTagCreate {
  name: string;
}

export interface QuestionnaireTagUpdate {
  name?: string;
  is_active?: boolean;
}

export interface QuestionnaireBulkLibraryCategoryUpdate {
  questionnaire_ids: number[];
  library_category_id: number;
}

export interface QuestionnaireBulkLibraryCategoryResult {
  updated_count: number;
}

const appendTrimmed = (search: URLSearchParams, key: string, value?: string) => {
  const normalized = value?.trim();
  if (normalized) search.append(key, normalized);
};

export const buildQuestionnaireListSearch = (params: QuestionnaireListParams = {}) => {
  const search = new URLSearchParams();
  if (params.skip !== undefined) search.append('skip', String(params.skip));
  if (params.limit !== undefined) search.append('limit', String(params.limit));
  appendTrimmed(search, 'category', params.category);
  if (params.library_category_id !== undefined) {
    search.append('library_category_id', String(params.library_category_id));
  }
  [...new Set(params.tag_ids || [])].forEach(tagId => search.append('tag_ids', String(tagId)));
  appendTrimmed(search, 'creator', params.creator);
  appendTrimmed(search, 'status', params.status);
  appendTrimmed(search, 'custom_type', params.custom_type);
  appendTrimmed(search, 'keyword', params.keyword);
  appendTrimmed(search, 'sort', params.sort);
  return search;
};

export interface Questionnaire {
  id: number;
  name: string;
  type: string; // EPQ/DISC/MBTI
  category?: string;
  description?: string;
  custom_type?: string;
  scoring_config?: any;
  purpose?: string;
  creator?: string;
  library_category?: QuestionnaireLibraryCategorySummary | null;
  tags?: QuestionnaireTagSummary[];
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
  category?: string;
  description?: string;
  questions_count?: number;
  estimated_minutes?: number;
  questions_data?: any;
  scoring_rules?: any;
  custom_type?: string;
  scoring_config?: any;
  purpose?: string;
  library_category_id?: number;
  tag_ids?: number[];
}

export interface QuestionnaireUpdate extends Partial<QuestionnaireCreate> {
  status?: string;
}

export interface Assessment {
  id: number;
  name: string;
  code: string;
  questionnaire_id: number;
  valid_from: string;
  valid_until: string;
  description?: string;
  qr_code_url?: string;
  form_fields?: FormField[];
  page_texts?: PageTexts;
  link_type?: string;
  allow_repeat?: boolean;
  repeat_check_by?: string;
  repeat_interval_hours?: number;
  max_submissions?: number;
  anonymous_mode?: boolean;
  routing_config?: DepartmentRoutingConfig;
  created_at: string;
}

export interface DepartmentRoutingConfig {
  enabled: boolean;
  department_field: string;
  fallback_to_default: boolean;
  mappings: Array<{
    department_value: string;
    questionnaire_id: number;
  }>;
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
  anonymous_mode?: boolean;
  routing_config?: DepartmentRoutingConfig;
}

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

export interface PageTexts {
  welcomeText?: string;
  introText?: string;
  guideText?: string;
  privacyText?: string;
  showBasicInfoTitle?: boolean; // 是否显示“请填写您的基本信息”
  successTitle?: string;
  successMessage?: string;
  resultText?: string;
  contactText?: string;
  showNextSteps?: boolean;  // 是否显示"接下来"区域
  nextStepsText?: string;   // "接下来"合并文本（用于兼容）
}

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
  anonymous_mode?: boolean;
  routing_config?: DepartmentRoutingConfig;
}

export interface Submission {
  id: number;
  code: string;
  candidate_name: string;
  candidate_phone: string;
  candidate_email?: string;
  gender?: string;
  target_position?: string;
  questionnaire_id?: number;  // ⭐ 新增：问卷ID，用于前端过滤
  questionnaire_name?: string;
  questionnaire_type?: string;
  total_score?: number;
  max_score?: number;
  score_percentage?: number;
  grade?: string;
  status: string;
  started_at: string;
  submitted_at?: string;
  result_details?: any; // 测评维度详细数据 (MBTI/DISC/EPQ等)
  custom_data?: Record<string, any> & {
    meeting_identity?: Record<string, any>;
  };  // 自定义字段（用于部门等信息展示）
}

export interface AnswerExportOption {
  index?: number;
  label?: string;
  text?: string;
  value?: string | number;
}

export interface AnswerExportQuestion {
  id: string | number;
  index: number;
  text: string;
  type: string;
  options?: AnswerExportOption[];
}

export interface AnswerExportSubmission {
  id: number;
  code: string;
  candidate_name?: string;
  candidate_phone?: string;
  candidate_email?: string;
  gender?: string;
  target_position?: string;
  status: string;
  started_at?: string;
  submitted_at?: string;
  answers: Record<string, any>;
}

export interface QuestionnaireAnswerExportData {
  questionnaire_id: number;
  questionnaire_name: string;
  questions: AnswerExportQuestion[];
  submissions: AnswerExportSubmission[];
}

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

export interface QuestionOptionStat {
  index?: number;
  text: string;
  count: number;
  percentage?: number;
}

export interface TextAnswerGroup {
  text: string;
  count: number;
}

export interface TextSummary {
  tags?: TextAnswerGroup[];
  long_answers?: TextAnswerGroup[];
  empty_count?: number;
  total_answers?: number;
}

export interface ScoreSummary {
  scored_submission_count: number;
  max_score: number | null;
  average_score: number | null;
  highest_score: number | null;
  lowest_score: number | null;
  average_percentage: number | null;
  grade_distribution?: Record<string, number>;
  grade_percentages?: Record<string, number>;
  high_score_rate?: number | null;
}

export interface QuestionScoreStats {
  scored_answer_count: number;
  average_raw_score: number | null;
  max_raw_score: number | null;
  average_score: number | null;
  max_score: number | null;
  average_percentage: number | null;
}

export interface QuestionStat {
  id: string;
  index: number;
  text: string;
  type: string;  // single, multiple, text, rating
  total_answers: number;
  total_selections?: number;
  options: QuestionOptionStat[];
  text_summary?: TextSummary;
  score_stats?: QuestionScoreStats | null;
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
  score_summary?: ScoreSummary | null;
  scoring_enabled?: boolean;
  score_status?: 'not_scored' | 'no_submissions' | 'pending_recalculation' | 'partially_scored' | 'scored';
  scored_submission_count?: number;
  unscored_submission_count?: number;
}

export interface PublicAssessmentInfo {
  name: string;
  type: string;
  category?: string;
  custom_type?: string;
  purpose?: string;
  questions_count: number;
  estimated_minutes: number;
  valid: boolean;
  expired: boolean;
  description?: string;
  form_fields?: any[];
  page_texts?: PageTexts & {
    intro_text?: string;
    guide_text?: string;
    privacy_text?: string;
    welcome_text?: string;
    show_basic_info_title?: boolean;
    success_title?: string;
    success_message?: string;
    success_tips?: string;
    result_text?: string;
    contact_text?: string;
    show_next_steps?: boolean;
  };
  questions?: any[];  // ⭐ 问卷题目数据（用于 fallback）
  // ⭐ 重复提交配置
  allow_repeat?: boolean;
  repeat_check_by?: string;
  repeat_interval_hours?: number;
  max_submissions?: number;
  anonymous_mode?: boolean;
  entry_prefill?: Record<string, any>;
}

export interface PublicSubmissionStart {
  submission_code: string;
  questions: any[];
  questionnaire_name?: string;
  questionnaire_type?: string;
  category?: string;
  custom_type?: string;
  purpose?: string;
  questions_count?: number;
  estimated_minutes?: number;
}

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

export interface SubmissionStart {
  candidate_name: string;
  candidate_phone: string;
  candidate_email?: string;
  target_position?: string;
  gender?: string;
  custom_data?: Record<string, any>;
  anonymous_device_id?: string;
  survey_token?: string;
  participant_url?: string;
  callback_url?: string;
}

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
