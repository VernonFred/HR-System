/**
 * 候选人画像API客户端
 * 用于对接后端画像整合API
 */

import { apiRequest } from './client';

// ========== 类型定义 ==========

export interface DimensionScore {
  name: string;
  score: number;
  weight: number;
  description?: string;
  weighted_score: number;
}

export interface JobMatchInfo {
  profile_id: number;
  profile_name: string;
  department?: string;
  match_score: number;
  dimension_scores: DimensionScore[];
  ai_analysis?: string;
  matched_at?: string;
}

export interface AssessmentInfo {
  submission_id: number;
  assessment_name: string;
  questionnaire_name: string;
  total_score?: number;
  max_score?: number;
  score_percentage?: number;
  grade?: string;
  completed_at?: string;
}

export interface CandidateBasicInfo {
  id: number;
  name: string;
  phone: string;
  email?: string;
  gender?: string;
  target_position?: string;
  created_at: string;
}

export interface CandidatePortrait {
  basic_info: CandidateBasicInfo;
  assessments: AssessmentInfo[];
  job_match?: JobMatchInfo;
  overall_score?: number;
  strengths: string[];
  improvements: string[];
  portrait_version: string;
  generated_at: string;
}

export interface CandidatePortraitSummary {
  candidate_id: number;
  name: string;
  target_position?: string;
  overall_score?: number;
  match_score?: number;
  assessment_count: number;
  has_job_match: boolean;
}

export interface CandidatePortraitListResponse {
  items: CandidatePortraitSummary[];
  total: number;
}

// ========== API函数 ==========

/**
 * 分析级别类型 - V5: 只保留 pro 和 expert
 */
export type AnalysisLevel = 'pro' | 'expert';

/**
 * 获取候选人完整画像
 * @param candidateId 候选人ID
 * @param refresh 是否强制刷新（跳过缓存）
 * @param analysisLevel 分析级别: pro(深度分析，默认)/expert(专家分析)
 * @returns 完整画像数据
 */
export const getCandidatePortrait = async (
  candidateId: number,
  refresh: boolean = false,
  analysisLevel: AnalysisLevel = 'pro'  // V5: 默认使用 pro
): Promise<CandidatePortrait> => {
  const params = new URLSearchParams();
  if (refresh) params.append('refresh', 'true');
  // V5: 始终传递 analysis_level 参数
  params.append('analysis_level', analysisLevel);
  const query = params.toString();
  return apiRequest({
    path: `/api/candidates/${candidateId}/portrait${query ? '?' + query : ''}`,
    auth: false,
  });
};

/**
 * 获取候选人画像列表（摘要）
 * @param params 查询参数
 * @returns 画像列表
 */
export const getCandidatePortraits = async (params?: {
  skip?: number;
  limit?: number;
  target_position?: string;
}): Promise<CandidatePortraitListResponse> => {
  const query = new URLSearchParams();
  if (params?.skip !== undefined) query.append('skip', params.skip.toString());
  if (params?.limit !== undefined) query.append('limit', params.limit.toString());
  if (params?.target_position) query.append('target_position', params.target_position);

  const queryString = query.toString();
  return apiRequest({
    path: `/api/candidates/portraits${queryString ? '?' + queryString : ''}`,
    auth: false,
  });
};

/**
 * 获取候选人画像缓存状态
 * @param candidateId 候选人ID
 * @returns 缓存状态，包含哪些分析级别已缓存
 */
export interface PortraitCacheStatus {
  candidate_id: number;
  data_version: string;
  cached_levels: {
    pro: boolean;
    expert: boolean;
  };
}

export const getPortraitCacheStatus = async (
  candidateId: number
): Promise<PortraitCacheStatus> => {
  return apiRequest({
    path: `/api/candidates/${candidateId}/portrait-cache-status`,
    auth: false,
  });
};

/**
 * 构建Mock画像数据（用于样式展示）
 * 保留用于前端样式预览，实际使用时调用真实API
 */
export const buildMockPortrait = (candidateId: number): CandidatePortrait => {
  return {
    basic_info: {
      id: candidateId,
      name: '张三',
      phone: '13800138000',
      email: 'zhangsan@example.com',
      gender: '男',
      target_position: '产品经理',
      created_at: new Date().toISOString(),
    },
    assessments: [
      {
        submission_id: 101,
        assessment_name: '产品经理能力测评',
        questionnaire_name: 'EPQ性格测试',
        total_score: 85.5,
        max_score: 100,
        score_percentage: 85.5,
        grade: 'A',
        completed_at: new Date(Date.now() - 86400000).toISOString(),
      },
      {
        submission_id: 102,
        assessment_name: '逻辑思维测试',
        questionnaire_name: '逻辑推理题',
        total_score: 78.0,
        max_score: 100,
        score_percentage: 78.0,
        grade: 'B',
        completed_at: new Date(Date.now() - 172800000).toISOString(),
      },
    ],
    job_match: {
      profile_id: 1,
      profile_name: '产品经理',
      department: '产品部',
      match_score: 87.3,
      dimension_scores: [
        {
          name: '产品规划能力',
          score: 85.5,
          weight: 30,
          description: '负责产品中长期规划',
          weighted_score: 25.65,
        },
        {
          name: '用户洞察能力',
          score: 88.0,
          weight: 25,
          description: '深入理解用户需求',
          weighted_score: 22.0,
        },
        {
          name: '逻辑思维能力',
          score: 78.0,
          weight: 20,
          description: '清晰的逻辑分析能力',
          weighted_score: 15.6,
        },
        {
          name: '沟通协调能力',
          score: 92.0,
          weight: 15,
          description: '跨部门协作沟通',
          weighted_score: 13.8,
        },
        {
          name: '执行落地能力',
          score: 82.0,
          weight: 10,
          description: '推动项目落地',
          weighted_score: 8.2,
        },
      ],
      ai_analysis:
        '候选人在产品经理岗位的综合匹配度为 87.3分。在用户洞察和沟通协调方面表现突出，具备较强的产品思维。建议在逻辑思维能力方面持续提升。',
      matched_at: new Date().toISOString(),
    },
    overall_score: 86.4,
    strengths: [
      '测评表现优秀，平均得分 81.8%',
      '与产品经理岗位高度匹配（87.3分）',
      '用户洞察能力表现突出（88.0分）',
      '沟通协调能力表现突出（92.0分）',
    ],
    improvements: [
      '逻辑思维能力需要提升（78.0分）',
      '建议多参与复杂问题分析，提升逻辑推理能力',
    ],
    portrait_version: '1.0',
    generated_at: new Date().toISOString(),
  };
};

