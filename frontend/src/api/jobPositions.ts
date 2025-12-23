/**
 * 岗位画像管理 - API客户端
 */

// 生产环境使用相对路径（nginx代理），开发环境使用环境变量或空字符串
const BASE_URL = import.meta.env.VITE_API_BASE || '';

export interface JobPosition {
  id: number;
  name: string;
  department?: string;
  level?: string;
  description?: string;
  status: 'active' | 'inactive';
  created_at?: string;
  updated_at?: string;
}

export interface JobPositionCreate {
  name: string;
  department?: string;
  level?: string;
  description?: string;
  status?: 'active' | 'inactive';
}

export interface JobPositionUpdate {
  name?: string;
  department?: string;
  level?: string;
  description?: string;
  status?: 'active' | 'inactive';
}

export interface JobProfile {
  id: number;
  job_position_id: number;
  name: string;
  requirement_text?: string;
  ai_analysis?: any;
  dimensions: DimensionWeight[];
  created_at: string;
  updated_at: string;
}

export interface DimensionWeight {
  id?: number;
  dimension_code: string;
  dimension_name: string;
  weight: number;
  ideal_score?: number;
  min_score?: number;
  description?: string;
}

export interface RequirementAnalysis {
  key_abilities: Array<{ name: string; importance: string }>;
  personality_preferences: string[];
  experience_requirements?: string;
  education_requirements?: string;
  summary: string;
}

export interface DimensionSuggestion {
  dimensions: DimensionWeight[];
  explanation: string;
}

/**
 * 获取岗位列表
 */
export async function getJobPositions(): Promise<{ items: JobPosition[]; total: number }> {
  const response = await fetch(`${BASE_URL}/api/job-positions`);
  if (!response.ok) {
    throw new Error('获取岗位列表失败');
  }
  return response.json();
}

/**
 * 获取岗位详情（包含画像）
 */
export async function getJobPosition(jobId: number): Promise<JobPosition & { profiles: JobProfile[] }> {
  const response = await fetch(`${BASE_URL}/api/job-positions/${jobId}`);
  if (!response.ok) {
    throw new Error('获取岗位详情失败');
  }
  return response.json();
}

/**
 * 创建岗位
 */
export async function createJobPosition(data: JobPositionCreate): Promise<JobPosition> {
  const response = await fetch(`${BASE_URL}/api/job-positions`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  if (!response.ok) {
    throw new Error('创建岗位失败');
  }
  return response.json();
}

/**
 * 更新岗位
 */
export async function updateJobPosition(jobId: number, data: JobPositionUpdate): Promise<JobPosition> {
  const response = await fetch(`${BASE_URL}/api/job-positions/${jobId}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  if (!response.ok) {
    throw new Error('更新岗位失败');
  }
  return response.json();
}

/**
 * 删除岗位
 */
export async function deleteJobPosition(jobId: number): Promise<void> {
  const response = await fetch(`${BASE_URL}/api/job-positions/${jobId}`, {
    method: 'DELETE',
  });
  if (!response.ok) {
    throw new Error('删除岗位失败');
  }
}

/**
 * AI分析岗位需求文案
 */
export async function analyzeRequirement(requirementText: string): Promise<RequirementAnalysis> {
  const response = await fetch(`${BASE_URL}/api/job-positions/analyze-requirement`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ requirement_text: requirementText }),
  });
  if (!response.ok) {
    throw new Error('分析需求失败');
  }
  return response.json();
}

/**
 * AI建议维度权重配置
 */
export async function suggestDimensions(
  jobId: number, 
  requirementAnalysis?: any
): Promise<DimensionSuggestion> {
  const response = await fetch(`${BASE_URL}/api/job-positions/${jobId}/suggest-dimensions`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      job_position_id: jobId,
      requirement_analysis: requirementAnalysis,
    }),
  });
  if (!response.ok) {
    throw new Error('获取AI建议失败');
  }
  return response.json();
}

/**
 * 创建岗位画像
 */
export async function createJobProfile(data: {
  job_position_id: number;
  name: string;
  requirement_text?: string;
  dimensions?: DimensionWeight[];
}): Promise<JobProfile> {
  const response = await fetch(`${BASE_URL}/api/job-positions/profiles`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  if (!response.ok) {
    throw new Error('创建岗位画像失败');
  }
  return response.json();
}

/**
 * 更新岗位画像维度权重
 */
export async function updateDimensionWeights(
  profileId: number,
  dimensions: DimensionWeight[]
): Promise<DimensionWeight[]> {
  const response = await fetch(`${BASE_URL}/api/job-positions/profiles/${profileId}/dimensions`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(dimensions),
  });
  if (!response.ok) {
    throw new Error('更新维度权重失败');
  }
  return response.json();
}

/**
 * 上传JD文件并AI解析
 */
export async function uploadAndParseJD(file: File): Promise<{
  success: boolean;
  jd_text: string;
  parsed_data: {
    name: string;
    department?: string;
    level?: string;
    description: string;
    key_abilities: Array<{ name: string; importance: string }>;
    personality_preferences: string[];
    experience_requirements?: string;
    education_requirements?: string;
  };
}> {
  const formData = new FormData();
  formData.append('file', file);
  
  const response = await fetch(`${BASE_URL}/api/job-positions/upload-jd`, {
    method: 'POST',
    body: formData,
  });
  
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: '上传失败' }));
    throw new Error(error.detail || '上传JD失败');
  }
  
  return response.json();
}

