import type { DimensionScore } from "./submission";

export type Candidate = {
  id: number;
  name: string;
  position: string;
  phone: string;
  score: number;
  status: string;
  grade?: string;
  level?: string;
  tags?: string[];
  updated_at?: string;
  dimensions?: DimensionScore[];
  // ⭐ 提交类型标签：professional（专业测评）、survey（问卷调查）
  submission_types?: ('professional' | 'survey')[];
  // 性别：男/女
  gender?: '男' | '女';
};

export type CandidateListResponse = {
  items: Candidate[];
  page: number;
  pageSize: number;
  total: number;
};

export type PersonalityDimensionKey =
  | "extraversion"
  | "emotionalStability"
  | "openness"
  | "conscientiousness"
  | "teamwork"
  | "riskTaking";

export type PersonalityDimension = {
  key: PersonalityDimensionKey;
  label: string;
  score: number; // 0-100
};

export type CompetencyScore = {
  key: string;
  label: string;
  score: number; // 0-100
};

export type QuestionnaireType = 'EPQ' | 'MBTI' | 'DISC';

// MBTI 16种人格类型
export type MBTIType = 
  | 'INTJ' | 'INTP' | 'ENTJ' | 'ENTP'
  | 'INFJ' | 'INFP' | 'ENFJ' | 'ENFP'
  | 'ISTJ' | 'ISFJ' | 'ESTJ' | 'ESFJ'
  | 'ISTP' | 'ISFP' | 'ESTP' | 'ESFP';

// 测评记录类型
export type AssessmentRecord = {
  submission_id: number;
  assessment_name: string;
  questionnaire_name: string;
  questionnaire_type?: QuestionnaireType;
  total_score: number | null;
  max_score?: number | null;
  score_percentage?: number | null;
  grade?: string | null;
  completed_at: string;
};

// 🟢 P1-1: 交叉验证类型
export type TraitScore = {
  source: string;
  value: number;
};

export type TraitConsistencyCheck = {
  trait: string;
  scores: TraitScore[];
  mean: number;
  stdDev: number;
  consistency: number;
};

export type Contradiction = {
  trait: string;
  scores: number[];
  issue: string;
};

export type CrossValidationData = {
  consistency_score: number;
  confidence_level: string;
  assessment_count: number;
  consistency_checks: TraitConsistencyCheck[];
  contradictions: Contradiction[];
};

export type AssessmentInfo = {
  type: string;
  weight: number;
};

export type CandidateProfile = {
  id: string;
  name: string;
  avatarUrl?: string;
  appliedPosition: string;
  level?: string;
  updatedAt: string;
  overallMatchScore: number;
  tags: string[];
  questionnaireType?: QuestionnaireType; // 问卷类型，决定雷达图维度
  mbtiType?: MBTIType; // MBTI人格类型（仅当questionnaireType为'MBTI'时有效）
  personalityDimensions: PersonalityDimension[];
  competencies: CompetencyScore[];
  aiAnalysisText: string;
  highlights: string[];
  risks: string[];
  suitablePositions: string[];  // 推荐岗位
  unsuitablePositions: string[];  // 不适合岗位
  developmentSuggestions?: string[];  // 发展建议
  interviewFocus?: string[];  // 面试关注点
  hasResume?: boolean;
  resumeEducation?: string;
  resumeExperiences?: string;
  resumeSkills?: string[];
  resumeHighlights?: string[];
  assessments?: AssessmentRecord[];  // 测评记录列表
  crossValidation?: CrossValidationData;  // 🟢 P1-1: 交叉验证数据
  assessmentInfoList?: AssessmentInfo[];  // 🟢 P1-1: 测评信息列表（用于交叉验证）
  scoreBreakdown?: {  // 🟢 P0: 评分详情
    assessment: number;
    match: number;
    completeness: number;
    resume: number;
  };
  // 🟢 P1-2: 降级标识
  isFallbackAnalysis?: boolean;  // 是否为降级分析
  analysisMethod?: 'ai' | 'fallback';  // 分析方式
  fallbackReason?: 'ai_timeout' | 'ai_error' | 'ai_unavailable';  // 降级原因
};
