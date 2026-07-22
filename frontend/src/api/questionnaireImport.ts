/**
 * 问卷文件导入 API。
 */
import type { QuestionnaireImportResponse } from './assessmentTypes';
import { authenticatedFetch } from './client';

// ========== V43: 问卷导入 ==========


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

  const response = await authenticatedFetch(url, {
    method: 'POST',
    body: formData,
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: '导入失败' }));
    throw new Error(error.detail || '导入失败');
  }

  return response.json();
};
