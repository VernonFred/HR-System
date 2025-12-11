export type SubmissionAnswer = {
  questionId: number;
  value: string | number | boolean;
};

export type SubmissionRequest = {
  questionnaireCode: string;
  answers: SubmissionAnswer[];
};

export type DimensionScore = {
  dimension: string;
  score: number;
  grade?: string;
  grade_label?: string;
};

export type SubmissionResponse = {
  submissionId: string;
  questionnaireCode: string;
  scores: DimensionScore[];
  totalScore: number;
  summary?: string;
};
