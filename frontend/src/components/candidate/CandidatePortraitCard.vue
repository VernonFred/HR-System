<script setup lang="ts">
import { computed, ref, onMounted, watch } from 'vue';
import type { CandidateProfile } from '../../types/candidate';
import html2canvas from 'html2canvas';
import domtoimage from 'dom-to-image-more';
import jsPDF from 'jspdf';
import ResumeModal from '../resume/ResumeModal.vue';
import AssessmentAccordion from './AssessmentAccordion.vue';
import CompetencySection from './CompetencySection.vue';
import SummaryCard from './SummaryCard.vue';
import ScoreBreakdownModal from './ScoreBreakdownModal.vue';
import { getResumeInfo, getResumeDownloadUrl, deleteResume, parseResume } from '../../api/resumes';
import { getPortraitCacheStatus, type PortraitCacheStatus } from '../../api/candidatePortraits';

const props = withDefaults(defineProps<{ 
  profile: CandidateProfile | null;
  hideToolbar?: boolean;       // 是否隐藏工具栏（在抽屉中使用时）
  hideAssessmentList?: boolean; // 是否隐藏测评列表（在抽屉中使用时）
}>(), {
  hideToolbar: false,
  hideAssessmentList: false,
});

// 定义事件
const emit = defineEmits<{
  'portrait-regenerated': [level: 'pro' | 'expert', forceRefresh: boolean];
}>();

// 导出状态
const isExporting = ref(false);
const showExportMenu = ref(false);

// 简历状态
const showResumeModal = ref(false);
const resumeInfo = ref<any>(null);
const resumeLoading = ref(false);

// ⭐ V38: 分析级别切换状态
const currentAnalysisLevel = ref<'pro' | 'expert'>('pro');
const cacheStatus = ref<PortraitCacheStatus | null>(null);
const isLoadingCacheStatus = ref(false);
const isSwitchingLevel = ref(false);

// 消息提示状态
const toastMessage = ref('');
const toastType = ref<'success' | 'error' | 'info'>('info');
const showToast = ref(false);

// 🟢 P0+P1: 评分详情弹窗状态
const showScoreBreakdown = ref(false);

const showMessageToast = (message: string, type: 'success' | 'error' | 'info' = 'info') => {
  toastMessage.value = message;
  toastType.value = type;
  showToast.value = true;
  setTimeout(() => {
    showToast.value = false;
  }, 3000);
};

// 雷达图动画状态
const radarAnimated = ref(false);
const animatedRadarPoints = ref<string>('200,200 200,200 200,200 200,200');

// 默认模拟数据
const mockData: CandidateProfile = {
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

// 使用实际数据或模拟数据
const displayData = computed(() => props.profile || mockData);

// 处理综合评价文本（支持数组或字符串格式）
const getSummaryParagraphs = (text: string | string[] | undefined): string[] => {
  if (!text) return [];
  // 如果是数组，直接返回
  if (Array.isArray(text)) {
    return text.filter(p => p && p.trim());
  }
  // 如果是字符串，按段落拆分
  return text.split('\n\n').filter(p => p && p.trim()).map(p => p.trim());
};

// 检测是否为MBTI问卷
const isMBTI = computed(() => {
  return displayData.value.questionnaireType === 'MBTI';
});

// 检测是否为DISC问卷
const isDISC = computed(() => {
  return displayData.value.questionnaireType === 'DISC';
});

// 检测是否为EPQ问卷（默认）
const isEPQ = computed(() => {
  return !isMBTI.value && !isDISC.value;
});

// 获取DISC维度分数
const getDISCScore = (dimKey: string): number => {
  const dims = displayData.value.personalityDimensions || [];
  const dim = dims.find(d => d.key?.toUpperCase() === dimKey.toUpperCase());
  return dim?.score || 50;
};

// MBTI类型名称映射
const getMBTIName = (type: string): string => {
  const names: Record<string, string> = {
    'INTJ': '建筑师', 'INTP': '逻辑学家', 'ENTJ': '指挥官', 'ENTP': '辩论家',
    'INFJ': '提倡者', 'INFP': '调停者', 'ENFJ': '主人公', 'ENFP': '竞选者',
    'ISTJ': '物流师', 'ISFJ': '守卫者', 'ESTJ': '总经理', 'ESFJ': '执政官',
    'ISTP': '鉴赏家', 'ISFP': '探险家', 'ESTP': '企业家', 'ESFP': '表演者'
  };
  return names[type] || '';
};

// DISC类型名称映射
const getDISCName = (type: string): string => {
  const names: Record<string, string> = {
    'D型': '支配者', 'I型': '影响者', 'S型': '稳健者', 'C型': '谨慎者'
  };
  return names[type] || '';
};

// 计算人格类型信息（支持MBTI/EPQ/DISC）
const personalityTypeLabel = computed(() => {
  const dims = displayData.value.personalityDimensions || [];
  
  if (isMBTI.value) {
    // MBTI：使用mbtiType或从维度推断
    if (displayData.value.mbtiType) {
      return displayData.value.mbtiType;
    }
    // 从四个维度推断MBTI类型
    const e_i = dims.find(d => d.key === 'E-I' || d.label?.includes('外向'));
    const s_n = dims.find(d => d.key === 'S-N' || d.label?.includes('感觉'));
    const t_f = dims.find(d => d.key === 'T-F' || d.label?.includes('思考'));
    const j_p = dims.find(d => d.key === 'J-P' || d.label?.includes('判断'));
    
    let type = '';
    type += (e_i?.score ?? 50) >= 50 ? 'E' : 'I';
    type += (s_n?.score ?? 50) >= 50 ? 'S' : 'N';
    type += (t_f?.score ?? 50) >= 50 ? 'T' : 'F';
    type += (j_p?.score ?? 50) >= 50 ? 'J' : 'P';
    return type || 'INTJ';
  }
  
  if (isDISC.value) {
    // DISC：取最高分的维度
    const discDims = dims.filter(d => ['D', 'I', 'S', 'C'].includes(d.key));
    if (discDims.length > 0) {
      const maxDim = discDims.reduce((a, b) => (a.score > b.score ? a : b));
      const labels: Record<string, string> = { D: '支配型', I: '影响型', S: '稳健型', C: '谨慎型' };
      return `${maxDim.key}型`;
    }
    return 'D型';
  }
  
  // EPQ：根据E和N维度判断人格类型
  // 使用与后端一致的判断标准：T分 >= 60 为"高"，< 40 为"低"，40-60 为"中"
  const e = dims.find(d => d.key === 'E' || d.label?.includes('外向'));
  const n = dims.find(d => d.key === 'N' || d.label?.includes('神经'));
  
  const eScore = e?.score ?? 50;
  const nScore = n?.score ?? 50;
  
  // 判断水平（与后端 professional_scoring.py 保持一致）
  const eLevel = eScore >= 60 ? '高' : (eScore >= 40 ? '中' : '低');
  const nLevel = nScore >= 60 ? '高' : (nScore >= 40 ? '中' : '低');
  
  // 四种人格类型（与后端保持一致）
  if (eLevel === '高' && nLevel === '低') return '外向稳定型';
  if (eLevel === '高' && nLevel === '高') return '外向不稳定型';
  if (eLevel === '低' && nLevel === '低') return '内向稳定型';
  if (eLevel === '低' && nLevel === '高') return '内向不稳定型';
  // 中等水平的情况，根据分数倾向判断
  if (eScore >= 50 && nScore < 50) return '外向稳定型';
  if (eScore >= 50 && nScore >= 50) return '外向不稳定型';
  if (eScore < 50 && nScore < 50) return '内向稳定型';
  return '内向不稳定型';
});

// MBTI类型信息
const mbtiTypeInfo = computed(() => {
  if (!isMBTI.value || !displayData.value.mbtiType) return null;
  
  const type = displayData.value.mbtiType;
  const descriptions: Record<string, string> = {
    'INTJ': '建筑师 - 富有想象力和战略性的思考者',
    'INTP': '逻辑学家 - 创新的发明家',
    'ENTJ': '指挥官 - 大胆、富有想象力的领导者',
    'ENTP': '辩论家 - 聪明好奇的思想家',
    'INFJ': '提倡者 - 安静而神秘的理想主义者',
    'INFP': '调停者 - 诗意、善良的利他主义者',
    'ENFJ': '主人公 - 有魅力鼓舞人心的领导者',
    'ENFP': '竞选者 - 热情洋溢、富有创造力的社交家',
    'ISTJ': '物流师 - 实际而注重事实的个体',
    'ISFJ': '守卫者 - 非常专注且温暖的守护者',
    'ESTJ': '总经理 - 出色的管理者',
    'ESFJ': '执政官 - 极具同情心的善于交际者',
    'ISTP': '鉴赏家 - 大胆而实际的实验者',
    'ISFP': '探险家 - 灵活迷人的艺术家',
    'ESTP': '企业家 - 聪明、精力充沛的冒险家',
    'ESFP': '表演者 - 自发的、充满活力的演员'
  };
  
  return {
    type,
    description: descriptions[type] || type
  };
});

// 计算圆形进度
const scoreProgress = computed(() => {
  const score = displayData.value.overallMatchScore;
  const radius = 58;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (score / 100) * circumference;
  return { radius, circumference, offset };
});

// 根据分数获取颜色
const getScoreColor = (score: number) => {
  if (score >= 80) return '#10b981';
  if (score >= 60) return '#f59e0b';
  return '#ef4444';
};

// EPQ圆环图：获取每个维度的颜色
const getRingColor = (index: number) => {
  const colors = ['#6366f1', '#ec4899', '#f59e0b', '#10b981'];
  return colors[index % colors.length];
};

// EPQ圆环图：获取每个维度的图标
const getRingIcon = (key: string) => {
  const icons: Record<string, string> = {
    'E': 'ri-user-voice-line',      // 外向性
    'N': 'ri-emotion-line',         // 神经质/情绪稳定性
    'P': 'ri-star-smile-line',      // 精神质/宜人性
    'L': 'ri-shield-check-line',    // 掩饰性/尽责性
  };
  return icons[key] || 'ri-checkbox-circle-line';
};

// EPQ圆环图：获取默认描述
const getDefaultDescription = (key: string) => {
  const descriptions: Record<string, string> = {
    'E': '社交活跃度',
    'N': '情绪稳定性',
    'P': '宜人性特质',
    'L': '自律程度',
  };
  return descriptions[key] || '人格特征';
};

// 雷达图计算
const radarPoints = computed(() => {
  const dimensions = displayData.value.personalityDimensions;
  const centerX = 200;
  const centerY = 200;
  const maxRadius = 140;

  return dimensions.map((dim, i) => {
    const angle = (i * 2 * Math.PI) / dimensions.length - Math.PI / 2;
    const radius = (dim.score / 100) * maxRadius;
    const x = centerX + radius * Math.cos(angle);
    const y = centerY + radius * Math.sin(angle);
    return { x, y, ...dim };
  });
});

// 雷达图网格圈数（MBTI用4圈，其他用5圈）
const radarGridLevels = computed(() => {
  return isMBTI.value ? 4 : 5;
});

// 雷达图标签位置（MBTI特殊处理，确保4个维度均匀分布）
const radarLabels = computed(() => {
  const dimensions = displayData.value.personalityDimensions;
  const centerX = 200;
  const centerY = 200;
  const labelRadius = 175; // 增加标签距离中心的距离，避免被截断

  return dimensions.map((dim, i) => {
    const angle = (i * 2 * Math.PI) / dimensions.length - Math.PI / 2;
    const x = centerX + labelRadius * Math.cos(angle);
    const y = centerY + labelRadius * Math.sin(angle);
    
    // 根据角度调整文本锚点
    let textAnchor = 'middle';
    if (Math.abs(Math.cos(angle)) > 0.5) {
      textAnchor = Math.cos(angle) > 0 ? 'start' : 'end';
    }
    
    return { x, y, textAnchor, ...dim };
  });
});

const radarPolygonPoints = computed(() => {
  return radarPoints.value.map((p) => `${p.x},${p.y}`).join(' ');
});

// 监听profile变化，触发雷达图动画
watch(() => props.profile, (newProfile) => {
  if (newProfile) {
    // 重置动画
    radarAnimated.value = false;
    const centerPoint = '200,200 '.repeat(newProfile.personalityDimensions.length).trim();
    animatedRadarPoints.value = centerPoint;
    
    // 触发动画
    setTimeout(() => {
      radarAnimated.value = true;
      animatedRadarPoints.value = radarPolygonPoints.value;
    }, 100);
  }
}, { immediate: true });

// 组件挂载时触发初始动画
onMounted(() => {
  setTimeout(() => {
    radarAnimated.value = true;
    animatedRadarPoints.value = radarPolygonPoints.value;
  }, 300);
});

// 圆环颜色数组（与getRingColor保持一致）
const ringColors = ['#6366f1', '#ec4899', '#f59e0b', '#10b981'];

// DISC颜色
const discColors = {
  D: '#ef4444', // 红色
  I: '#f59e0b', // 黄色
  S: '#10b981', // 绿色
  C: '#3b82f6'  // 蓝色
};

// 处理克隆文档中的SVG元素，确保正确渲染
const prepareClonedDocForExport = (clonedDoc: Document) => {
  const clonedElement = clonedDoc.querySelector('.portrait-card') as HTMLElement;
  if (!clonedElement) return;
  
  // 移除transform
  clonedElement.style.transform = 'none';
  clonedElement.style.position = 'relative';
  
  // 隐藏工具栏
  const toolbar = clonedElement.querySelector('.portrait-toolbar') as HTMLElement;
  if (toolbar) toolbar.style.display = 'none';
  
  // ⭐ 方案D：导出时隐藏DOM文字，使用SVG内嵌文字（100%居中）
  // 隐藏综合匹配度的DOM文字，SVG内已有文字
  const scoreTextDom = clonedElement.querySelectorAll('.score-text-dom');
  scoreTextDom.forEach((el) => {
    (el as HTMLElement).style.display = 'none';
  });
  
  // 隐藏EPQ圆环的DOM文字（图标+分数），SVG内已有分数
  const ringCenterDom = clonedElement.querySelectorAll('.ring-center-dom');
  ringCenterDom.forEach((el) => {
    (el as HTMLElement).style.display = 'none';
  });
  
  // 移除所有 backdrop-filter
  clonedElement.querySelectorAll('*').forEach((el) => {
    const htmlEl = el as HTMLElement;
    if (htmlEl.style) {
      htmlEl.style.backdropFilter = 'none';
      htmlEl.style.webkitBackdropFilter = 'none';
    }
  });
  
  // 禁用所有CSS动画和过渡，并添加导出专用样式
  const styleEl = clonedDoc.createElement('style');
  styleEl.textContent = `
    * {
      animation: none !important;
      transition: none !important;
      -webkit-transition: none !important;
    }
    
    /* 头部区域样式 - 完整重写 */
    .header-gradient {
      position: relative !important;
      padding: 32px !important;
      background: linear-gradient(135deg, #8b5cf6, #6366f1, #3b82f6) !important;
      overflow: hidden !important;
    }
    .header-content {
      display: flex !important;
      flex-direction: row !important;
      align-items: flex-start !important;
      justify-content: space-between !important;
      gap: 32px !important;
      position: relative !important;
      z-index: 1 !important;
      width: 100% !important;
    }
    .candidate-info {
      display: flex !important;
      flex-direction: row !important;
      gap: 20px !important;
      flex: 1 !important;
      align-items: flex-start !important;
    }
    .avatar-badge {
      width: 72px !important;
      height: 72px !important;
      min-width: 72px !important;
      border-radius: 18px !important;
      background: rgba(255, 255, 255, 0.25) !important;
      display: flex !important;
      align-items: center !important;
      justify-content: center !important;
      font-size: 28px !important;
      font-weight: 700 !important;
      color: white !important;
      flex-shrink: 0 !important;
      border: 2px solid rgba(255, 255, 255, 0.3) !important;
    }
    .info-text {
      display: flex !important;
      flex-direction: column !important;
      align-items: flex-start !important;
      gap: 10px !important;
      flex: 1 !important;
    }
    .name-row {
      display: flex !important;
      flex-direction: row !important;
      align-items: center !important;
      justify-content: flex-start !important;
      gap: 14px !important;
      flex-wrap: wrap !important;
    }
    .name {
      font-size: 28px !important;
      font-weight: 700 !important;
      color: white !important;
      margin: 0 !important;
      line-height: 1.2 !important;
    }
    .personality-badge {
      display: inline-flex !important;
      flex-direction: row !important;
      align-items: center !important;
      gap: 6px !important;
      padding: 6px 14px !important;
      border-radius: 20px !important;
      font-size: 13px !important;
      font-weight: 600 !important;
      color: white !important;
      white-space: nowrap !important;
    }
    .personality-badge.epq {
      background: linear-gradient(135deg, #06b6d4, #14b8a6) !important;
    }
    .personality-badge.mbti {
      background: linear-gradient(135deg, #8b5cf6, #6366f1) !important;
    }
    .personality-badge.disc {
      background: linear-gradient(135deg, #f97316, #ea580c) !important;
    }
    .meta-row {
      display: flex !important;
      flex-direction: row !important;
      align-items: center !important;
      justify-content: flex-start !important;
      gap: 8px !important;
      color: rgba(255, 255, 255, 0.9) !important;
      font-size: 14px !important;
    }
    .meta-item {
      display: inline-flex !important;
      flex-direction: row !important;
      align-items: center !important;
      gap: 6px !important;
    }
    .meta-item i {
      font-size: 16px !important;
    }
    .meta-divider {
      color: rgba(255, 255, 255, 0.5) !important;
    }
    .tags-row {
      display: flex !important;
      flex-direction: row !important;
      justify-content: flex-start !important;
      flex-wrap: wrap !important;
      gap: 8px !important;
      margin-top: 6px !important;
    }
    .tag-pill {
      display: inline-flex !important;
      padding: 6px 14px !important;
      background: rgba(255, 255, 255, 0.18) !important;
      border-radius: 18px !important;
      font-size: 13px !important;
      color: white !important;
      white-space: nowrap !important;
    }
    .score-circle-wrapper {
      flex-shrink: 0 !important;
      position: relative !important;
      width: 130px !important;
      height: 130px !important;
      display: flex !important;
      align-items: center !important;
      justify-content: center !important;
    }
    .score-svg {
      width: 130px !important;
      height: 130px !important;
      position: absolute !important;
      top: 0 !important;
      left: 0 !important;
    }
    /* 导出时隐藏DOM文字，显示SVG文字 */
    .score-text-dom {
      display: none !important;
    }
    .ring-center-dom {
      display: none !important;
    }
    .score-svg-value, .score-svg-label, .ring-svg-score {
      display: block !important;
    }
    .score-text {
      position: relative !important;
      z-index: 2 !important;
      text-align: center !important;
      display: flex !important;
      flex-direction: column !important;
      align-items: center !important;
      justify-content: center !important;
      margin-top: 0 !important;
      margin-left: 0 !important;
      padding: 0 !important;
    }
    .score-value {
      font-size: 36px !important;
      font-weight: 700 !important;
      color: white !important;
      line-height: 1 !important;
      margin: 0 !important;
    }
    .score-label {
      font-size: 12px !important;
      color: rgba(255, 255, 255, 0.8) !important;
      margin-top: 4px !important;
      margin-bottom: 0 !important;
    }
    
    /* EPQ 圆环图样式 - 完整重写 */
    .epq-rings-container {
      display: grid !important;
      grid-template-columns: repeat(2, 1fr) !important;
      gap: 24px !important;
      padding: 20px !important;
    }
    .epq-ring-item {
      display: flex !important;
      flex-direction: column !important;
      align-items: center !important;
      text-align: center !important;
    }
    .ring-wrapper {
      width: 120px !important;
      height: 120px !important;
      position: relative !important;
      display: flex !important;
      align-items: center !important;
      justify-content: center !important;
    }
    .ring-svg {
      width: 120px !important;
      height: 120px !important;
      position: absolute !important;
      top: 0 !important;
      left: 0 !important;
    }
    .ring-center {
      position: relative !important;
      z-index: 2 !important;
      display: flex !important;
      flex-direction: column !important;
      align-items: center !important;
      justify-content: center !important;
      text-align: center !important;
      margin: 0 !important;
      padding: 0 !important;
    }
    .ring-icon {
      font-size: 20px !important;
      margin-bottom: 2px !important;
      margin-top: 0 !important;
    }
    .ring-score {
      font-size: 24px !important;
      font-weight: 700 !important;
      color: #374151 !important;
      line-height: 1 !important;
      margin: 0 !important;
    }
    }
    .ring-label {
      font-size: 14px !important;
      font-weight: 600 !important;
      color: #374151 !important;
      margin-top: 10px !important;
    }
    .ring-desc {
      font-size: 12px !important;
      color: #6b7280 !important;
      margin-top: 4px !important;
      max-width: 140px !important;
      line-height: 1.4 !important;
    }
    .ring-progress, .progress-circle {
      transition: none !important;
    }
    
    /* 旧版兼容 */
    .personality-grid {
      display: grid !important;
      grid-template-columns: repeat(2, 1fr) !important;
      gap: 20px !important;
    }
    .dim-card {
      display: flex !important;
      flex-direction: column !important;
      align-items: center !important;
      padding: 16px !important;
    }
    
    /* MBTI 进度条样式 */
    .mbti-quadrant-container {
      display: flex !important;
      flex-direction: column !important;
      gap: 16px !important;
      padding: 24px !important;
      width: 100% !important;
    }
    .mbti-dimension {
      display: flex !important;
      flex-direction: column !important;
      gap: 8px !important;
      width: 100% !important;
    }
    .mbti-dimension-header {
      display: flex !important;
      justify-content: space-between !important;
      align-items: center !important;
    }
    .dimension-label {
      font-weight: 600 !important;
      color: #374151 !important;
    }
    .dimension-score {
      font-weight: 700 !important;
      color: #6366f1 !important;
    }
    .mbti-bar-container {
      width: 100% !important;
    }
    .mbti-bar-track {
      height: 12px !important;
      background: #e5e7eb !important;
      border-radius: 6px !important;
      overflow: hidden !important;
      position: relative !important;
    }
    .mbti-bar-fill {
      height: 100% !important;
      border-radius: 6px !important;
      background: linear-gradient(90deg, #8b5cf6, #6366f1) !important;
    }
    .mbti-bar-labels {
      display: flex !important;
      justify-content: space-between !important;
      margin-top: 4px !important;
      font-size: 12px !important;
      color: #6b7280 !important;
    }
    .mbti-center-marker {
      display: none !important;
    }
    .mbti-bar-glow {
      display: none !important;
    }
    
    /* DISC 四象限样式 */
    .disc-quadrant-container {
      padding: 16px !important;
    }
    .disc-quadrant {
      display: grid !important;
      grid-template-columns: repeat(2, 1fr) !important;
      gap: 16px !important;
    }
    .disc-item {
      display: flex !important;
      flex-direction: column !important;
      align-items: center !important;
      padding: 16px !important;
      border-radius: 12px !important;
    }
    .disc-icon {
      width: 48px !important;
      height: 48px !important;
      border-radius: 50% !important;
      display: flex !important;
      align-items: center !important;
      justify-content: center !important;
      font-size: 24px !important;
    }
    .disc-bar {
      width: 100% !important;
      height: 8px !important;
      background: rgba(0,0,0,0.1) !important;
      border-radius: 4px !important;
      overflow: hidden !important;
    }
    .disc-bar-fill {
      height: 100% !important;
      border-radius: 4px !important;
    }
    
    /* 进度条样式 */
    .progress-track {
      height: 8px !important;
      background: #e5e7eb !important;
      border-radius: 4px !important;
      overflow: hidden !important;
    }
    .progress-bar {
      height: 100% !important;
      border-radius: 4px !important;
    }
    
    /* 综合匹配度圆环 */
    .score-svg {
      width: 110px !important;
      height: 110px !important;
    }
  `;
  clonedDoc.head.appendChild(styleEl);
  
  // ========== 处理头部区域 ==========
  const headerGradient = clonedElement.querySelector('.header-gradient') as HTMLElement;
  if (headerGradient) {
    headerGradient.style.padding = '32px';
    headerGradient.style.position = 'relative';
  }
  
  const headerContent = clonedElement.querySelector('.header-content') as HTMLElement;
  if (headerContent) {
    headerContent.style.display = 'flex';
    headerContent.style.flexDirection = 'row';
    headerContent.style.alignItems = 'flex-start';
    headerContent.style.justifyContent = 'space-between';
    headerContent.style.gap = '32px';
    headerContent.style.width = '100%';
  }
  
  const candidateInfo = clonedElement.querySelector('.candidate-info') as HTMLElement;
  if (candidateInfo) {
    candidateInfo.style.display = 'flex';
    candidateInfo.style.flexDirection = 'row';
    candidateInfo.style.gap = '20px';
    candidateInfo.style.flex = '1';
    candidateInfo.style.alignItems = 'flex-start';
  }
  
  const avatarBadge = clonedElement.querySelector('.avatar-badge') as HTMLElement;
  if (avatarBadge) {
    avatarBadge.style.width = '72px';
    avatarBadge.style.height = '72px';
    avatarBadge.style.minWidth = '72px';
    avatarBadge.style.borderRadius = '18px';
    avatarBadge.style.display = 'flex';
    avatarBadge.style.alignItems = 'center';
    avatarBadge.style.justifyContent = 'center';
    avatarBadge.style.flexShrink = '0';
    avatarBadge.style.background = 'rgba(255, 255, 255, 0.25)';
    avatarBadge.style.border = '2px solid rgba(255, 255, 255, 0.3)';
  }
  
  const infoText = clonedElement.querySelector('.info-text') as HTMLElement;
  if (infoText) {
    infoText.style.display = 'flex';
    infoText.style.flexDirection = 'column';
    infoText.style.alignItems = 'flex-start'; // 左对齐
    infoText.style.gap = '10px';
    infoText.style.flex = '1';
  }
  
  const nameRow = clonedElement.querySelector('.name-row') as HTMLElement;
  if (nameRow) {
    nameRow.style.display = 'flex';
    nameRow.style.flexDirection = 'row';
    nameRow.style.alignItems = 'center';
    nameRow.style.justifyContent = 'flex-start'; // 左对齐
    nameRow.style.gap = '14px';
    nameRow.style.flexWrap = 'wrap';
  }
  
  const metaRow = clonedElement.querySelector('.meta-row') as HTMLElement;
  if (metaRow) {
    metaRow.style.display = 'flex';
    metaRow.style.flexDirection = 'row';
    metaRow.style.alignItems = 'center';
    metaRow.style.justifyContent = 'flex-start'; // 左对齐
    metaRow.style.gap = '8px';
  }
  
  const tagsRow = clonedElement.querySelector('.tags-row') as HTMLElement;
  if (tagsRow) {
    tagsRow.style.display = 'flex';
    tagsRow.style.flexDirection = 'row';
    tagsRow.style.justifyContent = 'flex-start'; // 左对齐
    tagsRow.style.flexWrap = 'wrap';
    tagsRow.style.gap = '8px';
  }
  
  const scoreWrapper = clonedElement.querySelector('.score-circle-wrapper') as HTMLElement;
  if (scoreWrapper) {
    scoreWrapper.style.flexShrink = '0';
    scoreWrapper.style.position = 'relative';
    scoreWrapper.style.width = '130px';
    scoreWrapper.style.height = '130px';
    scoreWrapper.style.display = 'flex';
    scoreWrapper.style.alignItems = 'center';
    scoreWrapper.style.justifyContent = 'center';
  }
  
  const scoreSvgHeader = scoreWrapper?.querySelector('.score-svg') as SVGElement;
  if (scoreSvgHeader) {
    scoreSvgHeader.setAttribute('width', '130');
    scoreSvgHeader.setAttribute('height', '130');
    scoreSvgHeader.style.width = '130px';
    scoreSvgHeader.style.height = '130px';
    scoreSvgHeader.style.position = 'absolute';
    scoreSvgHeader.style.top = '0';
    scoreSvgHeader.style.left = '0';
  }
  
  const scoreText = clonedElement.querySelector('.score-text') as HTMLElement;
  if (scoreText) {
    // 使用绝对定位确保文字在圆环正中间
    scoreText.style.position = 'absolute';
    scoreText.style.top = '50%';
    scoreText.style.left = '50%';
    scoreText.style.transform = 'translate(-50%, -50%)';
    scoreText.style.zIndex = '2';
    scoreText.style.textAlign = 'center';
    scoreText.style.display = 'flex';
    scoreText.style.flexDirection = 'column';
    scoreText.style.alignItems = 'center';
    scoreText.style.justifyContent = 'center';
    scoreText.style.width = '100%';
  }
  
  const scoreValue = clonedElement.querySelector('.score-value') as HTMLElement;
  if (scoreValue) {
    scoreValue.style.fontSize = '36px';
    scoreValue.style.fontWeight = '700';
    scoreValue.style.color = 'white';
    scoreValue.style.lineHeight = '1';
  }
  
  const scoreLabel = clonedElement.querySelector('.score-label') as HTMLElement;
  if (scoreLabel) {
    scoreLabel.style.fontSize = '12px';
    scoreLabel.style.color = 'rgba(255, 255, 255, 0.8)';
    scoreLabel.style.marginTop = '4px';
  }
  
  // ========== 处理 EPQ 圆环图容器 ==========
  const epqContainer = clonedElement.querySelector('.epq-rings-container') as HTMLElement;
  if (epqContainer) {
    epqContainer.style.display = 'grid';
    epqContainer.style.gridTemplateColumns = 'repeat(2, 1fr)';
    epqContainer.style.gap = '24px';
    epqContainer.style.padding = '20px';
  }
  
  // 处理每个EPQ圆环项
  clonedElement.querySelectorAll('.epq-ring-item').forEach((item) => {
    const itemEl = item as HTMLElement;
    itemEl.style.display = 'flex';
    itemEl.style.flexDirection = 'column';
    itemEl.style.alignItems = 'center';
    itemEl.style.textAlign = 'center';
    
    const ringWrapper = item.querySelector('.ring-wrapper') as HTMLElement;
    if (ringWrapper) {
      ringWrapper.style.width = '120px';
      ringWrapper.style.height = '120px';
      ringWrapper.style.position = 'relative';
      ringWrapper.style.display = 'flex';
      ringWrapper.style.alignItems = 'center';
      ringWrapper.style.justifyContent = 'center';
    }
    
    const ringSvg = item.querySelector('.ring-svg') as SVGElement;
    if (ringSvg) {
      ringSvg.setAttribute('width', '120');
      ringSvg.setAttribute('height', '120');
      ringSvg.style.width = '120px';
      ringSvg.style.height = '120px';
      // 使用绝对定位让SVG覆盖整个wrapper
      ringSvg.style.position = 'absolute';
      ringSvg.style.top = '0';
      ringSvg.style.left = '0';
    }
    
    const ringCenter = item.querySelector('.ring-center') as HTMLElement;
    if (ringCenter) {
      // 使用绝对定位确保内容在圆环正中间
      ringCenter.style.position = 'absolute';
      ringCenter.style.top = '50%';
      ringCenter.style.left = '50%';
      ringCenter.style.transform = 'translate(-50%, -50%)';
      ringCenter.style.zIndex = '2';
      ringCenter.style.display = 'flex';
      ringCenter.style.flexDirection = 'column';
      ringCenter.style.alignItems = 'center';
      ringCenter.style.justifyContent = 'center';
      ringCenter.style.textAlign = 'center';
      ringCenter.style.width = '80px'; // 设置固定宽度确保内容居中
    }
    
    const ringIcon = item.querySelector('.ring-icon') as HTMLElement;
    if (ringIcon) {
      ringIcon.style.fontSize = '20px';
      ringIcon.style.marginBottom = '2px';
      ringIcon.style.lineHeight = '1';
    }
    
    const ringScore = item.querySelector('.ring-score') as HTMLElement;
    if (ringScore) {
      ringScore.style.fontSize = '28px';
      ringScore.style.fontWeight = '700';
      ringScore.style.color = '#374151';
      ringScore.style.lineHeight = '1';
    }
    
    const ringLabel = item.querySelector('.ring-label') as HTMLElement;
    if (ringLabel) {
      ringLabel.style.fontSize = '14px';
      ringLabel.style.fontWeight = '600';
      ringLabel.style.color = '#374151';
      ringLabel.style.marginTop = '10px';
    }
    
    const ringDesc = item.querySelector('.ring-desc') as HTMLElement;
    if (ringDesc) {
      ringDesc.style.fontSize = '12px';
      ringDesc.style.color = '#6b7280';
      ringDesc.style.marginTop = '4px';
    }
  });
  
  // ========== 处理 EPQ 圆环进度条的渐变 ==========
  clonedElement.querySelectorAll('.epq-ring-item').forEach((item, index) => {
    const progressCircle = item.querySelector('.ring-progress') as SVGCircleElement;
    if (progressCircle) {
      const color = ringColors[index % ringColors.length];
      // 移除渐变引用，使用纯色
      progressCircle.setAttribute('stroke', color);
      progressCircle.style.stroke = color;
      progressCircle.style.transition = 'none';
    }
  });
  
  // 兼容旧版dim-card结构
  clonedElement.querySelectorAll('.dim-card').forEach((card, index) => {
    const cardEl = card as HTMLElement;
    cardEl.style.display = 'flex';
    cardEl.style.flexDirection = 'column';
    cardEl.style.alignItems = 'center';
    
    const progressCircle = card.querySelector('circle[stroke-dasharray]') as SVGCircleElement;
    if (progressCircle) {
      const color = ringColors[index % ringColors.length];
      progressCircle.setAttribute('stroke', color);
      progressCircle.style.stroke = color;
      progressCircle.style.transition = 'none';
    }
  });
  
  // ========== 处理 MBTI 进度条 ==========
  const mbtiContainer = clonedElement.querySelector('.mbti-quadrant-container') as HTMLElement;
  if (mbtiContainer) {
    mbtiContainer.style.display = 'flex';
    mbtiContainer.style.flexDirection = 'column';
    mbtiContainer.style.gap = '16px';
    mbtiContainer.style.padding = '24px';
    mbtiContainer.style.width = '100%';
  }
  
  clonedElement.querySelectorAll('.mbti-dimension').forEach((dim) => {
    const dimEl = dim as HTMLElement;
    dimEl.style.display = 'flex';
    dimEl.style.flexDirection = 'column';
    dimEl.style.gap = '8px';
    dimEl.style.width = '100%';
    
    const header = dim.querySelector('.mbti-dimension-header') as HTMLElement;
    if (header) {
      header.style.display = 'flex';
      header.style.justifyContent = 'space-between';
      header.style.alignItems = 'center';
    }
    
    const barContainer = dim.querySelector('.mbti-bar-container') as HTMLElement;
    if (barContainer) {
      barContainer.style.width = '100%';
    }
    
    const barTrack = dim.querySelector('.mbti-bar-track') as HTMLElement;
    if (barTrack) {
      barTrack.style.height = '12px';
      barTrack.style.background = '#e5e7eb';
      barTrack.style.borderRadius = '6px';
      barTrack.style.overflow = 'hidden';
      barTrack.style.position = 'relative';
    }
    
    const barFill = dim.querySelector('.mbti-bar-fill') as HTMLElement;
    if (barFill) {
      // 确保进度条填充正确显示
      const computedWidth = window.getComputedStyle(barFill).width;
      barFill.style.width = computedWidth;
      barFill.style.background = 'linear-gradient(90deg, #8b5cf6, #6366f1)';
      barFill.style.height = '100%';
      barFill.style.borderRadius = '6px';
      barFill.style.transition = 'none';
    }
    
    const barLabels = dim.querySelector('.mbti-bar-labels') as HTMLElement;
    if (barLabels) {
      barLabels.style.display = 'flex';
      barLabels.style.justifyContent = 'space-between';
      barLabels.style.marginTop = '4px';
      barLabels.style.fontSize = '12px';
      barLabels.style.color = '#6b7280';
    }
    
    // 隐藏动画元素
    const glow = dim.querySelector('.mbti-bar-glow') as HTMLElement;
    if (glow) glow.style.display = 'none';
    
    const marker = dim.querySelector('.mbti-center-marker') as HTMLElement;
    if (marker) marker.style.display = 'none';
  });
  
  // ========== 处理 DISC 四象限 ==========
  const discContainer = clonedElement.querySelector('.disc-quadrant-container') as HTMLElement;
  if (discContainer) {
    discContainer.style.padding = '16px';
  }
  
  const discQuadrant = clonedElement.querySelector('.disc-quadrant') as HTMLElement;
  if (discQuadrant) {
    discQuadrant.style.display = 'grid';
    discQuadrant.style.gridTemplateColumns = 'repeat(2, 1fr)';
    discQuadrant.style.gap = '16px';
  }
  
  clonedElement.querySelectorAll('.disc-item').forEach((item) => {
    const itemEl = item as HTMLElement;
    itemEl.style.display = 'flex';
    itemEl.style.flexDirection = 'column';
    itemEl.style.alignItems = 'center';
    itemEl.style.padding = '16px';
    itemEl.style.borderRadius = '12px';
    
    // 根据类名设置背景色
    if (itemEl.classList.contains('disc-d')) {
      itemEl.style.background = 'rgba(239, 68, 68, 0.1)';
    } else if (itemEl.classList.contains('disc-i')) {
      itemEl.style.background = 'rgba(245, 158, 11, 0.1)';
    } else if (itemEl.classList.contains('disc-s')) {
      itemEl.style.background = 'rgba(16, 185, 129, 0.1)';
    } else if (itemEl.classList.contains('disc-c')) {
      itemEl.style.background = 'rgba(59, 130, 246, 0.1)';
    }
    
    const icon = item.querySelector('.disc-icon') as HTMLElement;
    if (icon) {
      icon.style.width = '48px';
      icon.style.height = '48px';
      icon.style.borderRadius = '50%';
      icon.style.display = 'flex';
      icon.style.alignItems = 'center';
      icon.style.justifyContent = 'center';
      icon.style.fontSize = '24px';
    }
    
    const bar = item.querySelector('.disc-bar') as HTMLElement;
    if (bar) {
      bar.style.width = '100%';
      bar.style.height = '8px';
      bar.style.background = 'rgba(0,0,0,0.1)';
      bar.style.borderRadius = '4px';
      bar.style.overflow = 'hidden';
    }
    
    const barFill = item.querySelector('.disc-bar-fill') as HTMLElement;
    if (barFill) {
      const computedWidth = window.getComputedStyle(barFill).width;
      const computedBg = window.getComputedStyle(barFill).background;
      barFill.style.width = computedWidth;
      barFill.style.background = computedBg;
      barFill.style.height = '100%';
      barFill.style.borderRadius = '4px';
      barFill.style.transition = 'none';
    }
  });
  
  // ========== 处理综合匹配度圆环 ==========
  const scoreSvg = clonedElement.querySelector('.score-svg') as SVGElement;
  if (scoreSvg) {
    scoreSvg.setAttribute('width', '136');
    scoreSvg.setAttribute('height', '136');
    scoreSvg.style.width = '110px';
    scoreSvg.style.height = '110px';
    
    const progressCircle = scoreSvg.querySelector('.progress-circle') as SVGCircleElement;
    if (progressCircle) {
      // 获取计算后的stroke-dashoffset
      const computedStyle = window.getComputedStyle(progressCircle);
      const dashOffset = computedStyle.strokeDashoffset;
      const dashArray = computedStyle.strokeDasharray;
      
      progressCircle.style.strokeDashoffset = dashOffset;
      progressCircle.style.strokeDasharray = dashArray;
      progressCircle.style.transition = 'none';
      
      // 使用渐变色或纯色
      const strokeAttr = progressCircle.getAttribute('stroke');
      if (strokeAttr && strokeAttr.includes('url(')) {
        progressCircle.setAttribute('stroke', '#f59e0b');
        progressCircle.style.stroke = '#f59e0b';
      }
    }
  }
  
  // ========== 处理所有SVG ==========
  clonedElement.querySelectorAll('svg').forEach((svg) => {
    const rect = svg.getBoundingClientRect();
    if (rect.width > 0 && !svg.getAttribute('width')) {
      svg.setAttribute('width', Math.ceil(rect.width).toString());
    }
    if (rect.height > 0 && !svg.getAttribute('height')) {
      svg.setAttribute('height', Math.ceil(rect.height).toString());
    }
    
    // 处理所有圆形元素
    svg.querySelectorAll('circle').forEach((circle) => {
      const strokeAttr = circle.getAttribute('stroke');
      if (strokeAttr && strokeAttr.includes('url(')) {
        // 尝试从渐变ID推断颜色
        if (strokeAttr.includes('scoreGradient')) {
          circle.setAttribute('stroke', '#f59e0b');
        } else if (strokeAttr.includes('ringGradient-0')) {
          circle.setAttribute('stroke', ringColors[0]);
        } else if (strokeAttr.includes('ringGradient-1')) {
          circle.setAttribute('stroke', ringColors[1]);
        } else if (strokeAttr.includes('ringGradient-2')) {
          circle.setAttribute('stroke', ringColors[2]);
        } else if (strokeAttr.includes('ringGradient-3')) {
          circle.setAttribute('stroke', ringColors[3]);
        } else {
          circle.setAttribute('stroke', '#6366f1');
        }
      }
      circle.style.transition = 'none';
    });
  });
  
  // ========== 处理胜任力进度条 ==========
  clonedElement.querySelectorAll('.progress-bar').forEach((bar) => {
    const barEl = bar as HTMLElement;
    const computedWidth = window.getComputedStyle(barEl).width;
    const computedBg = window.getComputedStyle(barEl).background;
    barEl.style.width = computedWidth;
    barEl.style.background = computedBg;
    barEl.style.transition = 'none';
  });
};

// 导出功能（使用 dom-to-image-more）
const exportAsPNG = async () => {
  if (!props.profile) return;
  
  isExporting.value = true;
  showExportMenu.value = false;
  
  try {
    // 等待DOM和动画完成
    await new Promise(resolve => setTimeout(resolve, 500));
    
    const element = document.querySelector('.portrait-card') as HTMLElement;
    if (!element) {
      console.error('找不到 .portrait-card 元素');
      alert('导出失败：找不到画像元素');
      return;
    }
    
    console.log('开始导出PNG（使用 dom-to-image-more），元素尺寸:', element.offsetWidth, 'x', element.offsetHeight);
    
    // 使用 dom-to-image-more 替代 html2canvas
    const dataUrl = await domtoimage.toPng(element, {
      width: element.offsetWidth,
      height: element.offsetHeight,
      style: {
        transform: 'scale(1)',
        transformOrigin: 'top left'
      },
      quality: 1.0,
      bgcolor: '#f8fafc'
    });
    
    console.log('图片生成成功');
    
    const link = document.createElement('a');
    // 文件名包含分析级别
    const levelLabel = currentAnalysisLevel.value === 'expert' ? '专家分析' : '深度分析';
    link.download = `候选人画像-${displayData.value.name}-${levelLabel}-${Date.now()}.png`;
    link.href = dataUrl;
    link.click();
    
    console.log(`PNG导出成功 (${levelLabel})`);
  } catch (error) {
    console.error('导出PNG失败:', error);
    alert('导出失败，请重试。错误信息：' + (error as Error).message);
  } finally {
    isExporting.value = false;
  }
};

const exportAsPDF = async () => {
  if (!props.profile) return;
  
  isExporting.value = true;
  showExportMenu.value = false;
  
  try {
    // 等待DOM和动画完成
    await new Promise(resolve => setTimeout(resolve, 500));
    
    const element = document.querySelector('.portrait-card') as HTMLElement;
    if (!element) {
      console.error('找不到 .portrait-card 元素');
      alert('导出失败：找不到画像元素');
      return;
    }
    
    console.log('开始导出PDF（使用 dom-to-image-more），元素尺寸:', element.offsetWidth, 'x', element.offsetHeight);
    
    // 使用 dom-to-image-more 生成图片
    const imgData = await domtoimage.toPng(element, {
      width: element.offsetWidth,
      height: element.offsetHeight,
      style: {
        transform: 'scale(1)',
        transformOrigin: 'top left'
      },
      quality: 1.0,
      bgcolor: '#f8fafc'
    });
    
    console.log('PDF 图片生成成功');
    
    // 创建临时图片以获取尺寸
    const tempImg = new Image();
    tempImg.src = imgData;
    await new Promise((resolve) => {
      tempImg.onload = resolve;
    });
    
    const imgWidth = tempImg.width;
    const imgHeight = tempImg.height;
    
    // A4 尺寸：210mm x 297mm
    const pageWidth = 210;
    const pageHeight = 297;
    const margin = 5; // 页边距
    const contentWidth = pageWidth - 2 * margin;
    
    // 计算图片在PDF中的尺寸（基于实际图片尺寸）
    const pdfImgWidth = contentWidth;
    const pdfImgHeight = (imgHeight * pdfImgWidth) / imgWidth;
    
    // 创建PDF，根据内容高度决定是否需要多页
    const pdf = new jsPDF({
      orientation: 'portrait',
      unit: 'mm',
      format: 'a4',
    });
    
    // 如果内容超过一页，需要分页处理
    const contentHeight = pageHeight - 2 * margin;
    if (pdfImgHeight <= contentHeight) {
      // 内容可以放在一页
      pdf.addImage(imgData, 'PNG', margin, margin, pdfImgWidth, pdfImgHeight);
    } else {
      // 需要多页 - 使用简化的分页方式
      const totalPages = Math.ceil(pdfImgHeight / contentHeight);
      console.log(`PDF需要 ${totalPages} 页，每页高度 ${contentHeight}mm，总高度 ${pdfImgHeight}mm`);
      
      for (let pageNum = 0; pageNum < totalPages; pageNum++) {
        if (pageNum > 0) {
          pdf.addPage();
        }
        
        // 计算当前页应该截取的高度
        const remainingImgHeight = pdfImgHeight - (pageNum * contentHeight);
        const heightOnPage = Math.min(contentHeight, remainingImgHeight);
        
        console.log(`第 ${pageNum + 1} 页: heightOnPage=${heightOnPage}`);
        
        // 使用图片偏移的方式添加到PDF（简化分页）
        const yOffset = -(pageNum * contentHeight);
        pdf.addImage(imgData, 'PNG', margin, margin + yOffset, pdfImgWidth, pdfImgHeight);
      }
    }
    
    // 文件名包含分析级别
    const levelLabel = currentAnalysisLevel.value === 'expert' ? '专家分析' : '深度分析';
    pdf.save(`候选人画像-${displayData.value.name}-${levelLabel}-${Date.now()}.pdf`);
    console.log(`PDF导出成功 (${levelLabel})`);
  } catch (error) {
    console.error('导出PDF失败:', error);
    alert('导出失败，请重试。错误信息：' + (error as Error).message);
  } finally {
    isExporting.value = false;
  }
};

const exportAsWord = () => {
  if (!props.profile) return;
  
  showExportMenu.value = false;
  alert('Word导出功能开发中，敬请期待！\n建议使用 PDF 格式导出。');
};

// ========== 简历相关函数 ==========

const hasResume = computed(() => {
  return resumeInfo.value?.has_resume || false;
});

const openResumeModal = async () => {
  if (!props.profile?.id) return;
  
  showResumeModal.value = true;
  
  // 加载简历信息
  await loadResumeInfo(props.profile.id);
};

const loadResumeInfo = async (candidateId: string | number) => {
  resumeLoading.value = true;
  try {
    const info = await getResumeInfo(Number(candidateId));
    resumeInfo.value = info;
  } catch (error) {
    console.error('加载简历信息失败:', error);
    resumeInfo.value = null;
  } finally {
    resumeLoading.value = false;
  }
};

const handleResumeUploaded = async (data: any) => {
  console.log('简历上传成功:', data);
  // 重新加载简历信息
  if (props.profile?.id) {
    await loadResumeInfo(props.profile.id);
  }
};

const handleResumeError = (error: string) => {
  showMessageToast(`上传失败: ${error}`, 'error');
};

const handleDownloadResume = () => {
  if (props.profile?.id) {
    const url = getResumeDownloadUrl(Number(props.profile.id));
    window.open(url, '_blank');
  }
};

// 删除简历确认弹窗状态
const showDeleteResumeConfirm = ref(false);

const handleDeleteResume = async () => {
  showDeleteResumeConfirm.value = true;
};

const confirmDeleteResume = async () => {
  if (!props.profile?.id) return;
  
    try {
      await deleteResume(Number(props.profile.id));
    showMessageToast('简历已删除', 'success');
    showDeleteResumeConfirm.value = false;
      // 重新加载简历信息
      await loadResumeInfo(props.profile.id);
    } catch (error: any) {
    showMessageToast(`删除失败: ${error.response?.data?.detail || error.message}`, 'error');
  }
};

const cancelDeleteResume = () => {
  showDeleteResumeConfirm.value = false;
};

// 解析简历（带分析级别）
const handleParseResume = async (level: 'pro' | 'expert' = 'pro') => {
  if (!props.profile?.id) return;
  
  try {
    console.log(`📄 开始解析简历 (level=${level})`);
    const result = await parseResume(Number(props.profile.id), level);
    // 解析成功后重新加载简历信息（会触发 ResumeModal 的 watch 检测解析完成）
    await loadResumeInfo(props.profile.id);
    console.log(`✅ 简历解析完成 (level=${level})`);
  } catch (error: any) {
    showMessageToast(`解析失败: ${error.response?.data?.detail || error.message}`, 'error');
  }
};

// 解析完成回调（带分析级别，自动触发画像生成）
const handleParseComplete = (level: 'pro' | 'expert' = 'pro') => {
  console.log(`✅ 简历解析完成，准备生成画像 (level=${level})`);
  // 解析完成后自动触发画像生成
  regeneratePortrait(level);
};

// ⭐ 重新生成画像功能
const isRegeneratingPortrait = ref(false);

const regeneratePortrait = (level: 'pro' | 'expert' = 'pro') => {
  if (!props.profile?.id) return;
  
  // 保存当前分析级别
  currentAnalysisLevel.value = level;
  
  // 设置加载状态（按钮显示加载中）
    isRegeneratingPortrait.value = true;
    
    // 关闭简历弹窗
    showResumeModal.value = false;
    
  // 触发父组件重新生成画像（由父组件负责调用API和显示进度条动画）
  // 传递分析级别给父组件，简历解析后需要强制刷新
  emit('portrait-regenerated', level, true); // forceRefresh = true
  
  // 注意：isRegeneratingPortrait 会在父组件完成后自动重置
  // 这里延迟重置，确保弹窗关闭动画完成
  setTimeout(() => {
    isRegeneratingPortrait.value = false;
  }, 500);
};

// ⭐ V38: 加载缓存状态
const loadCacheStatus = async () => {
  if (!props.profile?.id) return;
  
  isLoadingCacheStatus.value = true;
  try {
    cacheStatus.value = await getPortraitCacheStatus(Number(props.profile.id));
    console.log('📦 缓存状态:', cacheStatus.value);
  } catch (error) {
    console.error('获取缓存状态失败:', error);
  } finally {
    isLoadingCacheStatus.value = false;
  }
};

// ⭐ V38: 切换分析级别（使用缓存或重新生成）
const switchAnalysisLevel = async (level: 'pro' | 'expert') => {
  if (!props.profile?.id || level === currentAnalysisLevel.value) return;
  
  isSwitchingLevel.value = true;
  currentAnalysisLevel.value = level;
  
  // 检查是否有缓存
  const hasCached = cacheStatus.value?.cached_levels[level];
  
  if (hasCached) {
    // 有缓存，直接切换（不需要强制刷新，从缓存加载）
    console.log(`🔄 切换到${level}（使用缓存，forceRefresh=false）`);
    emit('portrait-regenerated', level, false); // forceRefresh = false
    setTimeout(() => {
      isSwitchingLevel.value = false;
    }, 500);
  } else {
    // 无缓存，需要重新生成
    console.log(`🔄 切换到${level}（需要生成，forceRefresh=true）`);
    emit('portrait-regenerated', level, true); // forceRefresh = true
    // 生成完成后更新缓存状态
    setTimeout(async () => {
      await loadCacheStatus();
      isSwitchingLevel.value = false;
    }, 3000);
  }
};

// 监听 profile 变化，加载缓存状态
watch(() => props.profile?.id, async (newId) => {
  if (newId) {
    await loadCacheStatus();
  }
}, { immediate: true });

// 🟢 P0优化：新增 computed
const currentAssessmentType = computed(() => {
  if (isMBTI.value) return 'MBTI'
  if (isDISC.value) return 'DISC'
  if (isEPQ.value) return 'EPQ'
  return '未知'
})

const assessmentCount = computed(() => {
  return displayData.value.assessments?.length || 0
})

// 🟢 P1-2: 重新生成AI分析
const handleRetryAI = () => {
  if (!props.profile?.id) return
  
  showMessageToast('正在重新生成AI分析...', 'info')
  
  // 强制刷新，跳过缓存
  emit('portrait-regenerated', currentAnalysisLevel.value, true)
}

</script>

<template>
  <div class="portrait-wrapper">
    <!-- 空状态 -->
    <div v-if="!profile" class="empty-state">
      <i class="ri-user-search-line"></i>
      <h3>请选择候选人查看画像</h3>
      <p>包含人格分布、岗位胜任力、画像总结、亮点/风险分析</p>
    </div>

    <!-- 有数据时显示导出按钮和画像 -->
    <div v-else class="portrait-container">
      <!-- 画像卡片 -->
      <div class="portrait-card">
        <!-- 顶部工具栏 -->
        <div v-if="!hideToolbar" class="portrait-toolbar">
          <div class="toolbar-actions">
            <!-- 简历按钮 -->
            <button 
              class="toolbar-btn resume-btn" 
              @click="openResumeModal"
              :class="{ 'has-resume': hasResume }"
              title="简历管理"
            >
              <i class="ri-file-text-line"></i>
              <span>简历</span>
              <span v-if="hasResume" class="resume-badge"></span>
            </button>
            
            <!-- 导出按钮 -->
            <button 
              class="toolbar-btn export-btn" 
              @click="showExportMenu = !showExportMenu"
              :disabled="isExporting"
              title="导出画像"
            >
              <i class="ri-download-cloud-line"></i>
              <span>导出</span>
            </button>
            
            <!-- 导出菜单 -->
            <transition name="fade-slide">
              <div v-if="showExportMenu" class="export-dropdown">
                <button class="dropdown-item" @click="exportAsPNG">
                  <i class="ri-image-line"></i>
                  <span>导出为图片</span>
                </button>
                <button class="dropdown-item" @click="exportAsPDF">
                  <i class="ri-file-pdf-line"></i>
                  <span>导出为 PDF</span>
                </button>
                <button class="dropdown-item disabled" @click="exportAsWord">
                  <i class="ri-file-word-line"></i>
                  <span>导出为 Word</span>
                </button>
              </div>
            </transition>
          </div>
        </div>

        <!-- 精致渐变头部 -->
        <div class="header-gradient">
          <div class="header-content">
          <!-- 左侧信息 -->
          <div class="candidate-info">
            <div class="avatar-badge">{{ displayData.name.charAt(0) }}</div>
            <div class="info-text">
              <div class="name-row">
                <h1 class="name">{{ displayData.name }}</h1>
                <!-- 人格类型徽章 - 完整格式：问卷类型 · 人格类型 描述 -->
                <div v-if="isMBTI" class="personality-badge mbti" :title="mbtiTypeInfo?.description || 'MBTI人格类型'">
                  <span class="badge-prefix">MBTI</span>
                  <span class="badge-divider">·</span>
                  <span class="badge-type">{{ personalityTypeLabel }}</span>
                  <span class="badge-desc">{{ getMBTIName(personalityTypeLabel) }}</span>
                </div>
                <div v-else-if="isDISC" class="personality-badge disc" :title="'DISC行为风格'">
                  <span class="badge-prefix">DISC</span>
                  <span class="badge-divider">·</span>
                  <span class="badge-type">{{ personalityTypeLabel }}</span>
                  <span class="badge-desc">{{ getDISCName(personalityTypeLabel) }}</span>
                </div>
                <div v-else class="personality-badge epq" :title="'EPQ人格类型'">
                  <span class="badge-prefix">EPQ</span>
                  <span class="badge-divider">·</span>
                  <span class="badge-type">{{ personalityTypeLabel }}</span>
                </div>
              </div>
              <div class="meta-row">
                <div class="meta-item">
                  <i class="ri-briefcase-4-line"></i>
                  <span>{{ displayData.appliedPosition || '未指定岗位' }}</span>
                </div>
                <div class="meta-divider">·</div>
                <div class="meta-item">
                  <i class="ri-calendar-event-line"></i>
                  <span>{{ displayData.updatedAt }}</span>
                </div>
              </div>
              <div class="tags-row">
                <span v-for="tag in displayData.tags" :key="tag" class="tag-pill">
                  {{ tag }}
                </span>
              </div>
              
              <!-- 专家分析按钮保留，深度分析按钮隐藏避免误触 -->
              <div class="analysis-level-switch">
                <button 
                  class="level-btn"
                  style="display: none;"
                  :class="{ 
                    active: currentAnalysisLevel === 'pro',
                    cached: cacheStatus?.cached_levels?.pro
                  }"
                  @click="switchAnalysisLevel('pro')"
                  :disabled="isSwitchingLevel"
                  title="深度分析"
                >
                  <i class="ri-focus-3-line"></i>
                  <span>深度分析</span>
                  <span v-if="cacheStatus?.cached_levels?.pro" class="cache-dot" title="已缓存"></span>
                </button>
                <button 
                  class="level-btn"
                  :class="{ 
                    active: currentAnalysisLevel === 'expert',
                    cached: cacheStatus?.cached_levels?.expert
                  }"
                  @click="switchAnalysisLevel('expert')"
                  :disabled="isSwitchingLevel"
                  title="专家分析 (DeepSeek)"
                >
                  <i class="ri-vip-crown-line"></i>
                  <span>专家分析</span>
                  <span v-if="cacheStatus?.cached_levels?.expert" class="cache-dot" title="已缓存"></span>
                </button>
                
                <!-- 🟢 P0+P1: 评分详情按钮 -->
                <button 
                  class="level-btn score-detail-header-btn"
                  @click="showScoreBreakdown = true"
                  title="查看综合评分详情"
                >
                  <i class="ri-pie-chart-line"></i>
                  <span>评分详情</span>
                </button>
                
                <span v-if="isSwitchingLevel" class="switching-indicator">
                  <i class="ri-loader-4-line spin"></i>
                </span>
              </div>
            </div>
          </div>

          <!-- 右侧分数圈 -->
          <div class="score-circle-wrapper">
            <svg class="score-svg" viewBox="0 0 136 136">
              <defs>
                <linearGradient id="scoreGradient" x1="0%" y1="0%" x2="100%" y2="100%">
                  <stop
                    offset="0%"
                    :stop-color="getScoreColor(displayData.overallMatchScore)"
                    stop-opacity="1"
                  />
                  <stop
                    offset="100%"
                    :stop-color="getScoreColor(displayData.overallMatchScore)"
                    stop-opacity="0.7"
                  />
                </linearGradient>
                <filter id="glow">
                  <feGaussianBlur stdDeviation="2.5" result="coloredBlur" />
                  <feMerge>
                    <feMergeNode in="coloredBlur" />
                    <feMergeNode in="SourceGraphic" />
                  </feMerge>
                </filter>
              </defs>
              <circle
                cx="68"
                cy="68"
                :r="scoreProgress.radius"
                fill="none"
                stroke="rgba(255, 255, 255, 0.25)"
                stroke-width="8"
              />
              <circle
                cx="68"
                cy="68"
                :r="scoreProgress.radius"
                fill="none"
                stroke="url(#scoreGradient)"
                stroke-width="8"
                stroke-linecap="round"
                :stroke-dasharray="scoreProgress.circumference"
                :stroke-dashoffset="scoreProgress.offset"
                transform="rotate(-90 68 68)"
                class="progress-circle"
                filter="url(#glow)"
              />
              <!-- 文字直接在SVG内，确保导出时居中 -->
              <text x="68" y="62" text-anchor="middle" dominant-baseline="middle" 
                    fill="white" font-size="36" font-weight="700" class="score-svg-value">
                {{ displayData.overallMatchScore }}
              </text>
              <text x="68" y="90" text-anchor="middle" dominant-baseline="middle"
                    fill="rgba(255,255,255,0.8)" font-size="12" class="score-svg-label">
                综合匹配度
              </text>
            </svg>
            <!-- 保留DOM文字用于页面显示（导出时隐藏） -->
            <div class="score-text score-text-dom">
              <div class="score-value">{{ displayData.overallMatchScore }}</div>
              <div class="score-label">综合匹配度</div>
            </div>
          </div>
        </div>
      </div>

      <!-- 测评记录折叠列表 -->
      <AssessmentAccordion 
        v-if="!hideAssessmentList && displayData.assessments && displayData.assessments.length > 0"
        :assessments="displayData.assessments"
        :profile="displayData"
      />

      <!-- 主内容区 -->
      <div class="main-content">
        <!-- 双栏布局：雷达图 + 胜任力 -->
        <div class="two-column-grid">
          <!-- 左栏：人格雷达图 -->
          <div class="card-section radar-section">
            <div class="section-header">
              <div class="header-icon">
                <i class="ri-radar-line"></i>
              </div>
              <div>
                <h2 class="section-title">人格特征分布</h2>
                <p class="section-subtitle">PERSONALITY TRAIT DISTRIBUTION</p>
              </div>
            </div>

            <!-- MBTI 四象限展示（替代雷达图） -->
            <div v-if="isMBTI" class="mbti-quadrant-container">
              <!-- 四个维度的进度条展示 -->
              <div v-for="dim in displayData.personalityDimensions" :key="dim.key" class="mbti-dimension">
                <div class="mbti-dimension-header">
                  <span class="dimension-label">{{ dim.label }} ({{ dim.key }})</span>
                  <span class="dimension-score">{{ dim.score }}</span>
                </div>
                <div class="mbti-bar-container">
                  <div class="mbti-bar-track">
                    <div class="mbti-bar-fill" :style="{ width: dim.score + '%' }">
                      <div class="mbti-bar-glow"></div>
                    </div>
                    <div class="mbti-center-marker"></div>
                  </div>
                  <div class="mbti-bar-labels">
                    <span class="bar-label-left">{{ dim.label?.split('-')?.[0]?.trim() || '' }} ({{ dim.key?.split('-')?.[0] || '' }})</span>
                    <span class="bar-label-right">{{ dim.label?.split('-')?.[1]?.trim() || '' }} ({{ dim.key?.split('-')?.[1] || '' }})</span>
                  </div>
                </div>
              </div>
            </div>

            <!-- DISC 四色象限图展示 -->
            <div v-else-if="isDISC" class="disc-quadrant-container">
              <div class="disc-quadrant">
                <!-- D - 支配型 (红色) -->
                <div class="disc-item disc-d" :class="{ active: getDISCScore('D') > 50 }">
                  <div class="disc-icon">
                    <i class="ri-fire-line"></i>
                  </div>
                  <div class="disc-label">D 支配型</div>
                  <div class="disc-score">{{ getDISCScore('D') }}</div>
                  <div class="disc-bar">
                    <div class="disc-bar-fill" :style="{ width: getDISCScore('D') + '%' }"></div>
                  </div>
                  <div class="disc-traits">结果导向、决断力强</div>
                </div>
                
                <!-- I - 影响型 (黄色) -->
                <div class="disc-item disc-i" :class="{ active: getDISCScore('I') > 50 }">
                  <div class="disc-icon">
                    <i class="ri-sun-line"></i>
                  </div>
                  <div class="disc-label">I 影响型</div>
                  <div class="disc-score">{{ getDISCScore('I') }}</div>
                  <div class="disc-bar">
                    <div class="disc-bar-fill" :style="{ width: getDISCScore('I') + '%' }"></div>
                  </div>
                  <div class="disc-traits">热情开朗、善于社交</div>
                </div>
                
                <!-- S - 稳健型 (绿色) -->
                <div class="disc-item disc-s" :class="{ active: getDISCScore('S') > 50 }">
                  <div class="disc-icon">
                    <i class="ri-leaf-line"></i>
                  </div>
                  <div class="disc-label">S 稳健型</div>
                  <div class="disc-score">{{ getDISCScore('S') }}</div>
                  <div class="disc-bar">
                    <div class="disc-bar-fill" :style="{ width: getDISCScore('S') + '%' }"></div>
                  </div>
                  <div class="disc-traits">耐心稳重、团队协作</div>
                </div>
                
                <!-- C - 谨慎型 (蓝色) -->
                <div class="disc-item disc-c" :class="{ active: getDISCScore('C') > 50 }">
                  <div class="disc-icon">
                    <i class="ri-shield-check-line"></i>
                  </div>
                  <div class="disc-label">C 谨慎型</div>
                  <div class="disc-score">{{ getDISCScore('C') }}</div>
                  <div class="disc-bar">
                    <div class="disc-bar-fill" :style="{ width: getDISCScore('C') + '%' }"></div>
                  </div>
                  <div class="disc-traits">严谨细致、追求品质</div>
                </div>
              </div>
            </div>

            <!-- EPQ 圆环图展示 -->
            <div v-else class="epq-rings-container">
              <div v-for="(dim, index) in displayData.personalityDimensions" 
                   :key="dim.key" 
                   class="epq-ring-item">
                <div class="ring-wrapper">
                  <svg viewBox="0 0 120 120" class="ring-svg">
                <defs>
                      <linearGradient :id="`ringGradient-${index}`" x1="0%" y1="0%" x2="100%" y2="100%">
                        <stop offset="0%" :stop-color="getRingColor(index)" stop-opacity="1" />
                        <stop offset="100%" :stop-color="getRingColor(index)" stop-opacity="0.6" />
                      </linearGradient>
                </defs>
                    <!-- 背景圆环 -->
                <circle
                      cx="60"
                      cy="60"
                      r="45"
                  fill="none"
                  stroke="#e5e7eb"
                      stroke-width="10"
                />
                    <!-- 进度圆环 -->
                <circle
                      cx="60"
                      cy="60"
                      r="45"
                      fill="none"
                      :stroke="`url(#ringGradient-${index})`"
                      stroke-width="10"
                      stroke-linecap="round"
                      :stroke-dasharray="`${(dim.score / 100) * 282.7} 282.7`"
                      transform="rotate(-90 60 60)"
                      class="ring-progress"
                    />
                    <!-- 分数直接在SVG内，确保导出时居中 -->
                    <text x="60" y="68" text-anchor="middle" dominant-baseline="middle" 
                          fill="#374151" font-size="24" font-weight="700" class="ring-svg-score">
                      {{ dim.score }}
                    </text>
              </svg>
                  <!-- 中心内容（导出时隐藏，只用SVG文字） -->
                  <div class="ring-center ring-center-dom">
                    <div class="ring-icon" :style="{ color: getRingColor(index) }">
                      <i :class="getRingIcon(dim.key)"></i>
                    </div>
                    <div class="ring-score">{{ dim.score }}</div>
                  </div>
                </div>
                <!-- 标签和描述 -->
                <div class="ring-label">{{ dim.label }}</div>
                <div class="ring-desc">{{ dim.description || getDefaultDescription(dim.key) }}</div>
              </div>
            </div>
          </div>

          <!-- 右栏：胜任力 - 使用重构后的组件 🟢 -->
          <CompetencySection :competencies="displayData.competencies" />
        </div>

        <!-- 亮点与风险 -->
        <div class="insights-grid">
          <div class="insight-card highlight-card">
            <div class="insight-header">
              <div class="icon-badge highlight-badge">
                <i class="ri-checkbox-circle-fill"></i>
              </div>
              <h3 class="insight-title">优势亮点</h3>
            </div>
            <ul class="insight-list">
              <li
                v-for="(item, i) in displayData.highlights"
                :key="i"
                class="insight-item highlight-item"
              >
                <i class="ri-checkbox-circle-line"></i>
                <span>{{ item }}</span>
              </li>
            </ul>
          </div>

          <div class="insight-card risk-card">
            <div class="insight-header">
              <div class="icon-badge risk-badge">
                <i class="ri-error-warning-fill"></i>
              </div>
              <h3 class="insight-title">潜在风险</h3>
            </div>
            <ul class="insight-list">
              <li
                v-for="(item, i) in displayData.risks"
                :key="i"
                class="insight-item risk-item"
              >
                <i class="ri-error-warning-line"></i>
                <span>{{ item }}</span>
              </li>
            </ul>
          </div>
        </div>

        <!-- 新增：岗位推荐模块 -->
        <div class="position-recommendation-section">
          <div class="section-header-block">
            <div class="header-icon-large">
              <i class="ri-compass-3-line"></i>
            </div>
            <div>
              <h2 class="section-title-large">岗位匹配分析</h2>
              <p class="section-subtitle">POSITION MATCH ANALYSIS</p>
            </div>
          </div>

          <div class="position-grid">
            <!-- 推荐岗位 -->
            <div class="position-card suitable-card">
              <div class="position-header">
                <i class="ri-thumb-up-line"></i>
                <h4>推荐岗位</h4>
              </div>
              <div class="position-list">
                <span
                  v-for="(pos, i) in displayData.suitablePositions"
                  :key="i"
                  class="position-tag suitable-tag"
                >
                  <i class="ri-check-line"></i>
                  {{ pos }}
                </span>
              </div>
            </div>

            <!-- 不推荐岗位 -->
            <div class="position-card unsuitable-card">
              <div class="position-header">
                <i class="ri-close-circle-line"></i>
                <h4>不推荐岗位</h4>
              </div>
              <div class="position-list">
                <span
                  v-for="(pos, i) in displayData.unsuitablePositions"
                  :key="i"
                  class="position-tag unsuitable-tag"
                >
                  <i class="ri-close-line"></i>
                  {{ pos }}
                </span>
              </div>
            </div>
          </div>
        </div>

        <!-- 新增：发展建议与面试焦点 -->
        <div class="action-grid" v-if="displayData.developmentSuggestions?.length || displayData.interviewFocus?.length">
          <!-- 发展建议 -->
          <div class="action-card development-card" v-if="displayData.developmentSuggestions?.length">
            <div class="action-header">
              <div class="icon-badge development-badge">
                <i class="ri-lightbulb-line"></i>
              </div>
              <h3 class="action-title">发展建议</h3>
            </div>
            <ul class="action-list">
              <li
                v-for="(item, i) in displayData.developmentSuggestions"
                :key="i"
                class="action-item development-item"
              >
                <i class="ri-arrow-right-s-line"></i>
                <span>{{ item }}</span>
              </li>
            </ul>
          </div>

          <!-- 面试关注点 -->
          <div class="action-card interview-card" v-if="displayData.interviewFocus?.length">
            <div class="action-header">
              <div class="icon-badge interview-badge">
                <i class="ri-question-answer-line"></i>
              </div>
              <h3 class="action-title">面试关注点</h3>
            </div>
            <ul class="action-list">
              <li
                v-for="(item, i) in displayData.interviewFocus"
                :key="i"
                class="action-item interview-item"
              >
                <i class="ri-arrow-right-s-line"></i>
                <span>{{ item }}</span>
              </li>
            </ul>
          </div>
        </div>

        <!-- 🌟 综合评价 - 使用重构后的组件 🟢 + P1-2 降级提示 -->
        <SummaryCard
          :ai-analysis-text="displayData.aiAnalysisText"
          :is-fallback="displayData.isFallbackAnalysis"
          :fallback-reason="displayData.fallbackReason"
          @retry-ai="handleRetryAI"
        />
      </div><!-- 结束 main-content -->
    </div><!-- 结束 portrait-card -->
  </div><!-- 结束 portrait-container -->
</div><!-- 结束 portrait-wrapper -->

<!-- 简历模态框 -->
<ResumeModal
  :visible="showResumeModal"
  :candidate-id="profile?.id ? Number(profile.id) : undefined"
  :candidate-name="profile?.name"
  :resume-info="resumeInfo"
  :loading="resumeLoading"
  :is-regenerating-portrait="isRegeneratingPortrait"
  @close="showResumeModal = false"
  @uploaded="handleResumeUploaded"
  @error="handleResumeError"
  @download="handleDownloadResume"
  @delete="handleDeleteResume"
  @parse="handleParseResume"
  @parse-complete="handleParseComplete"
/>

<!-- 删除简历确认弹窗 -->
<Transition name="modal">
  <div v-if="showDeleteResumeConfirm" class="delete-confirm-overlay" @click.self="cancelDeleteResume">
    <div class="delete-confirm-modal">
      <div class="modal-icon warning">
        <i class="ri-error-warning-line"></i>
      </div>
      <h3>确认删除简历</h3>
      <p>删除后将无法恢复，确定要删除这份简历吗？</p>
      <div class="modal-actions">
        <button class="btn-secondary" @click="cancelDeleteResume">取消</button>
        <button class="btn-danger" @click="confirmDeleteResume">确认删除</button>
      </div>
    </div>
  </div>
</Transition>

<!-- 消息提示 Toast -->
<Transition name="toast">
  <div v-if="showToast" :class="['toast-message', toastType]">
    <i :class="toastType === 'success' ? 'ri-check-line' : toastType === 'error' ? 'ri-close-circle-line' : 'ri-information-line'"></i>
    <span>{{ toastMessage }}</span>
  </div>
</Transition>

<!-- 🟢 P0+P1: 评分详情弹窗 -->
<ScoreBreakdownModal
  v-model:visible="showScoreBreakdown"
  :overall-score="displayData.overallMatchScore"
  :score-breakdown="displayData.scoreBreakdown"
  :assessment-count="assessmentCount"
  :current-assessment-type="currentAssessmentType"
  :has-resume="hasResume"
  :cross-validation-data="displayData.crossValidation"
  :assessments="displayData.assessmentInfoList"
/>
</template>

<style scoped>
@import './styles/portrait-card.css';

/* 页面显示时隐藏SVG文字（只在导出时显示） */
.score-svg-value,
.score-svg-label,
.ring-svg-score {
  display: none;
}
</style>

