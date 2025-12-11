import type { SubmissionRequest, SubmissionResponse } from "../../types/submission";

export const MOCK_SUBMISSION_RESULT: SubmissionResponse = {
  submissionId: "mock-123",
  questionnaireCode: "epq",
  scores: [
    { dimension: "E", score: 16 },
    { dimension: "N", score: 8 },
    { dimension: "P", score: 10 },
    { dimension: "L", score: 14 },
  ],
  totalScore: 48,
  summary: "模拟提交结果：外向性较高，情绪稳定性中等。",
};

export function mockSubmit(_payload: SubmissionRequest): Promise<SubmissionResponse> {
  return Promise.resolve(MOCK_SUBMISSION_RESULT);
}
