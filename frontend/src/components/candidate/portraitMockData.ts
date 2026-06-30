import type { CandidateProfile } from '../../types/candidate';

export const mockCandidateProfile: CandidateProfile = {
  id: '1',
  name: '张三',
  appliedPosition: '产品经理',
  updatedAt: '2025-11-29',
  overallMatchScore: 86,
  tags: ['结构化思维', '跨部门协作', '产品规划'],
  personalityDimensions: [
    { key: 'extraversion', label: '外向性 E', score: 88 },
    { key: 'emotionalStability', label: '情绪稳定性 N', score: 66 },
    { key: 'openness', label: '精神质 P', score: 75 },
    { key: 'conscientiousness', label: '掩饰性 L', score: 80 },
  ],
  competencies: [
    { key: 'planning', label: '产品规划能力', score: 82 },
    { key: 'insight', label: '用户洞察力', score: 82 },
    { key: 'communication', label: '跨部门沟通', score: 78 },
    { key: 'negotiation', label: '谈判沟通力', score: 74 },
    { key: 'analysis', label: '洞察力', score: 80 },
    { key: 'data', label: '数据敏感度', score: 78 },
    { key: 'organization', label: '组织能力', score: 75 },
    { key: 'decision', label: '决策能力', score: 70 },
  ],
  aiAnalysisText:
    '候选人在结构化分析和规划能力上表现突出，画像风格能够带给团队积极影响，可在不确定场景下保持良好的判断力，适合承担相对重要和复杂的项目管理。',
  highlights: ['结构化分析能力强', '规划视野成熟', '善于跨部门协调'],
  risks: ['高压多任务下可能焦虑', '对低效流程容忍度低'],
  suitablePositions: ['ToB 产品经理', '产品策略', '用户增长产品', '跨部门项目负责人'],
  unsuitablePositions: ['高度重复事务岗', '纯情绪劳动岗位', '纯销售类岗位'],
  developmentSuggestions: ['强化情绪管理技巧', '培养同理心沟通', '提升团队协作意识'],
  interviewFocus: ['如何处理多任务压力', '团队协作具体案例', '失败经历与反思'],
};
