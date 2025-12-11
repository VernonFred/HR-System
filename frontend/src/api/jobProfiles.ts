/**
 * 岗位画像API客户端
 */

import { apiRequest, apiRequestWithBody } from './client';

// ========== 类型定义 ==========

export interface Dimension {
  name: string;
  weight: number;
  description?: string;
}

export interface JobProfile {
  id: number;
  name: string;
  department?: string;
  description?: string;
  tags: string[];
  dimensions: Dimension[];
  status: string;
  created_at: string;
  updated_at: string;
}

export interface JobProfileCreate {
  name: string;
  department?: string;
  description?: string;
  tags?: string[];
  dimensions: Dimension[];
}

export interface JobProfileUpdate {
  name?: string;
  department?: string;
  description?: string;
  tags?: string[];
  dimensions?: Dimension[];
  status?: string;
}

export interface JobProfileListResponse {
  items: JobProfile[];
  total: number;
  skip: number;
  limit: number;
}

export interface ProfileMatch {
  id: number;
  profile_id: number;
  submission_id: number;
  match_score: number;
  dimension_scores?: Record<string, number>;
  ai_analysis?: string;
  created_at: string;
}

export interface MatchCandidatesRequest {
  min_score?: number;
  limit?: number;
}

export interface MatchCandidatesResponse {
  matches: ProfileMatch[];
  total: number;
}

// ========== API函数 ==========

/**
 * 获取岗位画像列表
 */
export const getJobProfiles = async (params?: {
  skip?: number;
  limit?: number;
  department?: string;
  status?: string;
}): Promise<JobProfileListResponse> => {
  const query = new URLSearchParams();
  if (params?.skip !== undefined) query.append('skip', params.skip.toString());
  if (params?.limit !== undefined) query.append('limit', params.limit.toString());
  if (params?.department) query.append('department', params.department);
  if (params?.status) query.append('status_filter', params.status);  // ⭐ 后端参数名为 status_filter

  const queryString = query.toString();
  return apiRequest({
    path: `/api/job-profiles${queryString ? '?' + queryString : ''}`,
    auth: false,
  });
};

/**
 * 获取单个岗位画像
 */
export const getJobProfile = async (id: number): Promise<JobProfile> => {
  return apiRequest({
    path: `/api/job-profiles/${id}`,
    auth: false,
  });
};

/**
 * 创建岗位画像
 */
export const createJobProfile = async (data: JobProfileCreate): Promise<JobProfile> => {
  return apiRequestWithBody({
    path: '/api/job-profiles',
    method: 'POST',
    body: data,
    auth: false,
  });
};

/**
 * 更新岗位画像
 */
export const updateJobProfile = async (
  id: number,
  data: JobProfileUpdate
): Promise<JobProfile> => {
  return apiRequestWithBody({
    path: `/api/job-profiles/${id}`,
    method: 'PUT',
    body: data,
    auth: false,
  });
};

/**
 * 删除岗位画像
 */
export const deleteJobProfile = async (id: number): Promise<void> => {
  return apiRequestWithBody({
    path: `/api/job-profiles/${id}`,
    method: 'DELETE',
    auth: false,
  });
};

/**
 * 匹配候选人
 */
export const matchCandidates = async (
  profileId: number,
  params?: MatchCandidatesRequest
): Promise<MatchCandidatesResponse> => {
  return apiRequestWithBody({
    path: `/api/job-profiles/${profileId}/match`,
    method: 'POST',
    body: params || {},
    auth: false,
  });
};

/**
 * 获取匹配记录
 */
export const getProfileMatches = async (
  profileId: number,
  params?: {
    min_score?: number;
    limit?: number;
  }
): Promise<MatchCandidatesResponse> => {
  const query = new URLSearchParams();
  if (params?.min_score !== undefined) query.append('min_score', params.min_score.toString());
  if (params?.limit !== undefined) query.append('limit', params.limit.toString());

  const queryString = query.toString();
  return apiRequest({
    path: `/api/job-profiles/${profileId}/matches${queryString ? '?' + queryString : ''}`,
    auth: false,
  });
};

// ========== Phase 5: AI辅助功能 ==========

/**
 * AI分析单份简历生成岗位画像建议
 * @param file 简历文件
 * @param jobTitle 岗位名称
 * @param department 部门名称
 * @returns 岗位画像配置建议
 */
export const analyzeResumeForProfile = async (
  file: File,
  jobTitle: string,
  department?: string
): Promise<JobProfile> => {
  const formData = new FormData();
  formData.append('file', file);
  
  const query = new URLSearchParams();
  query.append('job_title', jobTitle);
  if (department) query.append('department', department);
  
  const response = await fetch(
    `/api/job-profiles/analyze-resume?${query.toString()}`,
    {
      method: 'POST',
      body: formData,
    }
  );
  
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'AI分析失败' }));
    throw new Error(error.detail || 'AI分析失败');
  }
  
  return response.json();
};

/**
 * AI分析多份简历生成岗位画像建议（提取共性特征）
 * @param files 简历文件数组
 * @param jobTitle 岗位名称
 * @param department 部门名称
 * @returns 岗位画像配置建议
 */
export const analyzeMultipleResumesForProfile = async (
  files: File[],
  jobTitle: string,
  department?: string
): Promise<JobProfile> => {
  const formData = new FormData();
  files.forEach((file, index) => {
    formData.append('files', file);
  });
  
  const query = new URLSearchParams();
  query.append('job_title', jobTitle);
  if (department) query.append('department', department);
  
  const response = await fetch(
    `/api/job-profiles/analyze-resumes?${query.toString()}`,
    {
      method: 'POST',
      body: formData,
    }
  );
  
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'AI分析失败' }));
    throw new Error(error.detail || 'AI分析失败');
  }
  
  return response.json();
};

/**
 * AI智能配置能力维度权重
 * @param jobTitle 岗位名称
 * @param description 岗位描述
 * @param existingDimensions 已有的维度（可选）
 * @returns 配置好权重的维度列表
 */
export const aiConfigureDimensions = async (
  jobTitle: string,
  description?: string,
  existingDimensions?: Dimension[]
): Promise<{ dimensions: Dimension[]; analysis: string }> => {
  const response = await fetch('/api/job-profiles/ai-configure-dimensions', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      job_title: jobTitle,
      description: description || '',
      existing_dimensions: existingDimensions || [],
    }),
  });
  
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'AI配置失败' }));
    throw new Error(error.detail || 'AI配置失败');
  }
  
  return response.json();
};

/**
 * AI分析JD生成岗位画像建议
 * @param jdText JD文本
 * @param jobTitle 岗位名称
 * @param department 部门名称
 * @returns 岗位画像配置建议
 */
export const analyzeJDForProfile = async (
  jdText: string,
  jobTitle: string,
  department?: string
): Promise<JobProfile> => {
  // 使用 POST body 传递 JD 文本（JD 文本可能很长，不适合放在 URL 中）
  const query = new URLSearchParams();
  query.append('job_title', jobTitle);
  if (department) query.append('department', department);
  
  const response = await fetch(
    `/api/job-profiles/analyze-jd?${query.toString()}`,
    {
    method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ jd_text: jdText }),
    }
  );
  
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'AI分析失败' }));
    throw new Error(error.detail || 'AI分析失败');
  }
  
  return response.json();
};

