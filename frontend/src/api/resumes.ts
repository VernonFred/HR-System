/**
 * 简历管理 API
 */
import { authenticatedFetch } from './client';

// 生产环境使用相对路径（nginx代理），开发环境可通过环境变量配置
const API_BASE = import.meta.env.VITE_API_BASE || '';

// 上传单个简历
export async function uploadResume(candidateId: number, file: File) {
  const formData = new FormData();
  formData.append('file', file);
  
  const response = await authenticatedFetch(
    `${API_BASE}/api/resumes/candidates/${candidateId}/upload`,
    { method: 'POST', body: formData }
  );
  return parseJsonResponse(response);
}

// 批量上传简历
export async function batchUploadResumes(files: File[], candidateIds: number[]) {
  const formData = new FormData();
  
  files.forEach(file => {
    formData.append('files', file);
  });
  formData.append('candidate_ids', candidateIds.join(','));
  
  const response = await authenticatedFetch(
    `${API_BASE}/api/resumes/batch-upload`,
    { method: 'POST', body: formData }
  );
  return parseJsonResponse(response);
}

// 获取简历信息
export async function getResumeInfo(candidateId: number) {
  const response = await authenticatedFetch(
    `${API_BASE}/api/resumes/candidates/${candidateId}`
  );
  return parseJsonResponse(response);
}

// 下载简历文件，避免在 URL 中暴露访问凭据。
export async function downloadResume(candidateId: number): Promise<Blob> {
  const response = await authenticatedFetch(
    `${API_BASE}/api/resumes/candidates/${candidateId}/download`
  );
  if (!response.ok) {
    throw await buildResponseError(response);
  }
  return response.blob();
}

// 删除简历
export async function deleteResume(candidateId: number) {
  const response = await authenticatedFetch(
    `${API_BASE}/api/resumes/candidates/${candidateId}`,
    { method: 'DELETE' }
  );
  return parseJsonResponse(response);
}

// 手动触发解析。analysis_level 保留旧接口兼容，画像生成统一按 pro 单模型处理。
export type AnalysisLevel = 'pro' | 'expert';

export async function parseResume(
  candidateId: number, 
  analysisLevel: AnalysisLevel = 'pro'
) {
  const response = await authenticatedFetch(
    `${API_BASE}/api/resumes/candidates/${candidateId}/parse?analysis_level=${analysisLevel}`,
    { method: 'POST' }
  );
  return parseJsonResponse(response);
}

async function parseJsonResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    throw await buildResponseError(response);
  }
  return response.json() as Promise<T>;
}

async function buildResponseError(response: Response): Promise<Error> {
  const payload = await response.json().catch(() => null);
  const message = payload?.detail || `请求失败 (${response.status})`;
  const error = new Error(message) as Error & { response?: { data: unknown } };
  error.response = { data: payload };
  return error;
}
