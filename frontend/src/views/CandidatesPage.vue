<script setup lang="ts">
import { onMounted, ref, computed, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import HeaderBar from "../components/HeaderBar.vue";
import { fetchCandidates, fetchCandidate } from "../api/candidates";
import type { Candidate, CandidateProfile } from "../types/candidate";
import { getMatch, getInterpretation } from "../apis/ai";
import CandidatePortraitCard from "../components/candidate/CandidatePortraitCard.vue";
import SurveyDetailCard from "../components/candidate/SurveyDetailCard.vue";
import AssessmentAccordion from "../components/candidate/AssessmentAccordion.vue";
import PortraitDrawer from "../components/candidate/PortraitDrawer.vue";
// ⭐ 新增：候选人画像API（Phase 3后端API）
import { getCandidatePortrait, buildMockPortrait, type AnalysisLevel } from "../api/candidatePortraits";

// 路由
const route = useRoute();
const router = useRouter();

const loading = ref(false);
const listErrorMsg = ref("");  // 列表加载错误
const portraitErrorMsg = ref("");  // 画像加载错误
const candidates = ref<Candidate[]>([]);
const activeCandidate = ref<Candidate | null>(null);
const page = ref(1);
const pageSize = 10;
const total = ref(0);
const aiLoading = ref(false);
const aiInterpretation = ref<{ dimensions?: any[]; strengths?: string[]; risks?: string[]; summary?: string }>({});
const aiMatch = ref<{ match_analysis?: string[]; risks?: string[]; follow_up_questions?: string[] }>({});
const activeProfile = ref<CandidateProfile | null>(null);

// ⭐ 重新生成画像进度
const regenerateProgress = ref(0);
const isPortraitRefreshing = ref(false); // 画像刷新动画状态
let regenerateTimer: ReturnType<typeof setInterval> | null = null;
let regenerateStartTime = 0;
const minProgressTime = 2000; // 最少显示2秒进度条

const startRegenerateProgress = () => {
  regenerateProgress.value = 0;
  regenerateStartTime = Date.now();
  if (regenerateTimer) clearInterval(regenerateTimer);
  
  regenerateTimer = setInterval(() => {
    const elapsed = Date.now() - regenerateStartTime;
    // 前2秒内进度最多到80%，确保用户能看到进度条
    const maxProgress = elapsed < minProgressTime ? 80 : 95;
    
    if (regenerateProgress.value < maxProgress) {
      // 更慢的增长速度
      const increment = Math.max(0.5, (maxProgress - regenerateProgress.value) / 15);
      regenerateProgress.value = Math.min(maxProgress, regenerateProgress.value + increment);
    }
  }, 100); // 更频繁更新，动画更平滑
};

const stopRegenerateProgress = () => {
  if (regenerateTimer) {
    clearInterval(regenerateTimer);
    regenerateTimer = null;
  }
  regenerateProgress.value = 100;
  
  // 触发画像刷新动画
  isPortraitRefreshing.value = true;
  setTimeout(() => {
    isPortraitRefreshing.value = false;
  }, 800);
  setTimeout(() => {
    regenerateProgress.value = 0;
  }, 500);
};

// 搜索关键词
const searchKeyword = ref('');

// V45: 年份/月份筛选
const filterYear = ref<number | null>(null);
const filterMonth = ref<number | null>(null);

// 生成年份选项（从2024年到当前年份）
const yearOptions = computed(() => {
  const currentYear = new Date().getFullYear();
  const years: number[] = [];
  for (let y = currentYear; y >= 2024; y--) {
    years.push(y);
  }
  return years;
});

// 月份选项
const monthOptions = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12];

// V45: 删除功能已移至人员管理页面，此处隐藏
// const showDeleteConfirm = ref(false);
// const deleteTarget = ref<Candidate | null>(null);
// const deleteLoading = ref(false);

// ⭐ 右侧区域Tab切换：'portrait' = 专业测评画像, 'survey' = 问卷调查
const activeTab = ref<'portrait' | 'survey'>('portrait');

// ⭐ 抽屉状态：点击测评记录后打开抽屉显示完整画像
const drawerVisible = ref(false);
const selectedAssessment = ref<any>(null);

// 打开画像抽屉
const openPortraitDrawer = (assessment: any) => {
  selectedAssessment.value = assessment;
  
  // ⭐ 关键修复：切换主画像的测评类型和维度数据
  if (activeProfile.value && assessment) {
    // 更新主画像的测评类型
    activeProfile.value.questionnaireType = assessment.questionnaire_type;
    
    // ⭐ 更新主画像的维度数据为该测评的维度
    if (assessment.personality_dimensions && assessment.personality_dimensions.length > 0) {
      activeProfile.value.personalityDimensions = assessment.personality_dimensions;
      console.log('🔄 切换维度数据:', assessment.questionnaire_type, '→', assessment.personality_dimensions.length, '个维度');
    }
  }
  
  drawerVisible.value = true;
};

// 关闭画像抽屉
const closePortraitDrawer = () => {
  drawerVisible.value = false;
  setTimeout(() => {
    selectedAssessment.value = null;
  }, 300);
};

// ⭐ 处理画像重新生成事件（支持分析级别）- V38: 支持缓存切换
const handlePortraitRegenerated = async (level: 'pro' | 'expert' = 'pro', forceRefresh: boolean = true) => {
  console.log('🔄 handlePortraitRegenerated 被调用, 分析级别:', level, ', 强制刷新:', forceRefresh);
  // 重新加载当前候选人的画像数据（保持抽屉打开，让用户看到更新后的画像）
  if (activeCandidate.value?.id) {
    console.log('🔄 开始加载画像，候选人ID:', activeCandidate.value.id, '级别:', level, '强制刷新:', forceRefresh);
    
    // 如果是从缓存加载，不需要显示长时间的进度动画
    if (!forceRefresh) {
      // 从缓存加载，快速切换
      aiLoading.value = true;
      try {
        const portrait = await getCandidatePortrait(activeCandidate.value.id, false, level);
        if (portrait) {
          activeProfile.value = convertRealPortraitToProfile(portrait);
          console.log('✅ 从缓存加载画像成功 (级别:', level, ')');
        }
      } catch (error) {
        console.error('从缓存加载画像失败:', error);
      } finally {
        aiLoading.value = false;
      }
      return;
    }
    
    // 强制刷新，需要调用AI重新生成
    aiLoading.value = true;
    startRegenerateProgress(); // 开始进度动画
    console.log('🔄 进度动画已启动, regenerateProgress:', regenerateProgress.value);
    
    // 根据分析级别调整最小显示时间 - V5: 只有 pro 和 expert
    const levelMinTime: Record<string, number> = {
      pro: minProgressTime * 1.5,
      expert: minProgressTime * 2,
    };
    
    try {
      // ⭐ 使用 refresh=true 强制刷新画像（清除缓存），传递分析级别
      const [portrait] = await Promise.all([
        getCandidatePortrait(activeCandidate.value.id, true, level),
        // 确保进度条至少显示一定时间
        new Promise(resolve => setTimeout(resolve, levelMinTime[level]))
      ]);
      
      if (portrait) {
        activeProfile.value = convertRealPortraitToProfile(portrait);
        console.log('✅ 画像已更新 (级别:', level, ')');
      }
      // ⭐ 不关闭抽屉，让用户直接看到更新后的画像
    } catch (error) {
      console.error('重新加载画像失败:', error);
    } finally {
      stopRegenerateProgress(); // 停止进度动画
      aiLoading.value = false;
      console.log('🔄 进度动画已停止');
    }
  }
};

// 计算当前候选人是否有专业测评和问卷调查
const hasProfessional = computed(() => {
  return activeCandidate.value?.submission_types?.includes('professional') ?? false;
});

const hasSurvey = computed(() => {
  return activeCandidate.value?.submission_types?.includes('survey') ?? false;
});

// 是否显示Tab切换（始终显示，让用户知道有两种类型）
const showTabSwitch = computed(() => {
  // 只要选中了候选人就显示Tab
  return !!activeCandidate.value;
});

// 过滤后的候选人列表（支持按姓名、手机号、岗位、标签搜索 + V45: 年份/月份筛选）
const filteredCandidates = computed(() => {
  let result = candidates.value;
  
  // V45: 年份筛选
  if (filterYear.value) {
    result = result.filter(c => {
      if (!c.updated_at) return false;
      const date = new Date(c.updated_at);
      return date.getFullYear() === filterYear.value;
    });
  }
  
  // V45: 月份筛选
  if (filterMonth.value) {
    result = result.filter(c => {
      if (!c.updated_at) return false;
      const date = new Date(c.updated_at);
      return (date.getMonth() + 1) === filterMonth.value;
    });
  }
  
  // 关键词搜索
  if (searchKeyword.value.trim()) {
  const keyword = searchKeyword.value.toLowerCase().trim();
    result = result.filter(c => {
    // 按姓名搜索
    if (c.name?.toLowerCase().includes(keyword)) return true;
    // 按手机号搜索
    if (c.phone?.includes(keyword)) return true;
    // 按岗位搜索
    if (c.position?.toLowerCase().includes(keyword)) return true;
    // 按标签搜索（专业测评、问卷调查）
    if (keyword.includes('测评') || keyword.includes('专业')) {
      if (c.submission_types?.includes('professional')) return true;
    }
    if (keyword.includes('问卷') || keyword.includes('调查')) {
      if (c.submission_types?.includes('survey')) return true;
    }
    return false;
  });
  }
  
  return result;
});

// 搜索处理
const handleSearch = () => {
  // 实时搜索，无需额外处理
};

// 问卷类型检测函数
const detectQuestionnaireType = (name: string): 'MBTI' | 'EPQ' | 'DISC' => {
  const upperName = (name || '').toUpperCase();
  if (upperName.includes('MBTI')) return 'MBTI';
  if (upperName.includes('DISC')) return 'DISC';
  if (upperName.includes('EPQ') || upperName.includes('艾森克')) return 'EPQ';
  // 默认返回EPQ
  return 'EPQ';
};

// 加载进度状态（美化加载界面）
const loadingProgress = ref(0);
const loadingStage = ref('');
const loadingTimer = ref<number | null>(null);

// 模拟加载进度（平滑动画）
const startLoadingProgress = () => {
  loadingProgress.value = 0;
  loadingStage.value = '正在连接AI服务...';
  
  const stages = [
    { progress: 10, text: '正在连接AI服务...' },
    { progress: 25, text: '正在分析人格特征...' },
    { progress: 40, text: '正在评估岗位匹配度...' },
    { progress: 55, text: '正在生成胜任力分析...' },
    { progress: 70, text: '正在生成综合评价...' },
    { progress: 82, text: '正在整理分析结果...' },
    { progress: 92, text: '即将完成...' },
  ];
  
  let stageIndex = 0;
  // 先立即显示第一阶段
  loadingProgress.value = stages[0].progress;
  stageIndex = 1;
  
  loadingTimer.value = window.setInterval(() => {
    if (stageIndex < stages.length) {
      loadingProgress.value = stages[stageIndex].progress;
      loadingStage.value = stages[stageIndex].text;
      stageIndex++;
    }
  }, 3000); // 每3秒更新一次
};

const stopLoadingProgress = () => {
  if (loadingTimer.value) {
    clearInterval(loadingTimer.value);
    loadingTimer.value = null;
  }
  loadingProgress.value = 100;
  loadingStage.value = '分析完成！';
};

// ⭐ Phase 4: 画像数据来源控制
// 设置为 true 使用真实API（Phase 3后端），false 使用Mock数据（查看样式）
const USE_REAL_PORTRAIT_API = true;

const loadCandidates = async () => {
  loading.value = true;
  listErrorMsg.value = "";
  try {
    const res = await fetchCandidates({ page: page.value, pageSize });
    candidates.value = res.items;
    total.value = res.total;
  } catch (err) {
    listErrorMsg.value = (err as Error).message || "加载候选人失败";
  } finally {
    loading.value = false;
  }
};

// V45: 删除功能已移至人员管理页面
// 人员画像页面只做数据展示，不提供删除功能

const selectCandidate = async (id: number) => {
  // 更新URL参数（不刷新页面）
  router.replace({ query: { ...route.query, id: String(id) } });
  
  const detail = await fetchCandidate(id);
  activeCandidate.value = detail || candidates.value.find((c) => c.id === id) || null;
  
  // ⭐ 自动选择合适的Tab
  const types = activeCandidate.value?.submission_types || [];
  if (types.includes('professional')) {
    activeTab.value = 'portrait';
  } else if (types.includes('survey')) {
    activeTab.value = 'survey';
  } else {
    activeTab.value = 'portrait'; // 默认显示专业测评
  }
  
  // ⭐ 智能加载动画逻辑：
  // 1. 先不显示加载动画，等待API响应
  // 2. 如果API响应很快（<500ms），说明是缓存数据，不显示加载动画
  // 3. 如果API响应慢（>=500ms），说明需要生成新画像，显示加载动画
  aiInterpretation.value = {};
  aiMatch.value = {};
  
  // ⭐ Phase 4: 根据开关决定使用真实API还是Mock数据
  if (USE_REAL_PORTRAIT_API) {
    // === 使用真实画像API（Phase 3后端） ===
    const timeout = 60000; // 60秒超时（AI生成可能需要较长时间）
    const LOADING_DELAY = 500; // 500ms后才显示加载动画
    
    let loadingTimerId: ReturnType<typeof setTimeout> | null = null;
    let showedLoading = false;
    
    // 延迟显示加载动画（如果API响应很快，就不显示）
    loadingTimerId = setTimeout(() => {
      if (!activeProfile.value) {
        // API还没返回，显示加载动画
        aiLoading.value = true;
        activeProfile.value = null;  // 清空以显示加载状态
        startLoadingProgress();
        showedLoading = true;
        console.log('⏳ 画像生成中，显示加载动画...');
      }
    }, LOADING_DELAY);
    
    const timeoutPromise = new Promise((_, reject) => 
      setTimeout(() => reject(new Error('请求超时')), timeout)
    );
    
    try {
      console.log(`🔄 使用真实API加载候选人 ${id} 的画像数据...`);
      const startTime = Date.now();
      
      const realPortrait = await Promise.race([
        getCandidatePortrait(id),
        timeoutPromise
      ]);
      
      const elapsed = Date.now() - startTime;
      console.log(`✅ 真实画像数据 (耗时: ${elapsed}ms, ${elapsed < LOADING_DELAY ? '缓存' : '新生成'}):`, realPortrait);
      
      // 将真实画像数据转换为前端展示格式
      activeProfile.value = convertRealPortraitToProfile(realPortrait);
    } catch (err) {
      console.error("❌ 加载真实画像失败:", err);
      portraitErrorMsg.value = `加载画像失败: ${(err as Error).message}`;
      // 降级到Mock数据
      activeProfile.value = convertMockPortraitToProfile(buildMockPortrait(id));
    } finally {
      // 清除延迟定时器
      if (loadingTimerId) {
        clearTimeout(loadingTimerId);
      }
      // 如果显示了加载动画，停止它
      if (showedLoading) {
        stopLoadingProgress();
      }
      aiLoading.value = false;
    }
  } else {
    // === 使用Mock数据（查看样式） ===
    console.log(`🎨 使用Mock数据展示候选人 ${id} 的画像样式...`);
    const mockPortrait = buildMockPortrait(id);
    activeProfile.value = convertMockPortraitToProfile(mockPortrait);
    stopLoadingProgress();  // 停止进度动画
    aiLoading.value = false;
    
    // 可选：仍然调用AI接口增强展示（当前保留旧逻辑）
  try {
    if (activeCandidate.value) {
      const mockScores = {
        E: 18,  // 外向性
        N: 10,  // 神经质
        P: 12,  // 精神质
        L: 16,  // 掩饰性
      };
      
        const [interpretation, match] = await Promise.all([
          getInterpretation({
        submission_code: `cand-${id}`,
        test_type: 'EPQ',
        scores: mockScores,
        candidate_profile: `${activeCandidate.value.name} - ${activeCandidate.value.position}`,
        position_keywords: [activeCandidate.value.position],
          }),
          getMatch({
        submission_code: `cand-${id}`,
        scores: mockScores,
        candidate_profile: `${activeCandidate.value.name} - ${activeCandidate.value.position}`,
        position_keywords: [activeCandidate.value.position],
          })
        ]);
      
      aiInterpretation.value = interpretation;
      aiMatch.value = match;
      
      console.log('🔍 AI Interpretation 数据:', interpretation);
      console.log('🔍 AI Match 数据:', match);
    }
  } catch (err) {
      console.warn("⚠️ AI分析失败（不影响Mock数据展示）:", err);
    }
  }
};

// ⭐ Phase 4: 将真实画像API数据转换为前端展示格式
const convertRealPortraitToProfile = (portrait: any): CandidateProfile => {
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
const convertMockPortraitToProfile = (mockPortrait: any): CandidateProfile => {
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
const buildProfileFromAI = (
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
const buildMockProfile = (c: Candidate | null): CandidateProfile | null => {
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

onMounted(async () => {
  await loadCandidates();
  
  // 从URL参数恢复选中的候选人
  const urlId = route.query.id;
  if (urlId) {
    const id = Number(urlId);
    if (!isNaN(id) && candidates.value.some(c => c.id === id)) {
      selectCandidate(id);
    }
  }
});
</script>

<template>
  <div class="candidates">
    <HeaderBar title="人员画像" />
    <div class="layout">
      <section class="list-panel">
        <div class="list-header">
          <!-- 第一行：搜索框 + 统计 -->
          <div class="header-row">
          <div class="search-box">
            <i class="ri-search-line"></i>
            <input 
              v-model="searchKeyword" 
              type="text" 
                placeholder="搜索姓名/手机/岗位..." 
              @input="handleSearch"
            />
            <button 
              v-if="searchKeyword" 
              class="clear-btn" 
              @click="searchKeyword = ''"
              title="清空搜索"
            >
              <i class="ri-close-line"></i>
            </button>
          </div>
          <div class="count-chip">
            <i class="ri-user-line"></i>
            <span v-if="loading">加载中</span>
            <span v-else>共 {{ total }} 人</span>
            </div>
          </div>
          <!-- V45: 第二行：年份/月份筛选 -->
          <div class="header-row filters-row">
            <div class="date-filters">
              <select v-model="filterYear" class="date-select">
                <option :value="null">全部年份</option>
                <option v-for="year in yearOptions" :key="year" :value="year">{{ year }}年</option>
              </select>
              <select v-model="filterMonth" class="date-select">
                <option :value="null">全部月份</option>
                <option v-for="month in monthOptions" :key="month" :value="month">{{ month }}月</option>
              </select>
            </div>
          </div>
        </div>
        <div class="list-body">
          <div 
            v-for="item in filteredCandidates" 
            :key="item.id" 
            class="candidate-row"
            :class="{ active: activeCandidate?.id === item.id }"
            @click="selectCandidate(item.id)"
          >
            <div class="candidate-info">
              <div class="candidate-name-row">
                <span class="candidate-name">{{ item.name }}</span>
                <!-- 性别标签 -->
                <span v-if="item.gender" class="gender-tag" :class="item.gender === '男' ? 'male' : 'female'">
                  <i :class="item.gender === '男' ? 'ri-men-line' : 'ri-women-line'"></i>
                </span>
                <!-- ⭐ 提交类型标签 -->
                <div class="submission-tags" v-if="item.submission_types?.length">
                  <span 
                    v-if="item.submission_types.includes('professional')" 
                    class="submission-tag professional"
                    title="已完成专业测评"
                  >
                    <i class="ri-brain-line"></i>
                    专业测评
                  </span>
                  <span 
                    v-if="item.submission_types.includes('survey')" 
                    class="submission-tag survey"
                    title="已填写问卷调查"
                  >
                    <i class="ri-questionnaire-line"></i>
                    问卷调查
                  </span>
                </div>
              </div>
              <div class="candidate-sub">
                <span class="position">{{ item.position || '未知岗位' }}</span>
                <span class="divider">·</span>
                <span class="phone">{{ item.phone }}</span>
              </div>
            </div>
            <!-- V45: 删除按钮已移至人员管理页面 -->
            </div>
          <div v-if="!loading && !listErrorMsg && candidates.length === 0" class="empty-state">
            <i class="ri-user-search-line"></i>
            <h4>暂无候选人</h4>
          </div>
        </div>
        
        <!-- ⭐ AI重新生成画像 - 左侧圆形动画（无边框设计，更大更清晰） -->
        <div v-if="aiLoading && activeProfile" class="regen-circle-loader">
          <div class="regen-circle-content">
            <!-- 圆形进度指示器 -->
            <div class="regen-circle-wrapper">
              <!-- 旋转光晕（放在底层） -->
              <div class="regen-circle-glow"></div>
              <svg class="regen-circle-svg" viewBox="0 0 180 180">
                <!-- 背景圆环 -->
                <circle 
                  class="regen-circle-bg" 
                  cx="90" cy="90" r="78" 
                  fill="none" 
                  stroke="rgba(255,255,255,0.3)" 
                  stroke-width="10"
                />
                <!-- 进度圆环 -->
                <circle 
                  class="regen-circle-progress" 
                  cx="90" cy="90" r="78" 
                  fill="none" 
                  stroke="url(#regenGradient)" 
                  stroke-width="10"
                  stroke-linecap="round"
                  :stroke-dasharray="490.09"
                  :stroke-dashoffset="490.09 - (490.09 * regenerateProgress / 100)"
                />
                <!-- 渐变定义 - 使用紫粉色调 -->
                <defs>
                  <linearGradient id="regenGradient" x1="0%" y1="0%" x2="100%" y2="100%">
                    <stop offset="0%" stop-color="#a855f7" />
                    <stop offset="50%" stop-color="#d946ef" />
                    <stop offset="100%" stop-color="#f0abfc" />
                  </linearGradient>
                </defs>
              </svg>
              <!-- 中心内容 -->
              <div class="regen-circle-center">
                <span class="regen-progress-number">{{ Math.round(regenerateProgress) }}</span>
                <span class="regen-progress-percent">%</span>
              </div>
            </div>
            
            <!-- 文字信息 -->
            <div class="regen-loading-info">
              <div class="regen-loading-header">
                <i class="ri-refresh-line"></i>
                <span>画像更新中</span>
              </div>
              <p class="regen-stage-text">正在融合简历数据...</p>
            </div>
          </div>
        </div>
      </section>

      <section class="detail-panel">
        <!-- ⭐ 独立悬浮胶囊Tab -->
        <div v-if="activeCandidate && showTabSwitch" class="floating-tabs">
          <button 
            class="floating-tab" 
            :class="{ active: activeTab === 'portrait', 'has-data': hasProfessional }"
            @click="activeTab = 'portrait'"
            :title="hasProfessional ? '查看专业测评画像' : '暂无专业测评数据'"
          >
            <i class="ri-brain-line"></i>
            <span>测评画像</span>
          </button>
          <button 
            class="floating-tab survey" 
            :class="{ active: activeTab === 'survey', 'has-data': hasSurvey }"
            @click="activeTab = 'survey'"
            :title="hasSurvey ? '查看问卷调查数据' : '暂无问卷调查数据'"
          >
            <i class="ri-questionnaire-line"></i>
            <span>问卷数据</span>
          </button>
          </div>
            
        <!-- ⭐ 专业测评画像内容 -->
        <template v-if="activeCandidate && activeTab === 'portrait'">
          <!-- 有专业测评数据时：只显示测评记录列表，点击打开抽屉查看画像 -->
          <template v-if="hasProfessional">
            <!-- AI加载状态 - 圆形进度 -->
        <div v-if="aiLoading && !activeProfile" class="ai-loading-circle-overlay">
          <div class="ai-loading-circle-card">
            <!-- 圆形进度指示器 -->
            <div class="circle-progress-wrapper">
              <svg class="circle-progress-svg" viewBox="0 0 120 120">
                <!-- 背景圆环 -->
                <circle 
                  class="circle-bg" 
                  cx="60" cy="60" r="52" 
                  fill="none" 
                  stroke="#e8ecf4" 
                  stroke-width="8"
                />
                <!-- 进度圆环 -->
                <circle 
                  class="circle-progress" 
                  cx="60" cy="60" r="52" 
                  fill="none" 
                  stroke="url(#progressGradient)" 
                  stroke-width="8"
                  stroke-linecap="round"
                  :stroke-dasharray="326.73"
                  :stroke-dashoffset="326.73 - (326.73 * loadingProgress / 100)"
                />
                <!-- 渐变定义 -->
                <defs>
                  <linearGradient id="progressGradient" x1="0%" y1="0%" x2="100%" y2="100%">
                    <stop offset="0%" stop-color="#6366f1" />
                    <stop offset="50%" stop-color="#8b5cf6" />
                    <stop offset="100%" stop-color="#a78bfa" />
                  </linearGradient>
                </defs>
              </svg>
              <!-- 中心内容 -->
              <div class="circle-center">
                <span class="progress-number">{{ loadingProgress }}</span>
                <span class="progress-percent">%</span>
              </div>
              <!-- 旋转光晕 -->
              <div class="circle-glow"></div>
            </div>
            
            <!-- 文字信息 -->
            <div class="loading-info">
              <div class="loading-header">
                <i class="ri-brain-line"></i>
                <span>AI 智能分析</span>
              </div>
              <p class="loading-stage-text">{{ loadingStage }}</p>
              <p class="loading-hint">
                <i class="ri-time-line"></i>
              首次分析约30s，再次访问秒开
            </p>
            </div>
          </div>
        </div>
        
        <!-- 画像错误提示 -->
        <div v-if="portraitErrorMsg && activeProfile" class="portrait-error-tip">
          <i class="ri-information-line"></i>
          <span>{{ portraitErrorMsg }}（已显示默认数据）</span>
          <button @click="portraitErrorMsg = ''" class="close-tip">
            <i class="ri-close-line"></i>
          </button>
        </div>
        
            <!-- ⭐ 测评记录列表（点击打开抽屉） -->
            <AssessmentAccordion 
              v-if="activeProfile"
              :assessments="activeProfile.assessments || []"
              :profile="activeProfile"
              @open-drawer="openPortraitDrawer"
            />
        
          
        </template>
          
          <!-- 无专业测评时的精致提示 -->
          <div v-if="!hasProfessional" class="empty-tab-content">
            <div class="empty-tab-icon">
              <i class="ri-brain-line"></i>
              <div class="empty-tab-badge">
                <i class="ri-time-line"></i>
              </div>
            </div>
            <h3>暂无专业测评数据</h3>
            <p class="single-line">该人员尚未完成专业测评，完成后将自动生成AI智能画像</p>
            <div class="empty-tab-features">
              <div class="feature-item">
                <i class="ri-pie-chart-2-line"></i>
                <span>人格特征分析</span>
              </div>
              <div class="feature-item">
                <i class="ri-bar-chart-grouped-line"></i>
                <span>岗位胜任力评估</span>
              </div>
              <div class="feature-item">
                <i class="ri-magic-line"></i>
                <span>AI综合评价</span>
              </div>
            </div>
          </div>
        </template>
        
        <!-- ⭐ 问卷调查数据内容 -->
        <template v-if="activeCandidate && activeTab === 'survey'">
          <!-- 有问卷调查数据时显示详情 -->
          <SurveyDetailCard 
            v-if="hasSurvey"
            :candidate-id="activeCandidate.id" 
            :candidate-name="activeCandidate.name" 
          />
          
          <!-- 无问卷调查时的精致提示 -->
          <div v-else class="empty-tab-content">
            <div class="empty-tab-icon survey">
              <i class="ri-questionnaire-line"></i>
              <div class="empty-tab-badge">
                <i class="ri-time-line"></i>
              </div>
            </div>
            <h3>暂无问卷调查数据</h3>
            <p class="single-line">该人员尚未填写任何问卷调查，填写后数据将自动同步</p>
            <div class="empty-tab-features survey">
              <div class="feature-item">
                <i class="ri-file-list-3-line"></i>
                <span>问卷填写记录</span>
              </div>
              <div class="feature-item">
                <i class="ri-checkbox-multiple-line"></i>
                <span>答题详情查看</span>
              </div>
              <div class="feature-item">
                <i class="ri-download-2-line"></i>
                <span>数据导出功能</span>
              </div>
            </div>
          </div>
        </template>
        
        <!-- 未选择候选人的提示 -->
        <div v-if="!activeCandidate" class="empty-detail">
          <i class="ri-user-line"></i>
          <h3>请选择候选人</h3>
          <p>点击左侧候选人列表查看详细画像</p>
        </div>
      </section>
    </div>
    
    <!-- V45: 删除功能已移至人员管理页面 -->
    
    <!-- ⭐ 画像抽屉：点击测评记录后打开，显示完整AI画像 -->
    <PortraitDrawer 
      :visible="drawerVisible"
      :profile="activeProfile"
      :assessment="selectedAssessment"
      :is-refreshing="isPortraitRefreshing"
      @close="closePortraitDrawer"
      @portrait-regenerated="(level, forceRefresh) => handlePortraitRegenerated(level, forceRefresh)"
    />
  </div>
</template>

<style scoped>
.candidates {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

.layout {
  display: grid;
  grid-template-columns: 300px 1fr;
  gap: 1rem;
  height: calc(100vh - 140px);
}

.list-panel {
  position: relative;
  background: linear-gradient(180deg, rgba(248, 250, 252, 0.8) 0%, rgba(241, 245, 249, 0.8) 100%);
  border: 1px solid rgba(99, 102, 241, 0.1);
  border-radius: 16px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.03);
}

.detail-panel {
  background: var(--bg-muted);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-lg);
  display: flex;
  flex-direction: column;
  position: relative;
  overflow: hidden;
}

/* ⭐ 独立悬浮胶囊Tab样式 */
.floating-tabs {
  position: sticky;
  top: 0;
  left: 0;
  display: flex;
  gap: 0.5rem;
  z-index: 200;
  pointer-events: auto;
  padding: 0.75rem;
  background: linear-gradient(180deg, rgba(248, 250, 252, 0.98) 0%, rgba(248, 250, 252, 0.9) 80%, transparent 100%);
  margin-bottom: -0.5rem;
}

.floating-tab {
  display: flex;
  align-items: center;
  gap: 0.375rem;
  padding: 0.5rem 0.875rem;
  border: none;
  background: rgba(255, 255, 255, 0.92);
  backdrop-filter: blur(10px);
  border-radius: 20px;
  font-size: 0.75rem;
  font-weight: 500;
  color: var(--text-muted);
  cursor: pointer;
  transition: all 0.25s ease;
  white-space: nowrap;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
  border: 1px solid rgba(139, 92, 246, 0.15);
}

.floating-tab i {
  font-size: 0.875rem;
  color: #8b5cf6;
  opacity: 0.6;
}

.floating-tab.survey i {
  color: #0891b2;
}

.floating-tab:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.12);
}

.floating-tab:hover i {
  opacity: 1;
}

/* 有数据时的样式 */
.floating-tab.has-data {
  border-color: rgba(139, 92, 246, 0.3);
}

.floating-tab.has-data i {
  opacity: 1;
}

.floating-tab.survey.has-data {
  border-color: rgba(6, 182, 212, 0.3);
}

/* 激活状态 */
.floating-tab.active {
  background: linear-gradient(135deg, #8b5cf6, #a78bfa);
  color: white;
  border-color: transparent;
  box-shadow: 0 4px 14px rgba(139, 92, 246, 0.35);
}

.floating-tab.active i {
  color: white;
  opacity: 1;
}

.floating-tab.survey.active {
  background: linear-gradient(135deg, #0891b2, #22d3ee);
  box-shadow: 0 4px 14px rgba(6, 182, 212, 0.35);
}

/* 无数据时的淡化效果 */
.floating-tab:not(.has-data):not(.active) {
  opacity: 0.55;
}

.floating-tab:not(.has-data):not(.active):hover {
  opacity: 0.8;
}

/* 加载状态遮罩 - 美化版 */
.loading-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: linear-gradient(135deg, rgba(255, 255, 255, 0.98) 0%, rgba(245, 247, 250, 0.98) 100%);
  backdrop-filter: blur(8px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 10;
  border-radius: var(--radius-lg);
}

.loading-content {
  text-align: center;
  max-width: 320px;
  padding: 2rem;
}

/* AI图标动画 */
.ai-icon-wrapper {
  position: relative;
  width: 80px;
  height: 80px;
  margin: 0 auto 1.5rem;
  display: flex;
  align-items: center;
  justify-content: center;
}

.ai-icon {
  font-size: 2.5rem;
  color: var(--primary-600);
  z-index: 2;
  animation: float 2s ease-in-out infinite;
}

.pulse-ring {
  position: absolute;
  width: 100%;
  height: 100%;
  border: 2px solid var(--primary-400);
  border-radius: 50%;
  animation: pulse-ring 2s ease-out infinite;
  opacity: 0;
}

.pulse-ring.delay-1 {
  animation-delay: 0.5s;
}

.pulse-ring.delay-2 {
  animation-delay: 1s;
}

@keyframes pulse-ring {
  0% {
    transform: scale(0.5);
    opacity: 0.8;
  }
  100% {
    transform: scale(1.5);
    opacity: 0;
  }
}

@keyframes float {
  0%, 100% {
    transform: translateY(0);
  }
  50% {
    transform: translateY(-8px);
  }
}

/* 加载文字 */
.loading-title {
  font-size: 1.25rem;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 0.5rem;
}

.loading-stage {
  font-size: 0.95rem;
  color: var(--primary-600);
  margin-bottom: 1.5rem;
  min-height: 1.5em;
}

/* 进度条 */
.progress-container {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  margin-bottom: 1.5rem;
}

.progress-bar {
  flex: 1;
  height: 8px;
  background: var(--bg-subtle);
  border-radius: 4px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, var(--primary-500), var(--primary-400));
  border-radius: 4px;
  transition: width 0.8s cubic-bezier(0.4, 0, 0.2, 1);
  position: relative;
  animation: progressPulse 1.5s ease-in-out infinite;
}

@keyframes progressPulse {
  0%, 100% {
    opacity: 1;
  }
  50% {
    opacity: 0.8;
  }
}

.progress-fill::after {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: linear-gradient(
    90deg,
    transparent,
    rgba(255, 255, 255, 0.4),
    transparent
  );
  animation: shimmer 1.5s infinite;
}

@keyframes shimmer {
  0% {
    transform: translateX(-100%);
  }
  100% {
    transform: translateX(100%);
  }
}

.progress-text {
  font-size: 0.85rem;
  font-weight: 600;
  color: var(--primary-600);
  min-width: 3em;
}

/* 提示文字 */
.loading-tip {
  font-size: 0.75rem;
  color: var(--text-muted);
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.375rem;
  padding: 0.5rem 1rem;
  background: var(--bg-subtle);
  border-radius: var(--radius-md);
  white-space: nowrap;
}

.loading-tip i {
  color: var(--warning-500);
}

/* ⭐ 新版圆形进度加载样式 */
.ai-loading-circle-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: linear-gradient(135deg, rgba(250, 251, 255, 0.95) 0%, rgba(245, 247, 252, 0.95) 100%);
  backdrop-filter: blur(12px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 10;
  border-radius: var(--radius-lg);
}

.ai-loading-circle-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1.5rem;
  padding: 2.5rem 3rem;
  background: white;
  border-radius: 24px;
  box-shadow: 
    0 4px 24px rgba(99, 102, 241, 0.08),
    0 8px 48px rgba(139, 92, 246, 0.06);
  border: 1px solid rgba(139, 92, 246, 0.1);
}

/* 圆形进度容器 */
.circle-progress-wrapper {
  position: relative;
  width: 140px;
  height: 140px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.circle-progress-svg {
  width: 100%;
  height: 100%;
  transform: rotate(-90deg);
  filter: drop-shadow(0 2px 8px rgba(99, 102, 241, 0.2));
}

.circle-bg {
  stroke: #e8ecf4;
}

.circle-progress {
  transition: stroke-dashoffset 0.8s cubic-bezier(0.4, 0, 0.2, 1);
}

/* 中心进度数字 */
.circle-center {
  position: absolute;
  display: flex;
  align-items: baseline;
  justify-content: center;
  gap: 2px;
}

.progress-number {
  font-size: 2.5rem;
  font-weight: 700;
  background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  line-height: 1;
}

.progress-percent {
  font-size: 1rem;
  font-weight: 600;
  color: #8b5cf6;
}

/* 旋转光晕 */
.circle-glow {
  position: absolute;
  width: 130%;
  height: 130%;
  border-radius: 50%;
  background: conic-gradient(
    from 0deg,
    transparent 0deg,
    rgba(99, 102, 241, 0.15) 60deg,
    transparent 120deg
  );
  animation: rotateGlow 3s linear infinite;
  pointer-events: none;
}

@keyframes rotateGlow {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

/* 文字信息区域 */
.loading-info {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.5rem;
  text-align: center;
}

.loading-header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 1.125rem;
  font-weight: 600;
  color: #4f46e5;
}

.loading-header i {
  font-size: 1.25rem;
  animation: brainPulse 2s ease-in-out infinite;
}

@keyframes brainPulse {
  0%, 100% {
    transform: scale(1);
    opacity: 1;
  }
  50% {
    transform: scale(1.1);
    opacity: 0.8;
  }
}

.loading-stage-text {
  font-size: 0.9rem;
  color: #6366f1;
  min-height: 1.5em;
  font-weight: 500;
}

.loading-hint {
  display: flex;
  align-items: center;
  gap: 0.375rem;
  font-size: 0.75rem;
  color: #9ca3af;
  padding: 0.5rem 1rem;
  background: #f8fafc;
  border-radius: 20px;
  margin-top: 0.5rem;
}

.loading-hint i {
  font-size: 0.875rem;
  color: #a78bfa;
}

/* 旧的spinner样式保留给其他地方使用 */
.loading-spinner {
  text-align: center;
}

.loading-spinner i {
  font-size: 3rem;
  color: var(--primary-600);
  animation: spin 1s linear infinite;
}

.loading-spinner p {
  margin-top: var(--space-3);
  font-size: 0.875rem;
  color: var(--text-secondary);
  font-weight: 500;
}

@keyframes spin {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

/* 画像错误提示 */
.portrait-error-tip {
  position: absolute;
  top: 0.75rem;
  left: 50%;
  transform: translateX(-50%);
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 1rem;
  background: rgba(251, 191, 36, 0.15);
  border: 1px solid rgba(251, 191, 36, 0.3);
  border-radius: var(--radius-md);
  font-size: 0.8rem;
  color: #b45309;
  z-index: 5;
  max-width: 90%;
}

.portrait-error-tip i {
  color: #f59e0b;
}

.portrait-error-tip .close-tip {
  background: none;
  border: none;
  padding: 2px;
  cursor: pointer;
  color: #b45309;
  opacity: 0.7;
}

.portrait-error-tip .close-tip:hover {
  opacity: 1;
}

/* 空状态提示 */
.empty-detail {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: var(--text-tertiary);
  padding: var(--space-8);
}

.empty-detail i {
  font-size: 4rem;
  margin-bottom: var(--space-4);
  opacity: 0.3;
}

.empty-detail h3 {
  font-size: 1.25rem;
  font-weight: 600;
  color: var(--text-secondary);
  margin-bottom: var(--space-2);
}

.empty-detail p {
  font-size: 0.875rem;
  color: var(--text-tertiary);
}

/* AI加载徽章（在画像右上角） */
/* ⭐ 左侧圆形加载动画 - 重新生成画像专用（紫粉色调，无边框设计） */
.regen-circle-loader {
  position: fixed;
  top: 50%;
  left: calc(var(--sidebar-width, 220px) + 170px);
  transform: translate(-50%, -50%);
  z-index: 10000;
  animation: regenLoaderFadeIn 0.4s ease-out;
}

@keyframes regenLoaderFadeIn {
  from { opacity: 0; transform: translate(-50%, -50%) scale(0.9); }
  to { opacity: 1; transform: translate(-50%, -50%) scale(1); }
}

.regen-circle-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1.5rem;
  /* 去掉白色方框背景 */
}

.regen-circle-wrapper {
  position: relative;
  width: 180px;
  height: 180px;
}

.regen-circle-svg {
  width: 100%;
  height: 100%;
  transform: rotate(-90deg);
  filter: drop-shadow(0 8px 32px rgba(147, 51, 234, 0.35));
}

.regen-circle-bg {
  stroke: rgba(255, 255, 255, 0.4);
}

.regen-circle-progress {
  transition: stroke-dashoffset 0.2s ease-out;
  filter: drop-shadow(0 0 12px rgba(192, 38, 211, 0.6));
}

.regen-circle-center {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  display: flex;
  align-items: baseline;
  gap: 3px;
}

.regen-progress-number {
  font-size: 3.5rem;
  font-weight: 700;
  background: linear-gradient(135deg, #ffffff 0%, #f0e6ff 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  font-variant-numeric: tabular-nums;
  text-shadow: 0 4px 20px rgba(147, 51, 234, 0.4);
}

.regen-progress-percent {
  font-size: 1.5rem;
  font-weight: 600;
  color: rgba(255, 255, 255, 0.9);
}

.regen-circle-glow {
  position: absolute;
  top: -10px;
  left: -10px;
  width: calc(100% + 20px);
  height: calc(100% + 20px);
  border-radius: 50%;
  background: conic-gradient(
    from 0deg,
    transparent 0deg,
    rgba(192, 38, 211, 0.25) 60deg,
    transparent 120deg
  );
  animation: regenGlowRotate 2s linear infinite;
}

@keyframes regenGlowRotate {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.regen-loading-info {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.6rem;
}

.regen-loading-header {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  font-size: 1.2rem;
  font-weight: 600;
  color: #ffffff;
  text-shadow: 0 2px 12px rgba(0, 0, 0, 0.2);
}

.regen-loading-header i {
  font-size: 1.3rem;
  animation: regenIconSpin 2s linear infinite;
}

@keyframes regenIconSpin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.regen-stage-text {
  font-size: 1rem;
  color: rgba(255, 255, 255, 0.85);
  margin: 0;
  text-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
}

@keyframes progressSlideUp {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.regen-progress-track {
  position: relative;
  width: 280px;
  height: 6px;
  background: rgba(99, 102, 241, 0.15);
  border-radius: 10px;
  overflow: visible;
  backdrop-filter: blur(10px);
}

.regen-progress-fill {
  position: absolute;
  top: 0;
  left: 0;
  height: 100%;
  background: linear-gradient(90deg, 
    #818cf8 0%, 
    #a78bfa 25%, 
    #c084fc 50%, 
    #e879f9 75%, 
    #f472b6 100%
  );
  background-size: 200% 100%;
  border-radius: 10px;
  animation: regenFillFlow 2s ease-in-out infinite;
  transition: width 0.2s ease-out;
  box-shadow: 
    0 0 20px rgba(168, 85, 247, 0.5),
    0 0 40px rgba(168, 85, 247, 0.3);
}

/* 旧样式已移除，使用新的精简样式 */

@keyframes particleFloat {
  0%, 100% {
    opacity: 0;
    transform: translateY(0) scale(0);
  }
  20% {
    opacity: 1;
    transform: translateY(-15px) scale(1);
  }
  80% {
    opacity: 0.5;
    transform: translateY(-35px) scale(0.5);
  }
}

@keyframes slideUp {
  from {
    opacity: 0;
    transform: translateX(-50%) translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateX(-50%) translateY(0);
  }
}

@keyframes iconPulse {
  0%, 100% { transform: scale(1); }
  50% { transform: scale(1.1); }
}

@keyframes pulseGlow {
  0%, 100% { 
    opacity: 0.5;
    transform: scale(0.8);
  }
  50% {
    opacity: 1;
    transform: scale(1.3);
  }
}

@keyframes dotBounce {
  0%, 60%, 100% { transform: translateY(0); }
  30% { transform: translateY(-4px); }
}

@keyframes progressSlide {
  0% { left: -40%; }
  100% { left: 100%; }
}

/* ===== 现代化列表样式 ===== */
/* ⭐ 美化后的列表头部 */
.list-header {
  display: flex;
  flex-direction: column;
  gap: 0.625rem;
  padding: 0.875rem 1rem;
  background: linear-gradient(180deg, rgba(99, 102, 241, 0.04) 0%, rgba(168, 85, 247, 0.02) 100%);
  border-bottom: 1px solid rgba(99, 102, 241, 0.1);
}

/* V45: 头部行布局 */
.header-row {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  width: 100%;
}

.filters-row {
  padding-top: 0.25rem;
}

/* V45: 日期筛选器样式 */
.date-filters {
  display: flex;
  gap: 0.5rem;
  flex: 1;
}

.date-select {
  flex: 1;
  padding: 0.5rem 0.625rem;
  font-size: 0.8125rem;
  border: 1px solid rgba(99, 102, 241, 0.2);
  border-radius: 10px;
  background: white;
  color: var(--text-secondary);
  cursor: pointer;
  transition: all 0.2s ease;
  outline: none;
}

.date-select:hover {
  border-color: var(--primary-400);
  background: rgba(99, 102, 241, 0.02);
}

.date-select:focus {
  border-color: var(--primary-500);
  box-shadow: 0 0 0 2px rgba(99, 102, 241, 0.1);
}

.search-box {
  flex: 1;
  display: flex;
  align-items: center;
  gap: 0.625rem;
  background: white;
  border: 1px solid rgba(99, 102, 241, 0.15);
  border-radius: 12px;
  padding: 0.625rem 0.875rem;
  transition: all 0.25s ease;
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.04);
}

.search-box:focus-within {
  border-color: var(--primary-500);
  box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.1);
}

.search-box i {
  color: var(--primary-400);
  font-size: 1rem;
}

.search-box input {
  background: transparent;
  border: none;
  color: var(--text-primary);
  outline: none;
  font-size: 0.8125rem;
  width: 100%;
}

.search-box input::placeholder {
  color: var(--text-muted);
}

.search-box .clear-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 20px;
  height: 20px;
  padding: 0;
  background: rgba(0, 0, 0, 0.08);
  border: none;
  border-radius: 50%;
  color: var(--text-muted);
  cursor: pointer;
  flex-shrink: 0;
  transition: all 0.2s;
}

.search-box .clear-btn:hover {
  background: rgba(0, 0, 0, 0.15);
  color: var(--text-primary);
}

.search-box .clear-btn i {
  font-size: 0.75rem;
}

/* ⭐ 美化后的统计徽章 */
.count-chip {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  padding: 0.5rem 0.875rem;
  background: linear-gradient(135deg, rgba(99, 102, 241, 0.12) 0%, rgba(168, 85, 247, 0.08) 100%);
  color: var(--primary-600);
  border-radius: 20px;
  font-weight: 600;
  font-size: 0.8rem;
  white-space: nowrap;
  border: 1px solid rgba(99, 102, 241, 0.2);
  box-shadow: 0 2px 6px rgba(99, 102, 241, 0.1);
}

.count-chip i {
  font-size: 0.9rem;
  opacity: 0.85;
}

.list-body {
  overflow-y: auto;
  flex: 1;
  padding: 0.75rem;
}

/* ⭐ 美化后的人员卡片样式 */
.candidate-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 1rem 1.125rem;
  margin-bottom: 0.625rem;
  background: white;
  border-radius: 14px;
  border: 1px solid rgba(99, 102, 241, 0.08);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.03);
  transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
  gap: 0.75rem;
  cursor: pointer;
  position: relative;
  overflow: hidden;
}

.candidate-row::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  width: 4px;
  height: 100%;
  background: linear-gradient(180deg, var(--primary-400), var(--primary-600));
  opacity: 0;
  transition: opacity 0.25s ease;
}

.candidate-row:hover {
  background: linear-gradient(135deg, rgba(99, 102, 241, 0.05) 0%, rgba(168, 85, 247, 0.03) 100%);
  border-color: rgba(99, 102, 241, 0.2);
  transform: translateX(4px);
  box-shadow: 0 4px 16px rgba(99, 102, 241, 0.1);
}

.candidate-row:hover::before {
  opacity: 0.6;
}

.candidate-row.active {
  background: linear-gradient(135deg, rgba(99, 102, 241, 0.12) 0%, rgba(168, 85, 247, 0.08) 100%);
  border-color: rgba(99, 102, 241, 0.35);
  box-shadow: 0 4px 20px rgba(99, 102, 241, 0.15);
}

.candidate-row.active::before {
  opacity: 1;
}

.candidate-info {
  flex: 1;
  min-width: 0;
  cursor: pointer;
}

.delete-btn {
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(239, 68, 68, 0.06);
  border: 1px solid rgba(239, 68, 68, 0.12);
  color: var(--text-muted);
  cursor: pointer;
  border-radius: 10px;
  transition: all 0.25s ease;
  flex-shrink: 0;
  opacity: 0;
  transform: scale(0.9);
}

.candidate-row:hover .delete-btn {
  opacity: 1;
  transform: scale(1);
}

.delete-btn:hover {
  background: rgba(239, 68, 68, 0.15);
  border-color: rgba(239, 68, 68, 0.3);
  color: #ef4444;
  transform: scale(1.05);
}

.delete-btn i {
  font-size: 1rem;
}

/* ⭐ 候选人名称行（包含名称和标签） */
.candidate-name-row {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  flex-wrap: wrap;
  margin-bottom: 0.375rem;
}

.candidate-name {
  font-weight: 600;
  font-size: 0.9375rem;
  color: var(--text-primary);
  letter-spacing: -0.01em;
}

/* 性别标签 */
.gender-tag {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 1.25rem;
  height: 1.25rem;
  border-radius: 50%;
  font-size: 0.75rem;
}

.gender-tag.male {
  background: linear-gradient(135deg, #e3f2fd, #bbdefb);
  color: #1976d2;
}

.gender-tag.female {
  background: linear-gradient(135deg, #fce4ec, #f8bbd9);
  color: #c2185b;
}

/* ⭐ 提交类型标签容器 */
.submission-tags {
  display: flex;
  gap: 0.375rem;
  flex-wrap: wrap;
}

/* ⭐ 提交类型标签样式 - 精致胶囊 */
.submission-tag {
  display: inline-flex;
  align-items: center;
  gap: 0.25rem;
  padding: 0.2rem 0.5rem;
  border-radius: 12px;
  font-size: 0.6875rem;
  font-weight: 600;
  white-space: nowrap;
  letter-spacing: 0.02em;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
}

.submission-tag i {
  font-size: 0.625rem;
}

/* 专业测评标签 - 紫色渐变 */
.submission-tag.professional {
  background: linear-gradient(135deg, rgba(139, 92, 246, 0.18), rgba(167, 139, 250, 0.12));
  color: #7c3aed;
  border: 1px solid rgba(139, 92, 246, 0.25);
}

/* 问卷调查标签 - 青色渐变 */
.submission-tag.survey {
  background: linear-gradient(135deg, rgba(6, 182, 212, 0.18), rgba(34, 211, 238, 0.12));
  color: #0891b2;
  border: 1px solid rgba(6, 182, 212, 0.25);
}

.candidate-sub {
  color: var(--text-muted);
  font-size: 0.8rem;
  display: flex;
  align-items: center;
  gap: 0.625rem;
}

.candidate-sub .position {
  color: var(--primary-600);
  font-weight: 500;
  background: rgba(99, 102, 241, 0.08);
  padding: 0.125rem 0.5rem;
  border-radius: 6px;
}

.candidate-sub .divider {
  width: 4px;
  height: 4px;
  background: rgba(99, 102, 241, 0.3);
  border-radius: 50%;
}

.candidate-sub .phone {
  color: var(--text-tertiary);
}

.candidate-sub .divider {
  color: var(--border-default);
}

.status {
  padding: 4px 10px;
  border-radius: var(--radius-full);
  border: 1px solid var(--border-default);
  color: var(--text-secondary);
  font-size: var(--text-sm);
}

.status[data-status="已完成"] {
  color: var(--accent-success);
  border-color: rgba(34, 197, 94, 0.4);
}

.status[data-status="测评中"] {
  color: var(--accent-warning);
  border-color: rgba(245, 158, 11, 0.4);
}

.status[data-status="待测评"] {
  color: var(--text-tertiary);
}

.detail-panel {
  background: var(--bg-muted);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-lg);
  overflow-y: auto;
  padding: 0;
}

.detail-empty {
  color: var(--text-tertiary);
  display: grid;
  gap: var(--space-2);
  place-items: center;
}

.detail-empty i {
  font-size: 32px;
  color: var(--text-muted);
}

.detail-content {
  width: 100%;
  display: grid;
  gap: var(--space-3);
}

.detail-header {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  border-bottom: 1px solid var(--border-default);
  padding-bottom: var(--space-3);
}

.avatar {
  width: 48px;
  height: 48px;
  border-radius: var(--radius-full);
  background: var(--gradient-primary);
  display: grid;
  place-items: center;
  font-weight: 700;
}

.detail-name {
  font-size: var(--text-lg);
  font-weight: 700;
}

.detail-sub {
  color: var(--text-tertiary);
  font-size: var(--text-sm);
}
.tag-list {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}
.chip {
  padding: 4px 8px;
  border-radius: var(--radius-full);
  background: rgba(99, 102, 241, 0.12);
  border: 1px solid var(--border-default);
}
.meta {
  color: var(--text-tertiary);
  font-size: var(--text-sm);
}

.detail-section {
  display: flex;
  align-items: center;
  gap: var(--space-3);
}

.detail-section .label {
  color: var(--text-tertiary);
}

.detail-section.muted {
  color: var(--text-tertiary);
  font-size: var(--text-sm);
}
.ai-panel {
  margin-top: var(--space-3);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-lg);
  padding: var(--space-3);
  background: var(--bg-subtle);
  display: grid;
  gap: var(--space-2);
}
.ai-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.ai-section {
  display: grid;
  gap: 4px;
}
.ai-title {
  font-weight: 700;
}
.ai-empty {
  color: var(--text-tertiary);
}
.ai-skeleton {
  color: var(--text-tertiary);
}

@media (max-width: 1024px) {
  .layout {
    grid-template-columns: 1fr;
    height: auto;
  }
}

/* ⭐ 删除确认弹窗样式 */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  backdrop-filter: blur(4px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.delete-confirm-modal {
  background: white;
  border-radius: 20px;
  padding: 2rem;
  width: 400px;
  max-width: 90vw;
  text-align: center;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.15);
  animation: modalSlideIn 0.2s ease-out;
}

@keyframes modalSlideIn {
  from {
    opacity: 0;
    transform: scale(0.95) translateY(-10px);
  }
  to {
    opacity: 1;
    transform: scale(1) translateY(0);
  }
}

.modal-icon {
  width: 64px;
  height: 64px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto 1.25rem;
}

.modal-icon.warning {
  background: linear-gradient(135deg, rgba(239, 68, 68, 0.1), rgba(239, 68, 68, 0.05));
}

.modal-icon.warning i {
  font-size: 2rem;
  color: #ef4444;
}

.delete-confirm-modal h3 {
  margin: 0 0 0.75rem;
  font-size: 1.25rem;
  font-weight: 600;
  color: var(--text-primary);
}

.delete-name {
  margin: 0 0 0.75rem;
  color: var(--text-secondary);
  font-size: 0.95rem;
}

.warning-text {
  margin: 0 0 1.5rem;
  padding: 0.75rem 1rem;
  background: rgba(239, 68, 68, 0.08);
  border-radius: 10px;
  color: #dc2626;
  font-size: 0.85rem;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
}

.modal-actions {
  display: flex;
  gap: 0.75rem;
  justify-content: center;
}

.btn-secondary {
  padding: 0.75rem 1.5rem;
  border: 1px solid var(--border-default);
  background: white;
  color: var(--text-secondary);
  border-radius: 10px;
  font-size: 0.9rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-secondary:hover {
  background: var(--bg-subtle);
  border-color: var(--border-hover);
}

.btn-danger {
  padding: 0.75rem 1.5rem;
  border: none;
  background: linear-gradient(135deg, #ef4444, #dc2626);
  color: white;
  border-radius: 10px;
  font-size: 0.9rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.btn-danger:hover {
  background: linear-gradient(135deg, #dc2626, #b91c1c);
  transform: translateY(-1px);
}

.btn-danger:disabled {
  opacity: 0.6;
  cursor: not-allowed;
  transform: none;
}

.animate-spin {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

/* ⭐ 无数据精致提示样式 */
.empty-tab-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 3rem 2rem;
  text-align: center;
  background: linear-gradient(180deg, rgba(248, 250, 252, 0.5) 0%, rgba(241, 245, 249, 0.3) 100%);
}

.empty-tab-icon {
  position: relative;
  width: 100px;
  height: 100px;
  background: linear-gradient(135deg, rgba(139, 92, 246, 0.1), rgba(167, 139, 250, 0.08));
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 1.5rem;
  border: 2px dashed rgba(139, 92, 246, 0.3);
}

.empty-tab-icon.survey {
  background: linear-gradient(135deg, rgba(6, 182, 212, 0.1), rgba(34, 211, 238, 0.08));
  border-color: rgba(6, 182, 212, 0.3);
}

.empty-tab-icon > i {
  font-size: 2.5rem;
  color: #8b5cf6;
  opacity: 0.6;
}

.empty-tab-icon.survey > i {
  color: #0891b2;
}

.empty-tab-badge {
  position: absolute;
  bottom: 0;
  right: 0;
  width: 32px;
  height: 32px;
  background: white;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  border: 2px solid rgba(245, 158, 11, 0.3);
}

.empty-tab-badge i {
  font-size: 1rem;
  color: #f59e0b;
}

.empty-tab-content h3 {
  font-size: 1.25rem;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0 0 0.5rem;
}

.empty-tab-content > p {
  font-size: 0.875rem;
  color: var(--text-secondary);
  margin: 0 0 2rem;
  line-height: 1.6;
}

.empty-tab-content > p.single-line {
  white-space: nowrap;
  max-width: none;
}

.empty-tab-features {
  display: flex;
  gap: 1rem;
  flex-wrap: wrap;
  justify-content: center;
}

.empty-tab-features .feature-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.625rem 1rem;
  background: white;
  border-radius: 30px;
  border: 1px solid rgba(139, 92, 246, 0.15);
  font-size: 0.8rem;
  color: var(--text-secondary);
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.04);
}

.empty-tab-features .feature-item i {
  font-size: 1rem;
  color: #8b5cf6;
}

.empty-tab-features.survey .feature-item {
  border-color: rgba(6, 182, 212, 0.15);
}

.empty-tab-features.survey .feature-item i {
  color: #0891b2;
}
</style>