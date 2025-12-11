/**
 * 简历管理 API
 */
import axios from 'axios';

const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:9000';

// 上传单个简历
export async function uploadResume(candidateId: number, file: File) {
  const formData = new FormData();
  formData.append('file', file);
  
  const response = await axios.post(
    `${API_BASE}/api/resumes/candidates/${candidateId}/upload`,
    formData,
    {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    }
  );
  
  return response.data;
}

// 批量上传简历
export async function batchUploadResumes(files: File[], candidateIds: number[]) {
  const formData = new FormData();
  
  files.forEach(file => {
    formData.append('files', file);
  });
  formData.append('candidate_ids', candidateIds.join(','));
  
  const response = await axios.post(
    `${API_BASE}/api/resumes/batch-upload`,
    formData,
    {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    }
  );
  
  return response.data;
}

// 获取简历信息
export async function getResumeInfo(candidateId: number) {
  const response = await axios.get(
    `${API_BASE}/api/resumes/candidates/${candidateId}`
  );
  return response.data;
}

// 下载简历
export function getResumeDownloadUrl(candidateId: number): string {
  return `${API_BASE}/api/resumes/candidates/${candidateId}/download`;
}

// 删除简历
export async function deleteResume(candidateId: number) {
  const response = await axios.delete(
    `${API_BASE}/api/resumes/candidates/${candidateId}`
  );
  return response.data;
}

// 手动触发解析（支持分析级别）
export type AnalysisLevel = 'pro' | 'expert';

export async function parseResume(
  candidateId: number, 
  analysisLevel: AnalysisLevel = 'pro'
) {
  const response = await axios.post(
    `${API_BASE}/api/resumes/candidates/${candidateId}/parse?analysis_level=${analysisLevel}`
  );
  return response.data;
}

