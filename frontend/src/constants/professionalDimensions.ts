/**
 * 专业测评维度配置
 * 定义 EPQ、DISC、MBTI 等测评的维度信息
 */

export interface DimensionOption {
  key: string;
  label: string;
}

export const professionalDimensions: Record<string, DimensionOption[]> = {
  EPQ: [
    { key: 'E', label: 'E - 外向性' },
    { key: 'N', label: 'N - 神经质' },
    { key: 'P', label: 'P - 精神质' },
    { key: 'L', label: 'L - 掩饰性' },
  ],
  DISC: [
    { key: 'D', label: 'D - 支配型' },
    { key: 'I', label: 'I - 影响型' },
    { key: 'S', label: 'S - 稳健型' },
    { key: 'C', label: 'C - 谨慎型' },
  ],
  MBTI: [
    { key: 'EI', label: 'EI - 外向/内向' },
    { key: 'SN', label: 'SN - 实感/直觉' },
    { key: 'TF', label: 'TF - 思考/情感' },
    { key: 'JP', label: 'JP - 判断/知觉' },
  ],
};

/**
 * 专业测评类型列表
 */
export const professionalTypes = ['EPQ', 'DISC', 'MBTI'] as const;
export type ProfessionalType = typeof professionalTypes[number];

/**
 * 判断是否为专业测评类型
 */
export const isProfessionalType = (type: string): type is ProfessionalType => {
  return professionalTypes.includes(type as ProfessionalType);
};

export default professionalDimensions;

