import type { Question, Questionnaire } from "../../types/questionnaire";

export const MOCK_QUESTIONNAIRES: Questionnaire[] = [
  {
    id: 1,
    code: "epq",
    name: "EPQ 人格测评",
    full_name: "艾森克人格问卷",
    description: "模拟数据：测量外向性、神经质、精神质和掩饰性四个维度。",
    dimensions: ["E", "N", "P", "L"],
    dimension_names: { E: "外向", N: "神经", P: "精神", L: "掩饰" },
    question_count: 2,
    estimated_time: 1,
  },
  {
    id: 2,
    code: "mbti",
    name: "MBTI 职业性格",
    full_name: "迈尔斯-布里格斯类型指标",
    description: "模拟数据：四个维度组合成 16 种类型。",
    dimensions: ["EI", "SN", "TF", "JP"],
    question_count: 2,
    estimated_time: 1,
  },
];

export const MOCK_QUESTIONS: Record<string, Question[]> = {
  epq: [
    {
      id: 1,
      questionnaire_id: 1,
      order: 1,
      text: "你是否喜欢周围热闹？",
      dimension: "E",
      answer_type: "yesno",
      payload: { positive: true },
      positive: true,
    },
    {
      id: 2,
      questionnaire_id: 1,
      order: 2,
      text: "你是否经常感到紧张？",
      dimension: "N",
      answer_type: "yesno",
      payload: { positive: true },
      positive: true,
    },
  ],
  mbti: [
    {
      id: 3,
      questionnaire_id: 2,
      order: 1,
      text: "在聚会上，你通常：",
      dimension: "EI",
      answer_type: "choice",
      payload: { optionA: "与很多人交流", optionB: "只与熟人交流", scoreA: "E", scoreB: "I" },
    },
    {
      id: 4,
      questionnaire_id: 2,
      order: 2,
      text: "你更喜欢：",
      dimension: "SN",
      answer_type: "choice",
      payload: { optionA: "具体事实", optionB: "抽象概念", scoreA: "S", scoreB: "N" },
    },
  ],
};
