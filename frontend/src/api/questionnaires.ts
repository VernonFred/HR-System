import { apiRequest } from "./client";
import { MOCK_QUESTIONNAIRES, MOCK_QUESTIONS } from "./mocks/questionnaires";
import type { Question, Questionnaire } from "../types/questionnaire";

export async function fetchQuestionnaires(): Promise<Questionnaire[]> {
  return apiRequest<Questionnaire[]>({
    path: "/questionnaires",
    fallback: MOCK_QUESTIONNAIRES,
  });
}

export async function fetchQuestionnaire(code: string): Promise<Questionnaire> {
  const mock = MOCK_QUESTIONNAIRES.find((q) => q.code === code);
  return apiRequest<Questionnaire>({
    path: `/questionnaires/${code}`,
    fallback: mock,
  });
}

export async function fetchQuestions(code: string): Promise<Question[]> {
  const mock = MOCK_QUESTIONS[code] || [];
  return apiRequest<Question[]>({
    path: `/questionnaires/${code}/questions`,
    fallback: mock,
  });
}
