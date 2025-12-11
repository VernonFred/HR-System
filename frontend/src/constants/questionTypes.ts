/**
 * 问卷题目类型定义
 * 定义问卷编辑器中使用的类型接口
 */

/**
 * 题目选项
 */
export interface QuestionOption {
  value: string;
  label: string;
  score?: number;
}

/**
 * 题目类型枚举
 */
export type QuestionType = 'radio' | 'checkbox' | 'text' | 'textarea' | 'scale' | 'yesno' | 'choice';

/**
 * 编辑器中的题目数据结构
 */
export interface EditorQuestion {
  id: string;
  order: number;
  type: QuestionType;
  text: string;
  required: boolean;
  options?: QuestionOption[];
  scale?: {
    min: number;
    max: number;
    minLabel?: string;
    maxLabel?: string;
    scorePerPoint?: number;  // 每级分值（评分问卷使用）
  };
  optionA?: string;  // 用于choice类型
  optionB?: string;  // 用于choice类型
  dimension?: string;  // 专业测评维度 (MBTI: EI/SN/TF/JP, DISC: D/I/S/C, EPQ: E/N/P/L)
  positive?: boolean;  // EPQ题目是否正向计分
}

/**
 * 等级配置
 */
export interface GradeConfig {
  grade: string;
  minScore: number;
  maxScore: number;
  label: string;
}

/**
 * 问卷用途类型
 */
export type QuestionnairePurpose = 'survey' | 'assessment';

/**
 * 评分类型
 */
export type ScoringType = 'simple' | 'dimension';

/**
 * 简单计分配置
 */
export interface SimpleScoring {
  enabled: boolean;
  totalScore: number;  // 满分
  passingScore: number;  // 及格分
}

/**
 * 默认等级配置
 */
export const defaultGradeConfig: GradeConfig[] = [
  { grade: "A", minScore: 90, maxScore: 100, label: "优秀" },
  { grade: "B", minScore: 75, maxScore: 89, label: "良好" },
  { grade: "C", minScore: 60, maxScore: 74, label: "合格" },
  { grade: "D", minScore: 0, maxScore: 59, label: "不合格" },
];

/**
 * 默认简单计分配置
 */
export const defaultSimpleScoring: SimpleScoring = {
  enabled: true,
  totalScore: 100,
  passingScore: 60,
};

