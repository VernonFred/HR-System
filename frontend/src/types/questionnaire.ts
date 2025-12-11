export type Questionnaire = {
  id: number;
  code: string;
  name: string;
  full_name?: string | null;
  description?: string | null;
  dimensions?: string[] | null;
  dimension_names?: Record<string, string> | null;
  dimension_descriptions?: Record<string, string> | null;
  answer_type?: string | null;
  question_count?: number | null;
  estimated_time?: number | null;
  extra?: Record<string, unknown> | null;
};

export type Question = {
  id: number;
  questionnaire_id: number;
  order: number;
  text: string;
  dimension?: string | null;
  answer_type?: string | null;
  payload?: Record<string, unknown> | null;
  positive?: boolean | null;
};
