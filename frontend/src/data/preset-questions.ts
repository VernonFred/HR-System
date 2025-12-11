/**
 * 内置问卷预设题目数据
 * 包含 EPQ (88道)、DISC (28道)、MBTI (93道) 标准题目
 */

export interface PresetQuestion {
  id: string;
  order: number;
  type: 'yesno' | 'scale' | 'choice' | 'radio';
  text: string;
  required: boolean;
  dimension?: string;  // 所属维度
  positive?: boolean;  // 是否正向计分
  options?: { value: string; label: string }[];
  scale?: { min: number; max: number; minLabel?: string; maxLabel?: string };
  optionA?: string;
  optionB?: string;
}

// =====================================================
// EPQ 艾森克人格问卷 (88道题)
// 维度: E(外向性), N(神经质), P(精神质), L(掩饰性)
// =====================================================
export const EPQ_QUESTIONS: PresetQuestion[] = [
  // E维度 - 外向性 (21道)
  { id: 'epq_1', order: 1, type: 'yesno', text: '你是否喜欢周围热闹？', required: true, dimension: 'E', positive: true },
  { id: 'epq_2', order: 2, type: 'yesno', text: '你是否是一个健谈的人？', required: true, dimension: 'E', positive: true },
  { id: 'epq_3', order: 3, type: 'yesno', text: '你是否喜欢参加聚会？', required: true, dimension: 'E', positive: true },
  { id: 'epq_4', order: 4, type: 'yesno', text: '你是否喜欢结交新朋友？', required: true, dimension: 'E', positive: true },
  { id: 'epq_5', order: 5, type: 'yesno', text: '你是否喜欢和别人开玩笑？', required: true, dimension: 'E', positive: true },
  { id: 'epq_6', order: 6, type: 'yesno', text: '你是否宁愿看书也不愿去社交？', required: true, dimension: 'E', positive: false },
  { id: 'epq_7', order: 7, type: 'yesno', text: '你是否喜欢独处？', required: true, dimension: 'E', positive: false },
  { id: 'epq_8', order: 8, type: 'yesno', text: '在社交场合你是否容易放松？', required: true, dimension: 'E', positive: true },
  { id: 'epq_9', order: 9, type: 'yesno', text: '你是否善于使聚会活跃起来？', required: true, dimension: 'E', positive: true },
  { id: 'epq_10', order: 10, type: 'yesno', text: '你是否经常主动和陌生人交谈？', required: true, dimension: 'E', positive: true },
  { id: 'epq_11', order: 11, type: 'yesno', text: '你是否喜欢有许多人围着你？', required: true, dimension: 'E', positive: true },
  { id: 'epq_12', order: 12, type: 'yesno', text: '你是否喜欢安静的环境？', required: true, dimension: 'E', positive: false },
  { id: 'epq_13', order: 13, type: 'yesno', text: '你是否经常参加社交活动？', required: true, dimension: 'E', positive: true },
  { id: 'epq_14', order: 14, type: 'yesno', text: '你是否喜欢在人群中成为焦点？', required: true, dimension: 'E', positive: true },
  { id: 'epq_15', order: 15, type: 'yesno', text: '你是否容易和别人打成一片？', required: true, dimension: 'E', positive: true },
  { id: 'epq_16', order: 16, type: 'yesno', text: '你是否喜欢独自工作？', required: true, dimension: 'E', positive: false },
  { id: 'epq_17', order: 17, type: 'yesno', text: '你是否喜欢热闹的活动？', required: true, dimension: 'E', positive: true },
  { id: 'epq_18', order: 18, type: 'yesno', text: '你是否经常感到活力充沛？', required: true, dimension: 'E', positive: true },
  { id: 'epq_19', order: 19, type: 'yesno', text: '你是否喜欢冒险和刺激？', required: true, dimension: 'E', positive: true },
  { id: 'epq_20', order: 20, type: 'yesno', text: '你是否喜欢变化和新鲜感？', required: true, dimension: 'E', positive: true },
  { id: 'epq_21', order: 21, type: 'yesno', text: '你是否喜欢按计划行事而非随机应变？', required: true, dimension: 'E', positive: false },

  // N维度 - 神经质 (23道)
  { id: 'epq_22', order: 22, type: 'yesno', text: '你是否经常感到紧张或焦虑？', required: true, dimension: 'N', positive: true },
  { id: 'epq_23', order: 23, type: 'yesno', text: '你是否容易感到不安？', required: true, dimension: 'N', positive: true },
  { id: 'epq_24', order: 24, type: 'yesno', text: '你是否经常感到孤独？', required: true, dimension: 'N', positive: true },
  { id: 'epq_25', order: 25, type: 'yesno', text: '你是否容易受伤害？', required: true, dimension: 'N', positive: true },
  { id: 'epq_26', order: 26, type: 'yesno', text: '你是否经常为过去的事情后悔？', required: true, dimension: 'N', positive: true },
  { id: 'epq_27', order: 27, type: 'yesno', text: '你是否容易发脾气？', required: true, dimension: 'N', positive: true },
  { id: 'epq_28', order: 28, type: 'yesno', text: '你是否经常失眠？', required: true, dimension: 'N', positive: true },
  { id: 'epq_29', order: 29, type: 'yesno', text: '你是否容易感到疲倦？', required: true, dimension: 'N', positive: true },
  { id: 'epq_30', order: 30, type: 'yesno', text: '你是否经常感到情绪低落？', required: true, dimension: 'N', positive: true },
  { id: 'epq_31', order: 31, type: 'yesno', text: '你是否容易被别人的情绪影响？', required: true, dimension: 'N', positive: true },
  { id: 'epq_32', order: 32, type: 'yesno', text: '你是否经常担心可能会发生不好的事？', required: true, dimension: 'N', positive: true },
  { id: 'epq_33', order: 33, type: 'yesno', text: '你是否经常感到紧张不安？', required: true, dimension: 'N', positive: true },
  { id: 'epq_34', order: 34, type: 'yesno', text: '你是否容易感到内疚？', required: true, dimension: 'N', positive: true },
  { id: 'epq_35', order: 35, type: 'yesno', text: '你是否经常觉得自己不如别人？', required: true, dimension: 'N', positive: true },
  { id: 'epq_36', order: 36, type: 'yesno', text: '你是否容易受批评影响？', required: true, dimension: 'N', positive: true },
  { id: 'epq_37', order: 37, type: 'yesno', text: '你是否经常感到心情起伏不定？', required: true, dimension: 'N', positive: true },
  { id: 'epq_38', order: 38, type: 'yesno', text: '你是否经常感到烦躁？', required: true, dimension: 'N', positive: true },
  { id: 'epq_39', order: 39, type: 'yesno', text: '你是否容易感到紧张和压力？', required: true, dimension: 'N', positive: true },
  { id: 'epq_40', order: 40, type: 'yesno', text: '你是否经常觉得自己会失败？', required: true, dimension: 'N', positive: true },
  { id: 'epq_41', order: 41, type: 'yesno', text: '你是否容易感到沮丧？', required: true, dimension: 'N', positive: true },
  { id: 'epq_42', order: 42, type: 'yesno', text: '你是否经常感到焦虑不安？', required: true, dimension: 'N', positive: true },
  { id: 'epq_43', order: 43, type: 'yesno', text: '你是否容易感到悲伤？', required: true, dimension: 'N', positive: true },
  { id: 'epq_44', order: 44, type: 'yesno', text: '你是否经常为小事烦恼？', required: true, dimension: 'N', positive: true },

  // P维度 - 精神质 (20道)
  { id: 'epq_45', order: 45, type: 'yesno', text: '你是否喜欢恶作剧？', required: true, dimension: 'P', positive: true },
  { id: 'epq_46', order: 46, type: 'yesno', text: '你是否认为规则可以被打破？', required: true, dimension: 'P', positive: true },
  { id: 'epq_47', order: 47, type: 'yesno', text: '你是否喜欢与众不同？', required: true, dimension: 'P', positive: true },
  { id: 'epq_48', order: 48, type: 'yesno', text: '你是否不太关心别人的感受？', required: true, dimension: 'P', positive: true },
  { id: 'epq_49', order: 49, type: 'yesno', text: '你是否喜欢冒险而不考虑后果？', required: true, dimension: 'P', positive: true },
  { id: 'epq_50', order: 50, type: 'yesno', text: '你是否容易对别人感到厌烦？', required: true, dimension: 'P', positive: true },
  { id: 'epq_51', order: 51, type: 'yesno', text: '你是否不太在意社会规范？', required: true, dimension: 'P', positive: true },
  { id: 'epq_52', order: 52, type: 'yesno', text: '你是否喜欢做一些出格的事？', required: true, dimension: 'P', positive: true },
  { id: 'epq_53', order: 53, type: 'yesno', text: '你是否认为大多数人都太敏感了？', required: true, dimension: 'P', positive: true },
  { id: 'epq_54', order: 54, type: 'yesno', text: '你是否喜欢嘲笑别人？', required: true, dimension: 'P', positive: true },
  { id: 'epq_55', order: 55, type: 'yesno', text: '你是否不太考虑道德问题？', required: true, dimension: 'P', positive: true },
  { id: 'epq_56', order: 56, type: 'yesno', text: '你是否喜欢挑战权威？', required: true, dimension: 'P', positive: true },
  { id: 'epq_57', order: 57, type: 'yesno', text: '你是否容易感到无聊？', required: true, dimension: 'P', positive: true },
  { id: 'epq_58', order: 58, type: 'yesno', text: '你是否认为诚实有时候是愚蠢的？', required: true, dimension: 'P', positive: true },
  { id: 'epq_59', order: 59, type: 'yesno', text: '你是否不太在意别人怎么看你？', required: true, dimension: 'P', positive: true },
  { id: 'epq_60', order: 60, type: 'yesno', text: '你是否喜欢独来独往？', required: true, dimension: 'P', positive: true },
  { id: 'epq_61', order: 61, type: 'yesno', text: '你是否认为大多数人不值得信任？', required: true, dimension: 'P', positive: true },
  { id: 'epq_62', order: 62, type: 'yesno', text: '你是否不太感到内疚？', required: true, dimension: 'P', positive: true },
  { id: 'epq_63', order: 63, type: 'yesno', text: '你是否喜欢冷酷的幽默？', required: true, dimension: 'P', positive: true },
  { id: 'epq_64', order: 64, type: 'yesno', text: '你是否不太关心传统习俗？', required: true, dimension: 'P', positive: true },

  // L维度 - 掩饰性 (24道)
  { id: 'epq_65', order: 65, type: 'yesno', text: '你是否总是说实话？', required: true, dimension: 'L', positive: true },
  { id: 'epq_66', order: 66, type: 'yesno', text: '你是否从不说谎？', required: true, dimension: 'L', positive: true },
  { id: 'epq_67', order: 67, type: 'yesno', text: '你是否总是遵守承诺？', required: true, dimension: 'L', positive: true },
  { id: 'epq_68', order: 68, type: 'yesno', text: '你是否从不迟到？', required: true, dimension: 'L', positive: true },
  { id: 'epq_69', order: 69, type: 'yesno', text: '你是否总是礼貌待人？', required: true, dimension: 'L', positive: true },
  { id: 'epq_70', order: 70, type: 'yesno', text: '你是否从不说别人坏话？', required: true, dimension: 'L', positive: true },
  { id: 'epq_71', order: 71, type: 'yesno', text: '你是否总是帮助别人？', required: true, dimension: 'L', positive: true },
  { id: 'epq_72', order: 72, type: 'yesno', text: '你是否从不发脾气？', required: true, dimension: 'L', positive: true },
  { id: 'epq_73', order: 73, type: 'yesno', text: '你是否总是按时完成任务？', required: true, dimension: 'L', positive: true },
  { id: 'epq_74', order: 74, type: 'yesno', text: '你是否从不嫉妒别人？', required: true, dimension: 'L', positive: true },
  { id: 'epq_75', order: 75, type: 'yesno', text: '你是否总是接受批评？', required: true, dimension: 'L', positive: true },
  { id: 'epq_76', order: 76, type: 'yesno', text: '你是否从不偷懒？', required: true, dimension: 'L', positive: true },
  { id: 'epq_77', order: 77, type: 'yesno', text: '你是否总是尊重别人？', required: true, dimension: 'L', positive: true },
  { id: 'epq_78', order: 78, type: 'yesno', text: '你是否从不抱怨？', required: true, dimension: 'L', positive: true },
  { id: 'epq_79', order: 79, type: 'yesno', text: '你是否总是乐于助人？', required: true, dimension: 'L', positive: true },
  { id: 'epq_80', order: 80, type: 'yesno', text: '你是否从不感到生气？', required: true, dimension: 'L', positive: true },
  { id: 'epq_81', order: 81, type: 'yesno', text: '你是否总是承认错误？', required: true, dimension: 'L', positive: true },
  { id: 'epq_82', order: 82, type: 'yesno', text: '你是否从不做坏事？', required: true, dimension: 'L', positive: true },
  { id: 'epq_83', order: 83, type: 'yesno', text: '你是否总是守时？', required: true, dimension: 'L', positive: true },
  { id: 'epq_84', order: 84, type: 'yesno', text: '你是否从不有私心？', required: true, dimension: 'L', positive: true },
  { id: 'epq_85', order: 85, type: 'yesno', text: '你是否总是公平对待别人？', required: true, dimension: 'L', positive: true },
  { id: 'epq_86', order: 86, type: 'yesno', text: '你是否从不感到嫉妒？', required: true, dimension: 'L', positive: true },
  { id: 'epq_87', order: 87, type: 'yesno', text: '你是否总是控制自己的情绪？', required: true, dimension: 'L', positive: true },
  { id: 'epq_88', order: 88, type: 'yesno', text: '你是否从不占别人便宜？', required: true, dimension: 'L', positive: true },
];

// =====================================================
// DISC 性格测评 (28道题)
// 维度: D(支配型), I(影响型), S(稳健型), C(谨慎型)
// =====================================================
export const DISC_QUESTIONS: PresetQuestion[] = [
  // D维度 - 支配型 (7道)
  { id: 'disc_1', order: 1, type: 'scale', text: '我喜欢掌控局面并做出决策', required: true, dimension: 'D', scale: { min: 1, max: 5, minLabel: '非常不同意', maxLabel: '非常同意' } },
  { id: 'disc_2', order: 2, type: 'scale', text: '我喜欢接受挑战和竞争', required: true, dimension: 'D', scale: { min: 1, max: 5, minLabel: '非常不同意', maxLabel: '非常同意' } },
  { id: 'disc_3', order: 3, type: 'scale', text: '我倾向于直接表达自己的观点', required: true, dimension: 'D', scale: { min: 1, max: 5, minLabel: '非常不同意', maxLabel: '非常同意' } },
  { id: 'disc_4', order: 4, type: 'scale', text: '我喜欢快速做出决定', required: true, dimension: 'D', scale: { min: 1, max: 5, minLabel: '非常不同意', maxLabel: '非常同意' } },
  { id: 'disc_5', order: 5, type: 'scale', text: '我更关注结果而非过程', required: true, dimension: 'D', scale: { min: 1, max: 5, minLabel: '非常不同意', maxLabel: '非常同意' } },
  { id: 'disc_6', order: 6, type: 'scale', text: '我喜欢领导团队', required: true, dimension: 'D', scale: { min: 1, max: 5, minLabel: '非常不同意', maxLabel: '非常同意' } },
  { id: 'disc_7', order: 7, type: 'scale', text: '我不怕承担风险', required: true, dimension: 'D', scale: { min: 1, max: 5, minLabel: '非常不同意', maxLabel: '非常同意' } },

  // I维度 - 影响型 (7道)
  { id: 'disc_8', order: 8, type: 'scale', text: '我喜欢与人交流和社交活动', required: true, dimension: 'I', scale: { min: 1, max: 5, minLabel: '非常不同意', maxLabel: '非常同意' } },
  { id: 'disc_9', order: 9, type: 'scale', text: '我善于激励和影响他人', required: true, dimension: 'I', scale: { min: 1, max: 5, minLabel: '非常不同意', maxLabel: '非常同意' } },
  { id: 'disc_10', order: 10, type: 'scale', text: '我喜欢成为关注的焦点', required: true, dimension: 'I', scale: { min: 1, max: 5, minLabel: '非常不同意', maxLabel: '非常同意' } },
  { id: 'disc_11', order: 11, type: 'scale', text: '我容易与人建立友好关系', required: true, dimension: 'I', scale: { min: 1, max: 5, minLabel: '非常不同意', maxLabel: '非常同意' } },
  { id: 'disc_12', order: 12, type: 'scale', text: '我喜欢表达自己的想法和感受', required: true, dimension: 'I', scale: { min: 1, max: 5, minLabel: '非常不同意', maxLabel: '非常同意' } },
  { id: 'disc_13', order: 13, type: 'scale', text: '我是一个乐观的人', required: true, dimension: 'I', scale: { min: 1, max: 5, minLabel: '非常不同意', maxLabel: '非常同意' } },
  { id: 'disc_14', order: 14, type: 'scale', text: '我喜欢团队合作', required: true, dimension: 'I', scale: { min: 1, max: 5, minLabel: '非常不同意', maxLabel: '非常同意' } },

  // S维度 - 稳健型 (7道)
  { id: 'disc_15', order: 15, type: 'scale', text: '我喜欢稳定和可预测的环境', required: true, dimension: 'S', scale: { min: 1, max: 5, minLabel: '非常不同意', maxLabel: '非常同意' } },
  { id: 'disc_16', order: 16, type: 'scale', text: '我是一个有耐心的人', required: true, dimension: 'S', scale: { min: 1, max: 5, minLabel: '非常不同意', maxLabel: '非常同意' } },
  { id: 'disc_17', order: 17, type: 'scale', text: '我喜欢帮助和支持他人', required: true, dimension: 'S', scale: { min: 1, max: 5, minLabel: '非常不同意', maxLabel: '非常同意' } },
  { id: 'disc_18', order: 18, type: 'scale', text: '我不喜欢突然的变化', required: true, dimension: 'S', scale: { min: 1, max: 5, minLabel: '非常不同意', maxLabel: '非常同意' } },
  { id: 'disc_19', order: 19, type: 'scale', text: '我是一个忠诚可靠的人', required: true, dimension: 'S', scale: { min: 1, max: 5, minLabel: '非常不同意', maxLabel: '非常同意' } },
  { id: 'disc_20', order: 20, type: 'scale', text: '我喜欢按部就班地工作', required: true, dimension: 'S', scale: { min: 1, max: 5, minLabel: '非常不同意', maxLabel: '非常同意' } },
  { id: 'disc_21', order: 21, type: 'scale', text: '我善于倾听他人', required: true, dimension: 'S', scale: { min: 1, max: 5, minLabel: '非常不同意', maxLabel: '非常同意' } },

  // C维度 - 谨慎型 (7道)
  { id: 'disc_22', order: 22, type: 'scale', text: '我注重细节和准确性', required: true, dimension: 'C', scale: { min: 1, max: 5, minLabel: '非常不同意', maxLabel: '非常同意' } },
  { id: 'disc_23', order: 23, type: 'scale', text: '我喜欢遵循规则和程序', required: true, dimension: 'C', scale: { min: 1, max: 5, minLabel: '非常不同意', maxLabel: '非常同意' } },
  { id: 'disc_24', order: 24, type: 'scale', text: '我在做决定前喜欢收集充分信息', required: true, dimension: 'C', scale: { min: 1, max: 5, minLabel: '非常不同意', maxLabel: '非常同意' } },
  { id: 'disc_25', order: 25, type: 'scale', text: '我追求高质量和高标准', required: true, dimension: 'C', scale: { min: 1, max: 5, minLabel: '非常不同意', maxLabel: '非常同意' } },
  { id: 'disc_26', order: 26, type: 'scale', text: '我是一个谨慎的人', required: true, dimension: 'C', scale: { min: 1, max: 5, minLabel: '非常不同意', maxLabel: '非常同意' } },
  { id: 'disc_27', order: 27, type: 'scale', text: '我喜欢分析和解决问题', required: true, dimension: 'C', scale: { min: 1, max: 5, minLabel: '非常不同意', maxLabel: '非常同意' } },
  { id: 'disc_28', order: 28, type: 'scale', text: '我注重事实和逻辑', required: true, dimension: 'C', scale: { min: 1, max: 5, minLabel: '非常不同意', maxLabel: '非常同意' } },
];

// =====================================================
// MBTI 性格测试 (93道题)
// 维度: E/I(外向/内向), S/N(感觉/直觉), T/F(思考/情感), J/P(判断/知觉)
// =====================================================
export const MBTI_QUESTIONS: PresetQuestion[] = [
  // E/I 维度 - 外向/内向 (23道)
  { id: 'mbti_1', order: 1, type: 'choice', text: '在聚会上，你通常：', required: true, dimension: 'EI', optionA: '与很多人交流，结交新朋友', optionB: '只与少数熟人深入交谈' },
  { id: 'mbti_2', order: 2, type: 'choice', text: '你更喜欢：', required: true, dimension: 'EI', optionA: '在人群中获得能量', optionB: '独处时充电恢复精力' },
  { id: 'mbti_3', order: 3, type: 'choice', text: '在工作中，你倾向于：', required: true, dimension: 'EI', optionA: '与他人合作讨论', optionB: '独立思考和工作' },
  { id: 'mbti_4', order: 4, type: 'choice', text: '周末时，你更喜欢：', required: true, dimension: 'EI', optionA: '参加社交活动', optionB: '在家安静休息' },
  { id: 'mbti_5', order: 5, type: 'choice', text: '当你有新想法时，你通常：', required: true, dimension: 'EI', optionA: '立即与他人分享讨论', optionB: '先自己思考整理' },
  { id: 'mbti_6', order: 6, type: 'choice', text: '你的朋友圈：', required: true, dimension: 'EI', optionA: '广泛，认识很多人', optionB: '小而深，几个知心好友' },
  { id: 'mbti_7', order: 7, type: 'choice', text: '在会议中，你通常：', required: true, dimension: 'EI', optionA: '积极发言表达观点', optionB: '倾听思考后发言' },
  { id: 'mbti_8', order: 8, type: 'choice', text: '你更喜欢的学习方式：', required: true, dimension: 'EI', optionA: '小组讨论学习', optionB: '自学看书研究' },
  { id: 'mbti_9', order: 9, type: 'choice', text: '当遇到问题时，你倾向于：', required: true, dimension: 'EI', optionA: '找人讨论寻求帮助', optionB: '自己先尝试解决' },
  { id: 'mbti_10', order: 10, type: 'choice', text: '你更擅长：', required: true, dimension: 'EI', optionA: '口头表达', optionB: '书面表达' },
  { id: 'mbti_11', order: 11, type: 'choice', text: '在陌生环境中，你通常：', required: true, dimension: 'EI', optionA: '主动与人交谈', optionB: '等待他人主动接近' },
  { id: 'mbti_12', order: 12, type: 'choice', text: '长时间独处后，你会：', required: true, dimension: 'EI', optionA: '渴望社交互动', optionB: '感到舒适自在' },
  { id: 'mbti_13', order: 13, type: 'choice', text: '你的能量来源于：', required: true, dimension: 'EI', optionA: '与他人的互动', optionB: '内心的思考' },
  { id: 'mbti_14', order: 14, type: 'choice', text: '你更喜欢：', required: true, dimension: 'EI', optionA: '热闹的环境', optionB: '安静的环境' },
  { id: 'mbti_15', order: 15, type: 'choice', text: '当你需要做决定时：', required: true, dimension: 'EI', optionA: '喜欢与他人讨论', optionB: '喜欢独自思考' },
  { id: 'mbti_16', order: 16, type: 'choice', text: '你的思考方式：', required: true, dimension: 'EI', optionA: '边说边想', optionB: '想好再说' },
  { id: 'mbti_17', order: 17, type: 'choice', text: '在团队中，你更适合：', required: true, dimension: 'EI', optionA: '协调沟通角色', optionB: '专注执行角色' },
  { id: 'mbti_18', order: 18, type: 'choice', text: '你更喜欢的工作环境：', required: true, dimension: 'EI', optionA: '开放式办公', optionB: '独立办公室' },
  { id: 'mbti_19', order: 19, type: 'choice', text: '当你感到压力时：', required: true, dimension: 'EI', optionA: '找人倾诉', optionB: '独自消化' },
  { id: 'mbti_20', order: 20, type: 'choice', text: '你更容易：', required: true, dimension: 'EI', optionA: '被打断思路', optionB: '过度沉浸在思考中' },
  { id: 'mbti_21', order: 21, type: 'choice', text: '你的休闲活动：', required: true, dimension: 'EI', optionA: '社交聚会', optionB: '阅读或个人爱好' },
  { id: 'mbti_22', order: 22, type: 'choice', text: '在电话中，你通常：', required: true, dimension: 'EI', optionA: '喜欢长时间聊天', optionB: '简短说完事情' },
  { id: 'mbti_23', order: 23, type: 'choice', text: '你更喜欢：', required: true, dimension: 'EI', optionA: '广泛涉猎各种话题', optionB: '深入研究某个领域' },

  // S/N 维度 - 感觉/直觉 (23道)
  { id: 'mbti_24', order: 24, type: 'choice', text: '你更关注：', required: true, dimension: 'SN', optionA: '具体的事实和细节', optionB: '可能性和整体概念' },
  { id: 'mbti_25', order: 25, type: 'choice', text: '你更喜欢：', required: true, dimension: 'SN', optionA: '实际可行的方案', optionB: '创新有想象力的方案' },
  { id: 'mbti_26', order: 26, type: 'choice', text: '在描述事物时，你倾向于：', required: true, dimension: 'SN', optionA: '具体详细', optionB: '概括抽象' },
  { id: 'mbti_27', order: 27, type: 'choice', text: '你更信任：', required: true, dimension: 'SN', optionA: '实际经验', optionB: '直觉感受' },
  { id: 'mbti_28', order: 28, type: 'choice', text: '在学习新事物时，你偏好：', required: true, dimension: 'SN', optionA: '实践操作，亲身体验', optionB: '理论思考，理解原理' },
  { id: 'mbti_29', order: 29, type: 'choice', text: '你更喜欢的工作内容：', required: true, dimension: 'SN', optionA: '明确具体的任务', optionB: '开放性的问题' },
  { id: 'mbti_30', order: 30, type: 'choice', text: '当你阅读时，你更关注：', required: true, dimension: 'SN', optionA: '字面意思', optionB: '言外之意' },
  { id: 'mbti_31', order: 31, type: 'choice', text: '你更擅长记住：', required: true, dimension: 'SN', optionA: '具体事实', optionB: '整体印象' },
  { id: 'mbti_32', order: 32, type: 'choice', text: '当面对问题时，你首先：', required: true, dimension: 'SN', optionA: '收集具体信息', optionB: '寻找模式规律' },
  { id: 'mbti_33', order: 33, type: 'choice', text: '你更喜欢：', required: true, dimension: 'SN', optionA: '按部就班的工作', optionB: '创新突破的工作' },
  { id: 'mbti_34', order: 34, type: 'choice', text: '你的思维方式：', required: true, dimension: 'SN', optionA: '从具体到抽象', optionB: '从抽象到具体' },
  { id: 'mbti_35', order: 35, type: 'choice', text: '你更关心：', required: true, dimension: 'SN', optionA: '现在发生的事', optionB: '未来的可能性' },
  { id: 'mbti_36', order: 36, type: 'choice', text: '当别人描述事情时，你希望他们：', required: true, dimension: 'SN', optionA: '详细具体', optionB: '简洁概括' },
  { id: 'mbti_37', order: 37, type: 'choice', text: '你更喜欢：', required: true, dimension: 'SN', optionA: '使用已验证的方法', optionB: '尝试新的方法' },
  { id: 'mbti_38', order: 38, type: 'choice', text: '你的优势是：', required: true, dimension: 'SN', optionA: '注重细节', optionB: '把握全局' },
  { id: 'mbti_39', order: 39, type: 'choice', text: '你更喜欢：', required: true, dimension: 'SN', optionA: '明确的指示', optionB: '大方向的指引' },
  { id: 'mbti_40', order: 40, type: 'choice', text: '当遇到新情况时，你会：', required: true, dimension: 'SN', optionA: '参考过去经验', optionB: '探索新可能' },
  { id: 'mbti_41', order: 41, type: 'choice', text: '你更擅长：', required: true, dimension: 'SN', optionA: '执行落实', optionB: '策划构思' },
  { id: 'mbti_42', order: 42, type: 'choice', text: '你更喜欢讨论：', required: true, dimension: 'SN', optionA: '实际问题', optionB: '理论观点' },
  { id: 'mbti_43', order: 43, type: 'choice', text: '你的观察方式：', required: true, dimension: 'SN', optionA: '关注具体细节', optionB: '关注整体模式' },
  { id: 'mbti_44', order: 44, type: 'choice', text: '你更喜欢的书籍：', required: true, dimension: 'SN', optionA: '实用类', optionB: '想象类' },
  { id: 'mbti_45', order: 45, type: 'choice', text: '你更注重：', required: true, dimension: 'SN', optionA: '实际可行性', optionB: '创新可能性' },
  { id: 'mbti_46', order: 46, type: 'choice', text: '你的表达方式：', required: true, dimension: 'SN', optionA: '直接明了', optionB: '含蓄委婉' },

  // T/F 维度 - 思考/情感 (24道)
  { id: 'mbti_47', order: 47, type: 'choice', text: '做决定时，你更看重：', required: true, dimension: 'TF', optionA: '逻辑分析和客观标准', optionB: '个人价值观和对他人的影响' },
  { id: 'mbti_48', order: 48, type: 'choice', text: '当朋友有问题时，你通常：', required: true, dimension: 'TF', optionA: '帮助分析问题找解决方案', optionB: '倾听并给予情感支持' },
  { id: 'mbti_49', order: 49, type: 'choice', text: '你更欣赏的品质：', required: true, dimension: 'TF', optionA: '公正客观', optionB: '善解人意' },
  { id: 'mbti_50', order: 50, type: 'choice', text: '在争论中，你更注重：', required: true, dimension: 'TF', optionA: '谁的观点更有道理', optionB: '维护关系和感情' },
  { id: 'mbti_51', order: 51, type: 'choice', text: '批评别人时，你通常：', required: true, dimension: 'TF', optionA: '直接指出问题', optionB: '考虑对方感受' },
  { id: 'mbti_52', order: 52, type: 'choice', text: '你更看重：', required: true, dimension: 'TF', optionA: '真相和事实', optionB: '和谐和感情' },
  { id: 'mbti_53', order: 53, type: 'choice', text: '当你评估一件事时：', required: true, dimension: 'TF', optionA: '用逻辑分析利弊', optionB: '用感觉判断好坏' },
  { id: 'mbti_54', order: 54, type: 'choice', text: '你更喜欢被认为是：', required: true, dimension: 'TF', optionA: '能干有能力', optionB: '善良有同情心' },
  { id: 'mbti_55', order: 55, type: 'choice', text: '在团队中，你更关注：', required: true, dimension: 'TF', optionA: '完成任务目标', optionB: '团队成员感受' },
  { id: 'mbti_56', order: 56, type: 'choice', text: '当别人犯错时，你倾向于：', required: true, dimension: 'TF', optionA: '指出错误帮助改正', optionB: '理解原因给予鼓励' },
  { id: 'mbti_57', order: 57, type: 'choice', text: '你的沟通风格：', required: true, dimension: 'TF', optionA: '直接坦率', optionB: '委婉体贴' },
  { id: 'mbti_58', order: 58, type: 'choice', text: '你更容易被：', required: true, dimension: 'TF', optionA: '逻辑论证说服', optionB: '情感诉求打动' },
  { id: 'mbti_59', order: 59, type: 'choice', text: '你更重视：', required: true, dimension: 'TF', optionA: '效率和成果', optionB: '过程和体验' },
  { id: 'mbti_60', order: 60, type: 'choice', text: '当你需要给建议时：', required: true, dimension: 'TF', optionA: '给出客观分析', optionB: '考虑对方感受' },
  { id: 'mbti_61', order: 61, type: 'choice', text: '你更认同：', required: true, dimension: 'TF', optionA: '对事不对人', optionB: '人情味更重要' },
  { id: 'mbti_62', order: 62, type: 'choice', text: '处理冲突时，你倾向于：', required: true, dimension: 'TF', optionA: '就事论事解决问题', optionB: '先安抚情绪再处理' },
  { id: 'mbti_63', order: 63, type: 'choice', text: '你更希望别人：', required: true, dimension: 'TF', optionA: '认可你的能力', optionB: '认可你的为人' },
  { id: 'mbti_64', order: 64, type: 'choice', text: '在做选择时：', required: true, dimension: 'TF', optionA: '理性分析各种因素', optionB: '跟随内心感受' },
  { id: 'mbti_65', order: 65, type: 'choice', text: '你更看重朋友的：', required: true, dimension: 'TF', optionA: '诚实直接', optionB: '体贴温暖' },
  { id: 'mbti_66', order: 66, type: 'choice', text: '你的优势是：', required: true, dimension: 'TF', optionA: '客观公正', optionB: '善解人意' },
  { id: 'mbti_67', order: 67, type: 'choice', text: '当你不同意别人时：', required: true, dimension: 'TF', optionA: '会直接表达', optionB: '会委婉暗示' },
  { id: 'mbti_68', order: 68, type: 'choice', text: '你更关注：', required: true, dimension: 'TF', optionA: '事情对不对', optionB: '别人感受好不好' },
  { id: 'mbti_69', order: 69, type: 'choice', text: '你更喜欢：', required: true, dimension: 'TF', optionA: '清晰的逻辑', optionB: '温暖的氛围' },
  { id: 'mbti_70', order: 70, type: 'choice', text: '当需要做艰难决定时：', required: true, dimension: 'TF', optionA: '依靠理性分析', optionB: '依靠直觉感受' },

  // J/P 维度 - 判断/知觉 (23道)
  { id: 'mbti_71', order: 71, type: 'choice', text: '你更喜欢的生活方式是：', required: true, dimension: 'JP', optionA: '有计划、有组织的', optionB: '灵活、随性的' },
  { id: 'mbti_72', order: 72, type: 'choice', text: '当面对任务时，你通常：', required: true, dimension: 'JP', optionA: '提前规划按时完成', optionB: '临近截止日期才行动' },
  { id: 'mbti_73', order: 73, type: 'choice', text: '你更喜欢：', required: true, dimension: 'JP', optionA: '事情有定论', optionB: '保持开放选择' },
  { id: 'mbti_74', order: 74, type: 'choice', text: '在日程安排上，你倾向于：', required: true, dimension: 'JP', optionA: '详细计划每一天', optionB: '灵活应对变化' },
  { id: 'mbti_75', order: 75, type: 'choice', text: '当计划被打乱时，你会：', required: true, dimension: 'JP', optionA: '感到不安', optionB: '觉得没关系' },
  { id: 'mbti_76', order: 76, type: 'choice', text: '你的工作台通常：', required: true, dimension: 'JP', optionA: '整齐有序', optionB: '看似杂乱但自己能找到' },
  { id: 'mbti_77', order: 77, type: 'choice', text: '做决定时，你倾向于：', required: true, dimension: 'JP', optionA: '尽快做出决定', optionB: '收集更多信息再说' },
  { id: 'mbti_78', order: 78, type: 'choice', text: '你更喜欢：', required: true, dimension: 'JP', optionA: '按计划行事', optionB: '随机应变' },
  { id: 'mbti_79', order: 79, type: 'choice', text: '在旅行时，你倾向于：', required: true, dimension: 'JP', optionA: '提前规划好行程', optionB: '走到哪算哪' },
  { id: 'mbti_80', order: 80, type: 'choice', text: '你更喜欢的工作方式：', required: true, dimension: 'JP', optionA: '有明确的截止日期', optionB: '灵活的时间安排' },
  { id: 'mbti_81', order: 81, type: 'choice', text: '当你完成一件事时，你会：', required: true, dimension: 'JP', optionA: '感到满足，可以放松了', optionB: '开始想还有什么可以改进' },
  { id: 'mbti_82', order: 82, type: 'choice', text: '你的优势是：', required: true, dimension: 'JP', optionA: '按时完成任务', optionB: '适应变化' },
  { id: 'mbti_83', order: 83, type: 'choice', text: '你更喜欢：', required: true, dimension: 'JP', optionA: '确定的答案', optionB: '开放的问题' },
  { id: 'mbti_84', order: 84, type: 'choice', text: '在做项目时，你倾向于：', required: true, dimension: 'JP', optionA: '先做计划再执行', optionB: '边做边调整' },
  { id: 'mbti_85', order: 85, type: 'choice', text: '你更喜欢：', required: true, dimension: 'JP', optionA: '事先知道会发生什么', optionB: '惊喜和意外' },
  { id: 'mbti_86', order: 86, type: 'choice', text: '当你购物时：', required: true, dimension: 'JP', optionA: '列好清单按计划买', optionB: '随意逛看到喜欢就买' },
  { id: 'mbti_87', order: 87, type: 'choice', text: '你更喜欢：', required: true, dimension: 'JP', optionA: '快速做出决定', optionB: '保留选择权' },
  { id: 'mbti_88', order: 88, type: 'choice', text: '在时间管理上，你：', required: true, dimension: 'JP', optionA: '严格遵守时间表', optionB: '根据情况灵活调整' },
  { id: 'mbti_89', order: 89, type: 'choice', text: '你更喜欢：', required: true, dimension: 'JP', optionA: '完成一件事再开始下一件', optionB: '同时处理多件事' },
  { id: 'mbti_90', order: 90, type: 'choice', text: '当有多个选择时，你：', required: true, dimension: 'JP', optionA: '尽快确定一个', optionB: '尽量保持选择开放' },
  { id: 'mbti_91', order: 91, type: 'choice', text: '你的生活节奏：', required: true, dimension: 'JP', optionA: '有规律可预测', optionB: '多变有惊喜' },
  { id: 'mbti_92', order: 92, type: 'choice', text: '你更喜欢：', required: true, dimension: 'JP', optionA: '稳定的例行公事', optionB: '新鲜的变化' },
  { id: 'mbti_93', order: 93, type: 'choice', text: '在完成任务后，你通常：', required: true, dimension: 'JP', optionA: '检查确认后结束', optionB: '想着还有什么可以补充' },
];

// 导出所有预设题目
export const PRESET_QUESTIONS: Record<string, PresetQuestion[]> = {
  'EPQ': EPQ_QUESTIONS,
  'DISC': DISC_QUESTIONS,
  'MBTI': MBTI_QUESTIONS,
};

// 获取问卷题目数量
export const QUESTIONNAIRE_STATS = {
  EPQ: EPQ_QUESTIONS.length,    // 88
  DISC: DISC_QUESTIONS.length,  // 28
  MBTI: MBTI_QUESTIONS.length,  // 93
};

