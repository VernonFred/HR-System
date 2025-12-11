import { apiRequestWithBody } from "../api/client";
import { useAuthStore } from "../stores/auth";

type AICommonPayload = Record<string, unknown>;

export async function getInterpretation(data: AICommonPayload) {
  const token = useAuthStore().token;
  return apiRequestWithBody({
    path: "/ai/interpretation",
    method: "POST",
    body: data,
    auth: true, // 启用认证
    token,
  }).catch((err) => {
    console.warn("AI interpretation failed", err);
    return {
      dimensions: [],
      strengths: [],
      risks: [],
      summary: "AI 暂不可用",
    };
  });
}

export async function getMatch(data: AICommonPayload) {
  const token = useAuthStore().token;
  return apiRequestWithBody({
    path: "/ai/match",
    method: "POST",
    body: data,
    auth: true, // 启用认证
    token,
  }).catch((err) => {
    console.warn("AI match failed", err);
    return {
      match_analysis: [],
      risks: [],
      follow_up_questions: [],
    };
  });
}

export async function getReport(data: AICommonPayload) {
  const token = useAuthStore().token;
  return apiRequestWithBody({
    path: "/ai/report",
    method: "POST",
    body: data,
    auth: true,
    token,
  }).catch((err) => {
    console.warn("AI report failed", err);
    return {
      markdown: "AI 暂不可用",
    };
  });
}
