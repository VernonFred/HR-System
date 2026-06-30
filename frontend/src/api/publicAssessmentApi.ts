/**
 * 候选人端公开答题 API。
 */
import { apiRequest, apiRequestWithBody } from './client';
import { MOCK_ASSESSMENTS, MOCK_QUESTIONNAIRES, MOCK_SUBMISSIONS } from './mocks/assessments';
import { getQuestionsForQuestionnaireType } from './assessmentFallbacks';
import type { PublicAssessmentInfo, PublicSubmissionStart, SubmitCheckResult, Submission, SubmissionStart } from './assessmentTypes';

// ========== 公开API（候选人端） ==========



// ⭐ 重复提交检测结果

// 检查是否可以提交
export const checkCanSubmit = (code: string, phone: string, name: string = "", anonymousDeviceId?: string) => {
  return apiRequestWithBody<SubmitCheckResult>({
    path: `/api/public/assessment/${code}/check-submit`,
    method: "POST",
    body: { phone, name, anonymous_device_id: anonymousDeviceId },
    fallback: { can_submit: true, reason: "", submission_number: 1, previous_submissions: [] },
    auth: false,
  });
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
    category: questionnaire.category,
    custom_type: questionnaire.custom_type,
    purpose: questionnaire.purpose,
    questions_count: questionnaire.questions_count,
    estimated_minutes: questionnaire.estimated_minutes,
    valid: now >= validFrom && now <= validUntil,
    expired: now > validUntil,
    description: assessment.description || questionnaire.name,
    anonymous_mode: assessment.anonymous_mode || false,
    form_fields: [
      { id: 1, name: 'candidate_name', label: '姓名', type: 'text', enabled: true, required: true, builtin: true },
      { id: 2, name: 'candidate_phone', label: '手机号', type: 'text', enabled: true, required: true, builtin: true }
    ],
    page_texts: {
      intro_text: '请认真填写以下信息',
      privacy_text: '我们将严格保护您的隐私',
      success_title: '提交成功',
      success_message: '感谢您的参与！',
      success_tips: '我们会尽快处理您的提交结果'
    }
  } : {
    name: '未找到链接',
    type: 'UNKNOWN',
    questions_count: 0,
    estimated_minutes: 0,
    valid: false,
    expired: false,
    description: '链接不存在'
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
  return apiRequestWithBody<PublicSubmissionStart>({
    path: `/api/public/assessment/${code}/start`,
    method: "POST",
    body: { ...data, assessment_code: code },
    // 不提供fallback，确保API失败时抛出错误
    auth: false,
  });
};


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
