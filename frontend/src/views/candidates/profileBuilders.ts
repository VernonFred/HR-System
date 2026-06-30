import type { Candidate, CandidateProfile } from "../../types/candidate";

// 问卷类型检测函数
export const detectQuestionnaireType = (name: string): 'MBTI' | 'EPQ' | 'DISC' => {
  const upperName = (name || '').toUpperCase();
  if (upperName.includes('MBTI')) return 'MBTI';
  if (upperName.includes('DISC')) return 'DISC';
  if (upperName.includes('EPQ') || upperName.includes('艾森克')) return 'EPQ';
  // 默认返回EPQ
  return 'EPQ';
};

// ⭐ Phase 4: 将真实画像API数据转换为前端展示格式
export const convertRealPortraitToProfile = (portrait: any): CandidateProfile => {
  console.log('🔄 转换真实画像数据:', portrait);

  // 转换人格维度数据 - 直接使用后端返回的label，不再拼接key（后端已包含）
  const personalityDims = (portrait.personality_dimensions || []).map((d: any) => ({
    key: d.key,
    label: d.label,  // 后端已返回完整格式如 "外向性 E"
    score: d.score,
    description: d.description
  }));

  // 转换岗位胜任力数据 - 优先使用portrait.competencies（新字段），否则用job_match.dimension_scores
  const competencies = (portrait.competencies || portrait.job_match?.dimension_scores || []).map((d: any) => ({
    key: d.key || d.name,
    label: d.label || d.name,
    score: d.score,
    description: d.rationale || d.description
  }));

  console.log('  → 胜任力数据:', competencies);

  // 转换测评记录数据
  const assessments = (portrait.assessments || []).map((a: any) => ({
    submission_id: a.submission_id,
    assessment_name: a.assessment_name,
    questionnaire_name: a.questionnaire_name,
    questionnaire_type: a.questionnaire_type || detectQuestionnaireType(a.questionnaire_name),  // 优先使用后端返回的类型
    total_score: a.total_score,
    max_score: a.max_score,
    score_percentage: a.score_percentage,
    grade: a.grade,
    completed_at: a.completed_at,
    personality_dimensions: a.personality_dimensions || [],  // 添加该测评的维度数据
  }));

  // 优先使用 quick_tags，否则从 strengths 中提取短标签
  const tags = portrait.quick_tags?.length > 0
    ? portrait.quick_tags
    : (portrait.strengths || []).slice(0, 3).map((s: string) => {
        // 从优势亮点中提取关键词（去掉冒号后的内容）
        const tag = s.includes('：') ? s.split('：')[0] : (s.includes(':') ? s.split(':')[0] : s);
        return tag.trim().slice(0, 6);  // 最多6个字
      });

  return {
    id: String(portrait.basic_info.id),
    name: portrait.basic_info.name,
    appliedPosition: portrait.basic_info.target_position || '未知岗位',
    level: portrait.assessments?.[0]?.grade || "待评估",
    updatedAt: new Date(portrait.generated_at).toLocaleDateString('zh-CN'),
    overallMatchScore: portrait.overall_score || 0,
    tags: tags,  // 使用 quick_tags 或从 strengths 提取的短标签
    questionnaireType: detectQuestionnaireType(portrait.assessments?.length > 0 ? portrait.assessments[0].questionnaire_name : 'EPQ'),
    personalityDimensions: personalityDims,
    competencies: competencies,
    // 正确映射到类型定义的字段名
    highlights: portrait.strengths || [],  // 优势亮点
    risks: portrait.improvements || [],    // 潜在风险
    // 使用3条摘要点，如果没有则fallback到完整summary
    aiAnalysisText: portrait.ai_summary_points?.length > 0
      ? portrait.ai_summary_points
      : (portrait.ai_summary || `综合得分：${portrait.overall_score?.toFixed(1) || 'N/A'}分`),
    suitablePositions: portrait.suitable_positions || [],
    unsuitablePositions: portrait.unsuitable_positions || [],
    assessments: assessments,  // ⭐ 新增：测评记录列表
    // 🟢 P1-1: 交叉验证数据
    crossValidation: portrait.cross_validation ? {
      consistency_score: portrait.cross_validation.consistency_score,
      confidence_level: portrait.cross_validation.confidence_level,
      assessment_count: portrait.cross_validation.assessment_count,
      consistency_checks: portrait.cross_validation.consistency_checks || [],
      contradictions: portrait.cross_validation.contradictions || []
    } : undefined,
    // 🟢 P1-1: 测评信息列表（用于交叉验证显示）
    assessmentInfoList: (portrait.assessments || []).map((a: any) => ({
      type: a.questionnaire_type || 'UNKNOWN',
      weight: a.questionnaire_type === 'MBTI' ? 40 : (a.questionnaire_type === 'DISC' ? 30 : 30)
    })),
    // 🟢 P0: 评分详情
    scoreBreakdown: {
      assessment: 80,  // TODO: 从后端获取
      match: 85,
      completeness: 90,
      resume: portrait.basic_info.resume ? 70 : 0
    },
    // 🟢 P1-2: 降级标识
    isFallbackAnalysis: portrait.is_fallback_analysis || false,
    analysisMethod: portrait.analysis_method || 'ai',
    fallbackReason: portrait.fallback_reason
  };
};

// ⭐ Phase 4: 将Mock画像数据转换为前端展示格式
export const convertMockPortraitToProfile = (mockPortrait: any): CandidateProfile => {
  return {
    id: String(mockPortrait.basic_info.id),
    name: mockPortrait.basic_info.name,
    appliedPosition: mockPortrait.basic_info.target_position || '未知岗位',
    level: "P6",  // Mock数据默认级别
    updatedAt: new Date(mockPortrait.generated_at).toLocaleDateString('zh-CN'),
    overallMatchScore: mockPortrait.overall_score || 0,
    tags: mockPortrait.strengths.slice(0, 3) || [],
    questionnaireType: 'EPQ',
    personalityDimensions: [
      { key: "E", label: "外向性 E", score: 85 },
      { key: "N", label: "神经质 N", score: 45 },
      { key: "P", label: "精神质 P", score: 68 },
      { key: "L", label: "掩饰性 L", score: 82 },
    ],
    competencies: mockPortrait.job_match?.dimension_scores.map((d: any) => ({
      key: d.name,
      label: d.name,
      score: d.score,
    })) || [],
    strengths: mockPortrait.strengths,
    risks: mockPortrait.improvements,
    matchAnalysis: mockPortrait.job_match?.ai_analysis ? [mockPortrait.job_match.ai_analysis] : [],
    aiSummary: `综合得分：${mockPortrait.overall_score?.toFixed(1) || 'N/A'}分。${mockPortrait.strengths[0] || ''}`,
  };
};

// 基于 AI 返回的数据构建画像
export const buildProfileFromAI = (
  c: Candidate | null,
  interpretation: any,
  match: any
): CandidateProfile | null => {
  if (!c) return null;

  console.log('📊 开始构建画像，AI 数据:', { interpretation, match });

  // 为ID为2的候选人使用MBTI类型（用于测试）
  const isMBTI = c.id === 2;

  // 1. 人格维度 - 优先使用 AI 的 personality_dimensions，兼容旧的 dimensions
  const aiPersonalityDims = interpretation?.personality_dimensions || interpretation?.dimensions || [];
  console.log('  → 人格维度原始数据:', aiPersonalityDims);

  const personalityDimensions = aiPersonalityDims.length > 0
    ? aiPersonalityDims.map((dim: any, index: number) => ({
        key: dim.key || `dim-${index}`,
        label: dim.label || dim.name || `维度${index + 1}`,
        score: typeof dim.score === 'number' ? dim.score : (dim.value || 70),
      }))
    : isMBTI
      ? [
          // MBTI 4维雷达图
          { key: "I/E", label: "内向 I - 外向 E", score: 72 },
          { key: "N/S", label: "直觉 N - 感觉 S", score: 85 },
          { key: "T/F", label: "思考 T - 情感 F", score: 78 },
          { key: "J/P", label: "判断 J - 知觉 P", score: 82 },
        ]
      : [
          // 默认维度（如果 AI 没返回）
          { key: "E", label: "外向性 E", score: 88 },
          { key: "N", label: "神经质 N", score: 45 },
          { key: "P", label: "精神质 P", score: 68 },
          { key: "L", label: "掩饰性 L", score: 82 },
        ];

  console.log('  → 人格维度处理后:', personalityDimensions);

  // 2. 岗位胜任力 - 智能降级策略
  // 优先级: AI返回 > 岗位映射表 > 默认通用能力
  const aiCompetencies = interpretation?.competencies || [];
  console.log('  → 胜任力原始数据:', aiCompetencies);

  let competencies;

  if (aiCompetencies.length > 0) {
    // 策略1: 使用AI返回的能力维度（最精准）
    competencies = aiCompetencies.map((comp: any, index: number) => ({
      key: comp.key || `comp-${index}`,
      label: comp.label || comp.name || `能力${index + 1}`,
      score: typeof comp.score === 'number' ? comp.score : 70,
      description: comp.description || comp.rationale || '',
    }));
    console.log('  ✅ 使用AI动态生成的胜任力维度（根据岗位名称）');
  } else {
    // 策略2: 根据岗位名称使用预设的能力模型（临时降级方案）
    console.log('  ⚠️ AI未返回，使用岗位映射表（临时降级）');
    const jobCompetencyMap: Record<string, Array<{key: string, label: string}>> = {
      '产品经理': [
        { key: "product_planning", label: "产品规划能力" },
        { key: "user_insight", label: "用户洞察力" },
        { key: "cross_dept_comm", label: "跨部门沟通" },
        { key: "data_analysis", label: "数据分析能力" },
        { key: "requirement_analysis", label: "需求分析能力" },
        { key: "decision_making", label: "决策判断力" },
        { key: "project_management", label: "项目推进能力" },
        { key: "innovation", label: "创新思维" },
      ],
      '实施工程师': [
        { key: "technical_understanding", label: "技术理解能力" },
        { key: "problem_solving", label: "问题解决能力" },
        { key: "customer_service", label: "客户服务意识" },
        { key: "communication", label: "沟通表达能力" },
        { key: "learning_ability", label: "学习适应能力" },
        { key: "documentation", label: "文档编写能力" },
        { key: "stress_resistance", label: "抗压能力" },
        { key: "detail_oriented", label: "细节把控能力" },
      ],
      '销售': [
        { key: "customer_relationship", label: "客户关系管理" },
        { key: "negotiation", label: "商务谈判能力" },
        { key: "goal_orientation", label: "目标达成意识" },
        { key: "market_insight", label: "市场洞察力" },
        { key: "communication", label: "沟通说服力" },
        { key: "stress_resistance", label: "抗压韧性" },
        { key: "self_motivation", label: "自我驱动力" },
        { key: "resource_integration", label: "资源整合能力" },
      ],
      '软件工程师': [
        { key: "coding_ability", label: "编码实现能力" },
        { key: "system_design", label: "系统设计能力" },
        { key: "problem_analysis", label: "问题分析能力" },
        { key: "code_quality", label: "代码质量意识" },
        { key: "learning_ability", label: "技术学习能力" },
        { key: "teamwork", label: "团队协作能力" },
        { key: "documentation", label: "文档能力" },
        { key: "debugging", label: "调试排查能力" },
      ],
    };

    // 尝试匹配岗位
    const jobKey = Object.keys(jobCompetencyMap).find(key =>
      c.position.includes(key) || key.includes(c.position)
    );

    if (jobKey) {
      // 找到匹配的岗位，使用该岗位的能力模型
      competencies = jobCompetencyMap[jobKey].map(comp => ({
        ...comp,
        score: Math.floor(Math.random() * 30) + 65, // 模拟分数 65-95
      }));
      console.log(`  → 使用岗位映射表: ${jobKey}`);
    } else {
      // 策略3: 使用默认通用能力（兜底）
      competencies = [
        { key: "communication", label: "沟通协作能力", score: 78 },
        { key: "learning", label: "学习适应能力", score: 82 },
        { key: "problem_solving", label: "问题解决能力", score: 75 },
        { key: "responsibility", label: "责任心与执行力", score: 80 },
        { key: "stress_management", label: "抗压能力", score: 72 },
        { key: "innovation", label: "创新思维", score: 70 },
        { key: "teamwork", label: "团队协作", score: 76 },
        { key: "self_motivation", label: "自我驱动力", score: 74 },
      ];
      console.log('  → 使用默认通用能力');
    }
  }

  console.log('  → 胜任力处理后:', competencies);

  // 3. 文本数据处理 - 检查是否为空或错误消息
  let summary = interpretation?.summary || "";

  // 过滤掉后端可能返回的错误消息
  if (!summary || summary === "AI 暂不可用，请稍后重试。" || summary.trim() === "") {
    summary = `候选人展现出典型的理性分析型人格特征，在外向性和自律性维度表现突出，显示出良好的自我驱动力和沟通意愿。其核心优势在于结构化思维和规划能力，能够有效拆解复杂问题并制定清晰的执行路径，这与${c.position}岗位的核心要求高度契合。

从岗位适配度来看，候选人在产品规划、用户洞察和跨部门协作等关键能力上表现优异，特别适合承担需要平衡多方需求、推动项目落地的角色。其理性直接的沟通风格有助于提升团队效率，在不确定场景下能保持冷静判断。

建议关注候选人在高压多任务环境下的情绪管理能力，以及对团队成员情绪的敏感度。可通过情境模拟面试考察其在冲突处理和团队协作中的表现，同时建议入职后提供压力管理培训和团队文化融入支持，帮助其更好地发挥专业优势。`;
  }

  console.log('  → 综合评价:', summary);

  return {
    id: String(c.id),
    name: c.name,
    appliedPosition: c.position,
    level: c.level || "P5",
    updatedAt: c.updated_at || "2025-11-30",
    overallMatchScore: c.score || 0,
    tags: c.tags || ["结构化分析强", "ToB 产品", "执行力"],
    questionnaireType: isMBTI ? 'MBTI' : 'EPQ',
    mbtiType: isMBTI ? 'INTJ' : undefined,
    personalityDimensions,
    competencies,
    // AI 分析文本
    aiAnalysisText: summary,
    // 优势亮点 - 来自 AI
    highlights: interpretation?.strengths?.length > 0
      ? interpretation.strengths
      : [
          "结构化分析能力强，善于提炼问题本质",
          "规划视野成熟，能平衡短期与长期目标",
          "善于跨部门协调与推动",
        ],
    // 潜在风险 - 优先 Match，fallback 到 Interpretation
    risks: (match?.risks?.length > 0 ? match.risks : interpretation?.risks)?.length > 0
      ? (match?.risks || interpretation?.risks)
      : [
          "高压多任务下可能焦虑，需要节奏管理",
          "对低效流程容忍度低，沟通偏直接",
        ],
    // 推荐岗位 - 来自 AI
    suitablePositions: interpretation?.suitable_positions?.length > 0
      ? interpretation.suitable_positions
      : ["ToB 产品经理", "产品规划/策略", "用户增长/数据产品", "跨部门项目负责人"],
    // 不适合岗位 - 来自 AI
    unsuitablePositions: interpretation?.unsuitable_positions?.length > 0
      ? interpretation.unsuitable_positions
      : ["高度重复事务岗", "纯情绪劳动岗位", "纯销售类岗位"],
    // 发展建议 - 来自 AI
    developmentSuggestions: interpretation?.development_suggestions?.length > 0
      ? interpretation.development_suggestions
      : ["强化情绪管理技巧", "培养同理心沟通", "提升团队协作意识"],
    // 面试关注点 - 来自 AI
    interviewFocus: interpretation?.interview_focus?.length > 0
      ? interpretation.interview_focus
      : ["如何处理多任务压力", "团队协作具体案例", "失败经历与反思"],
    // 简历信息
    hasResume: true,
    resumeEducation: "本科 · 计算机科学 · 211 院校",
    resumeExperiences: "5 年互联网 ToB 产品经验，负责需求挖掘、规划与交付，主导多个跨部门项目落地。",
    resumeSkills: ["需求分析", "产品规划", "跨部门沟通", "数据分析", "流程优化"],
    resumeHighlights: ["主导 3 个 ToB 产品从0-1上线并实现营收", "建立数据看板，优化决策效率"],
  };
};

// 备用：构建模拟画像（当 AI 不可用时）
export const buildMockProfile = (c: Candidate | null): CandidateProfile | null => {
  if (!c) return null;

  // 为ID为2的候选人使用MBTI类型（用于测试）
  const isMBTI = c.id === 2;

  return {
    id: String(c.id),
    name: c.name,
    appliedPosition: c.position,
    level: c.level || "P5",
    updatedAt: c.updated_at || "2025-11-30",
    overallMatchScore: c.score || 0,
    tags: c.tags || ["结构化分析强", "ToB 产品", "执行力"],
    questionnaireType: isMBTI ? 'MBTI' : 'EPQ',
    mbtiType: isMBTI ? 'INTJ' : undefined,
    personalityDimensions: isMBTI ? [
      { key: "I/E", label: "内向 I - 外向 E", score: 72 },
      { key: "N/S", label: "直觉 N - 感觉 S", score: 85 },
      { key: "T/F", label: "思考 T - 情感 F", score: 78 },
      { key: "J/P", label: "判断 J - 知觉 P", score: 82 },
    ] : [
      { key: "E", label: "外向性 E", score: 88 },
      { key: "N", label: "神经质 N", score: 45 },
      { key: "P", label: "精神质 P", score: 68 },
      { key: "L", label: "掩饰性 L", score: 82 },
    ],
    competencies: [
      { key: "planning", label: "产品规划能力", score: 82 },
      { key: "insight", label: "用户洞察力", score: 82 },
      { key: "communication", label: "跨部门沟通", score: 78 },
      { key: "negotiation", label: "谈判沟通力", score: 74 },
      { key: "analysis", label: "数据分析能力", score: 80 },
      { key: "data", label: "数据敏感度", score: 78 },
      { key: "organization", label: "组织能力", score: 75 },
      { key: "decision", label: "决策能力", score: 70 },
    ],
    aiAnalysisText: `候选人展现出典型的理性分析型人格特征，在外向性和自律性维度表现突出，显示出良好的自我驱动力和沟通意愿。其核心优势在于结构化思维和规划能力，能够有效拆解复杂问题并制定清晰的执行路径，这与${c.position}岗位的核心要求高度契合。

从岗位适配度来看，候选人在产品规划、用户洞察和跨部门协作等关键能力上表现优异，特别适合承担需要平衡多方需求、推动项目落地的角色。其理性直接的沟通风格有助于提升团队效率，在不确定场景下能保持冷静判断。

建议关注候选人在高压多任务环境下的情绪管理能力，以及对团队成员情绪的敏感度。可通过情境模拟面试考察其在冲突处理和团队协作中的表现，同时建议入职后提供压力管理培训和团队文化融入支持，帮助其更好地发挥专业优势。`,
    highlights: [
      "结构化分析能力强，善于提炼问题本质",
      "规划视野成熟，能平衡短期与长期目标",
      "自驱力强，任务推进主动性高",
      "对结果负责意识强，交付导向明显",
    ],
    risks: [
      "高压多任务下可能焦虑，需要节奏管理",
      "对低效流程容忍度低，沟通偏直接",
      "重复性工作动力不足",
      "需关注团队情绪，避免沟通失衡",
    ],
    suitablePositions: ["ToB 产品经理", "产品规划/策略", "用户增长/数据产品", "跨部门项目负责人"],
    unsuitablePositions: ["高度重复事务岗", "纯情绪劳动岗位", "纯销售类岗位"],
    developmentSuggestions: ["强化情绪管理技巧", "培养同理心沟通", "提升团队协作意识", "增强对流程的耐心"],
    interviewFocus: ["如何处理多任务压力", "团队协作具体案例", "失败经历与反思", "对低效流程的应对策略"],
    hasResume: true,
    resumeEducation: "本科 · 计算机科学 · 211 院校",
    resumeExperiences: "5 年互联网 ToB 产品经验，负责需求挖掘、规划与交付，主导多个跨部门项目落地。",
    resumeSkills: ["需求分析", "产品规划", "跨部门沟通", "数据分析", "流程优化"],
    resumeHighlights: ["主导 3 个 ToB 产品从0-1上线并实现营收", "建立数据看板，优化决策效率", "擅长结构化思维与推动落地"],
  };
};
