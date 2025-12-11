/**
 * 测评中心 Mock 数据
 */

import type { Questionnaire, Assessment, Submission } from "../assessments";

// Mock 问卷数据
export const MOCK_QUESTIONNAIRES: Questionnaire[] = [
  {
    id: 1,
    name: "MBTI性格测试",
    type: "MBTI",
    questions_count: 93,
    estimated_minutes: 20,
    status: "active",
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  },
  {
    id: 2,
    name: "DISC性格分析",
    type: "DISC",
    questions_count: 28,
    estimated_minutes: 10,
    status: "active",
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  },
  {
    id: 3,
    name: "EPQ人格测评",
    type: "EPQ",
    questions_count: 88,
    estimated_minutes: 15,
    status: "active",
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  },
  {
    id: 4,
    name: "员工满意度调查",
    type: "CUSTOM",
    questions_count: 10,
    estimated_minutes: 10,
    status: "active",
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
    custom_type: "scored",
    scoring_config: {
      enabled: true,
      method: "by_option",
      total_score: 100,
      grades: [
        { name: "A", label: "优秀", min_score: 90, max_score: 100, color: "#3b82f6" },
        { name: "B", label: "良好", min_score: 75, max_score: 89, color: "#f59e0b" },
        { name: "C", label: "合格", min_score: 60, max_score: 74, color: "#6b7280" },
        { name: "D", label: "不合格", min_score: 0, max_score: 59, color: "#ef4444" }
      ]
    }
  },
  {
    id: 5,
    name: "培训反馈问卷",
    type: "CUSTOM",
    questions_count: 8,
    estimated_minutes: 5,
    status: "active",
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
    custom_type: "non_scored",
    scoring_config: { enabled: false }
  },
];

// Mock 测评数据
export const MOCK_ASSESSMENTS: Assessment[] = [
  {
    id: 1,
    name: "MBTI性格测试 - 长期链接",
    code: "ASS_MBTI_001",
    questionnaire_id: 1,
    valid_from: new Date().toISOString(),
    valid_until: new Date(Date.now() + 10 * 365 * 24 * 60 * 60 * 1000).toISOString(), // 10年后
    description: "MBTI性格测试长期有效链接",
    created_at: new Date().toISOString(),
  },
  {
    id: 2,
    name: "DISC性格分析 - 长期链接",
    code: "ASS_DISC_001",
    questionnaire_id: 2,
    valid_from: new Date().toISOString(),
    valid_until: new Date(Date.now() + 10 * 365 * 24 * 60 * 60 * 1000).toISOString(),
    description: "DISC性格分析长期有效链接",
    created_at: new Date().toISOString(),
  },
  {
    id: 3,
    name: "EPQ人格测评 - 长期链接",
    code: "ASS_EPQ_001",
    questionnaire_id: 3,
    valid_from: new Date().toISOString(),
    valid_until: new Date(Date.now() + 10 * 365 * 24 * 60 * 60 * 1000).toISOString(),
    description: "EPQ人格测评长期有效链接",
    created_at: new Date().toISOString(),
  },
  {
    id: 4,
    name: "员工满意度调查 - 长期链接",
    code: "ASS_SURVEY_001",
    questionnaire_id: 4,
    valid_from: new Date().toISOString(),
    valid_until: new Date(Date.now() + 10 * 365 * 24 * 60 * 60 * 1000).toISOString(),
    description: "员工满意度调查长期有效链接",
    created_at: new Date().toISOString(),
  },
  {
    id: 5,
    name: "培训反馈问卷 - 长期链接",
    code: "ASS_FEEDBACK_001",
    questionnaire_id: 5,
    valid_from: new Date().toISOString(),
    valid_until: new Date(Date.now() + 10 * 365 * 24 * 60 * 60 * 1000).toISOString(),
    description: "培训反馈问卷长期有效链接",
    created_at: new Date().toISOString(),
  },
];

// Mock 提交记录数据
// ⚠️ Mock提交数据 - 与数据库保持一致
// 张三=EPQ, 李四=DISC, 王五=MBTI
export const MOCK_SUBMISSIONS: Submission[] = [
  {
    id: 1,
    code: "SUB-ZS-EPQ-2025",
    candidate_name: "张三",
    candidate_phone: "13812345678",
    questionnaire_name: "EPQ人格测评",
    questionnaire_type: "EPQ",
    total_score: 85,
    grade: "A",
    status: "completed",
    started_at: new Date(Date.now() - 2 * 24 * 60 * 60 * 1000).toISOString(),
    submitted_at: new Date(Date.now() - 2 * 24 * 60 * 60 * 1000 + 30 * 60 * 1000).toISOString(),
    result_details: {
      type: "EPQ",
      epq_personality_trait: "外向稳定型",
      epq_description: "性格外向、情绪稳定、善于表达",
      epq_dimensions: {
        E: { value: 85, t_score: 72, level: "高", label: "外向性" },
        N: { value: 45, t_score: 42, level: "低", label: "神经质" },
        P: { value: 68, t_score: 55, level: "中", label: "精神质" },
        L: { value: 82, t_score: 65, level: "高", label: "掩饰性" }
      }
    }
  },
  {
    id: 2,
    code: "SUB-LS-DISC-2025",
    candidate_name: "李四",
    candidate_phone: "13912345678",
    questionnaire_name: "DISC性格分析",
    questionnaire_type: "DISC",
    total_score: 75,
    grade: "B",
    status: "completed",
    started_at: new Date(Date.now() - 1 * 24 * 60 * 60 * 1000).toISOString(),
    submitted_at: new Date(Date.now() - 1 * 24 * 60 * 60 * 1000 + 20 * 60 * 1000).toISOString(),
    result_details: {
      type: "DISC",
      disc_type: "C型",
      disc_description: "谨慎型：严谨认真、注重细节、追求质量",
      disc_dimensions: {
        D: { label: "支配型 (Dominance)", value: 72 },
        I: { label: "影响型 (Influence)", value: 65 },
        S: { label: "稳健型 (Steadiness)", value: 78 },
        C: { label: "谨慎型 (Compliance)", value: 85 }
      }
    }
  },
  {
    id: 3,
    code: "SUB-WW-MBTI-2025",
    candidate_name: "王五",
    candidate_phone: "13712349999",
    questionnaire_name: "MBTI性格测试",
    questionnaire_type: "MBTI",
    total_score: 80,
    grade: "A",
    status: "completed",
    started_at: new Date(Date.now() - 12 * 60 * 60 * 1000).toISOString(),
    submitted_at: new Date(Date.now() - 12 * 60 * 60 * 1000 + 18 * 60 * 1000).toISOString(),
    result_details: {
      type: "MBTI",
      mbti_type: "INTJ",
      mbti_description: "建筑师 - 富有想象力和战略性的思想家",
      mbti_dimensions: {
        EI: { tendency: "I", label: "内向-外向", value: 35 },
        SN: { tendency: "N", label: "直觉-感觉", value: 72 },
        TF: { tendency: "T", label: "思考-情感", value: 80 },
        JP: { tendency: "J", label: "判断-知觉", value: 65 }
      }
    }
  },
  // ❌ 已删除赵六（id=4）- 只保留3个候选人对应EPQ/DISC/MBTI测评
  {
    id: 5,
    code: "SUB005",
    candidate_name: "钱七",
    candidate_phone: "13800138005",
    questionnaire_name: "培训反馈问卷",
    questionnaire_type: "CUSTOM",
    total_score: null,
    max_score: null,
    score_percentage: null,
    grade: null,
    status: "completed",
    started_at: new Date(Date.now() - 3 * 60 * 60 * 1000).toISOString(),
    submitted_at: new Date(Date.now() - 3 * 60 * 60 * 1000 + 10 * 60 * 1000).toISOString(),
    result_details: {
      custom_type: "non_scored",
      answers: [
        {
          question_id: "q1",
          question_title: "您参加的是哪个培训课程？",
          question_type: "single_choice",
          answer: { value: "产品设计培训" },
          scoring: null
        },
        {
          question_id: "q2",
          question_title: "培训时间是否合适？",
          question_type: "yes_no",
          answer: { boolean: true },
          scoring: null
        },
        {
          question_id: "q3",
          question_title: "您对培训内容的满意度？",
          question_type: "scale",
          answer: { value: 8 },
          scoring: null
        },
        {
          question_id: "q4",
          question_title: "您对讲师的满意度？",
          question_type: "scale",
          answer: { value: 9 },
          scoring: null
        },
        {
          question_id: "q5",
          question_title: "您觉得培训最有价值的部分是？（可多选）",
          question_type: "multiple_choice",
          answer: { values: ["案例分析", "实战演练", "互动讨论"] },
          scoring: null
        },
        {
          question_id: "q6",
          question_title: "您对培训的建议？",
          question_type: "long_text",
          answer: { value: "培训内容很实用，案例也很贴近实际工作。建议增加更多实战演练的环节，让大家有更多动手实践的机会。" },
          scoring: null
        },
        {
          question_id: "q7",
          question_title: "您希望参加后续的培训吗？",
          question_type: "yes_no",
          answer: { boolean: true },
          scoring: null
        },
        {
          question_id: "q8",
          question_title: "您的联系邮箱？",
          question_type: "short_text",
          answer: { value: "qianqi@example.com" },
          scoring: null
        }
      ]
    }
  },
];

