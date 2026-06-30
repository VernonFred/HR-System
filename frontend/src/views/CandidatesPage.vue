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
import { convertRealPortraitToProfile, convertMockPortraitToProfile } from "./candidates/profileBuilders";

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

    const portraitMinTime = minProgressTime * 1.5;

    try {
      // ⭐ 使用 refresh=true 强制刷新画像（清除缓存），传递分析级别
      const [portrait] = await Promise.all([
        getCandidatePortrait(activeCandidate.value.id, true, level),
        // 确保进度条至少显示一定时间
        new Promise(resolve => setTimeout(resolve, portraitMinTime))
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

// 总页数
const totalPages = computed(() => Math.ceil(total.value / pageSize));

// 切换页码
const changePage = async (newPage: number) => {
  if (newPage < 1 || newPage > totalPages.value) return;
  page.value = newPage;
  await loadCandidates();
};

// 搜索/筛选变化时重置页码（前端过滤不需要重新加载，只在切换年份/月份时可能需要）
watch([filterYear, filterMonth], () => {
  // 前端过滤，不需要重置page，因为数据已经加载
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

<template src="./CandidatesPage.template.html"></template>


<style scoped>
@import './styles/candidates-page.css';
</style>
