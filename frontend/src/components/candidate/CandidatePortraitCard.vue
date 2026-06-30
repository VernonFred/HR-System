<script setup lang="ts">
import { computed, ref, onMounted, watch } from 'vue';
import type { CandidateProfile } from '../../types/candidate';
import domtoimage from 'dom-to-image-more';
import jsPDF from 'jspdf';
import ResumeModal from '../resume/ResumeModal.vue';
import AssessmentAccordion from './AssessmentAccordion.vue';
import CompetencySection from './CompetencySection.vue';
import SummaryCard from './SummaryCard.vue';
import ScoreBreakdownModal from './ScoreBreakdownModal.vue';
import { getResumeInfo, getResumeDownloadUrl, deleteResume, parseResume } from '../../api/resumes';

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

const normalizeList = (value: string[] | string | undefined): string[] => {
  if (!value) return [];
  if (Array.isArray(value)) {
    return value.map(item => String(item).trim()).filter(Boolean);
  }
  return value
    .split(/[\n,，、;；|]+/)
    .map(item => item.trim())
    .filter(Boolean);
};

const suitablePositionsList = computed(() =>
  normalizeList(displayData.value.suitablePositions)
);

const unsuitablePositionsList = computed(() =>
  normalizeList(displayData.value.unsuitablePositions)
);

const developmentSuggestionsList = computed(() =>
  normalizeList(displayData.value.developmentSuggestions)
);

const interviewFocusList = computed(() =>
  normalizeList(displayData.value.interviewFocus)
);

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
    const levelLabel = 'AI画像';
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

    const levelLabel = 'AI画像';
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

const regeneratePortrait = (_level: 'pro' | 'expert' = 'pro') => {
  if (!props.profile?.id) return;

  // 设置加载状态（按钮显示加载中）
    isRegeneratingPortrait.value = true;

    // 关闭简历弹窗
    showResumeModal.value = false;

  // 触发父组件重新生成画像（由父组件负责调用API和显示进度条动画）
  // 单模型模式下统一使用默认画像生成流程。
  emit('portrait-regenerated', 'pro', true); // forceRefresh = true

  // 注意：isRegeneratingPortrait 会在父组件完成后自动重置
  // 这里延迟重置，确保弹窗关闭动画完成
  setTimeout(() => {
    isRegeneratingPortrait.value = false;
  }, 500);
};

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
  emit('portrait-regenerated', 'pro', true)
}

</script>

<template src="./CandidatePortraitCard.template.html"></template>


<style scoped>
@import './styles/portrait-card.css';
</style>
