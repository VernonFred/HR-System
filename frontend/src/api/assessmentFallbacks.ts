/**
 * 公开答题流程 Mock/fallback 题目生成工具。
 */
import { PRESET_QUESTIONS } from "../data/preset-questions";

export interface FallbackQuestionnaireLike {
  name?: string;
  type?: string | null;
}

// ⭐ 根据问卷类型字符串获取题目列表
export function getQuestionsForQuestionnaireType(typeStr: string | null | undefined): any[] {
  if (!typeStr) return [];

  const type = typeStr.toUpperCase();

  // 专业测评使用预设题目
  if (type === 'EPQ') {
    return PRESET_QUESTIONS.EPQ.map(q => ({
      id: q.id,
      type: q.type,
      text: q.text,
      required: q.required,
      dimension: q.dimension,
      positive: q.positive,
      options: q.type === 'yesno' ? [
        { label: '是', text: '是', value: 'yes' },
        { label: '否', text: '否', value: 'no' }
      ] : q.options?.map(o => ({ label: o.value, text: o.label, value: o.value }))
    }));
  }

  if (type === 'DISC') {
    return PRESET_QUESTIONS.DISC.map(q => ({
      id: q.id,
      type: q.type,
      text: q.text,
      required: q.required,
      dimension: q.dimension,
      options: q.options?.map(o => ({ label: o.value, text: o.label, value: o.value }))
    }));
  }

  if (type === 'MBTI') {
    return PRESET_QUESTIONS.MBTI.map(q => ({
      id: q.id,
      type: q.type,
      text: q.text,
      required: q.required,
      dimension: q.dimension,
      optionA: q.optionA,
      optionB: q.optionB,
      options: q.type === 'choice' ? [
        { label: 'A', text: q.optionA, value: 'A' },
        { label: 'B', text: q.optionB, value: 'B' }
      ] : undefined
    }));
  }

  // 自定义问卷返回示例题目
  return [
    { id: '1', type: 'radio', text: '示例题目1', required: true, options: [
      { label: 'A', text: '选项A', value: 'A' },
      { label: 'B', text: '选项B', value: 'B' },
      { label: 'C', text: '选项C', value: 'C' }
    ]},
    { id: '2', type: 'radio', text: '示例题目2', required: true, options: [
      { label: 'A', text: '选项A', value: 'A' },
      { label: 'B', text: '选项B', value: 'B' },
      { label: 'C', text: '选项C', value: 'C' }
    ]}
  ];
}

// ⭐ 根据问卷对象获取题目列表（保留旧函数以兼容）
export function getQuestionsForQuestionnaire(questionnaire: Questionnaire | null | undefined): any[] {
  if (!questionnaire) return [];

  const type = questionnaire.type?.toUpperCase();

  // 专业测评使用预设题目
  if (type === 'EPQ') {
    return PRESET_QUESTIONS.EPQ.map(q => ({
      id: q.id,
      type: q.type,
      text: q.text,
      required: q.required,
      dimension: q.dimension,
      positive: q.positive,
      options: q.type === 'yesno' ? [
        { label: '是', text: '是', value: 'yes' },
        { label: '否', text: '否', value: 'no' }
      ] : q.options?.map(o => ({ label: o.value, text: o.label, value: o.value }))
    }));
  }

  if (type === 'DISC') {
    return PRESET_QUESTIONS.DISC.map(q => ({
      id: q.id,
      type: q.type,
      text: q.text,
      required: q.required,
      dimension: q.dimension,
      options: q.options?.map(o => ({ label: o.value, text: o.label, value: o.value }))
    }));
  }

  if (type === 'MBTI') {
    return PRESET_QUESTIONS.MBTI.map(q => ({
      id: q.id,
      type: q.type,
      text: q.text,
      required: q.required,
      dimension: q.dimension,
      optionA: q.optionA,
      optionB: q.optionB,
      options: q.type === 'choice' ? [
        { label: 'A', text: q.optionA, value: 'A' },
        { label: 'B', text: q.optionB, value: 'B' }
      ] : undefined
    }));
  }

  // 自定义问卷返回示例题目
  return [
    { id: '1', type: 'radio', text: `${questionnaire.name} - 示例题目1`, required: true, options: [
      { label: 'A', text: '选项A', value: 'A' },
      { label: 'B', text: '选项B', value: 'B' },
      { label: 'C', text: '选项C', value: 'C' }
    ]},
    { id: '2', type: 'radio', text: `${questionnaire.name} - 示例题目2`, required: true, options: [
      { label: 'A', text: '选项A', value: 'A' },
      { label: 'B', text: '选项B', value: 'B' },
      { label: 'C', text: '选项C', value: 'C' }
    ]}
  ];
}
