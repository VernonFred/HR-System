export type QuestionnaireCopyMode = 'assessment' | 'answer'

export interface QuestionnaireCopySource {
  type?: string | null
  category?: string | null
  custom_type?: string | null
  purpose?: string | null
}

export interface QuestionnaireCopy {
  mode: QuestionnaireCopyMode
  noun: string
  startAction: string
  titleLabel: string
  namePlaceholder: string
  nameFallback: string
  descriptionLabel: string
  descriptionPlaceholder: string
  linkLabel: string
  qrAlt: string
  qrHint: string
  qrFileFallback: string
  entryTip: string
  contactAdminText: string
  expiredText: string
  notStartedText: string
  loadErrorTitle: string
  loadErrorFallback: string
  startErrorTitle: string
  startErrorFallback: string
  linkMissingText: string
  distributeTitle: string
  pageTexts: {
    welcomeText: string
    introText: string
    guideText: string
    privacyText: string
    showBasicInfoTitle: boolean
    successTitle: string
    successMessage: string
    resultText: string
    contactText: string
    showNextSteps: boolean
  }
}

const PROFESSIONAL_TYPES = new Set(['MBTI', 'DISC', 'EPQ'])

const normalize = (value?: string | null) => (value || '').trim().toLowerCase()
const normalizeUpper = (value?: string | null) => (value || '').trim().toUpperCase()

export const resolveQuestionnaireCopyMode = (
  source?: QuestionnaireCopySource | null,
): QuestionnaireCopyMode => {
  if (!source) return 'assessment'

  const type = normalizeUpper(source.type)
  const category = normalize(source.category)
  const customType = normalize(source.custom_type)
  const purpose = normalize(source.purpose)

  if (category === 'professional' || PROFESSIONAL_TYPES.has(type)) {
    return 'assessment'
  }

  if (purpose === 'survey') {
    return 'answer'
  }

  if (purpose === 'assessment') {
    return 'assessment'
  }

  if (category === 'survey' || customType === 'non_scored') {
    return 'answer'
  }

  return 'assessment'
}

const assessmentCopy: QuestionnaireCopy = {
  mode: 'assessment',
  noun: '测评',
  startAction: '开始测评',
  titleLabel: '测评名称',
  namePlaceholder: '例如：2024春季校招EPQ测评',
  nameFallback: '测评名称',
  descriptionLabel: '测评说明',
  descriptionPlaceholder: '请输入测评说明...',
  linkLabel: '测评链接',
  qrAlt: '测评二维码',
  qrHint: '扫码开始测评',
  qrFileFallback: '测评',
  entryTip: '请在安静的环境下完成测评，确保网络连接稳定',
  contactAdminText: '请联系管理员获取有效的测评链接',
  expiredText: '该测评已过期',
  notStartedText: '该测评暂未开始',
  loadErrorTitle: '加载测评失败',
  loadErrorFallback: '测评不存在或已失效',
  startErrorTitle: '开始测评失败',
  startErrorFallback: '开始测评失败，请重试',
  linkMissingText: '测评链接已失效或不存在',
  distributeTitle: '分发测评',
  pageTexts: {
    welcomeText: '欢迎参加本次测评',
    introText: '本测评旨在了解您的职业特质，帮助我们更好地为您匹配适合的岗位。',
    guideText: '请在安静的环境下完成，按照第一反应作答，没有对错之分。',
    privacyText: '您的信息将被严格保密，仅用于招聘评估目的。',
    showBasicInfoTitle: true,
    successTitle: '测评完成！',
    successMessage: '感谢您认真完成本次测评，您的回答对我们非常重要。',
    resultText: '我们将在 1-3 个工作日内完成评估分析。',
    contactText: '届时会通过您留下的联系方式通知您，请保持电话畅通。',
    showNextSteps: true,
  },
}

const answerCopy: QuestionnaireCopy = {
  mode: 'answer',
  noun: '答题',
  startAction: '开始答题',
  titleLabel: '答题名称',
  namePlaceholder: '例如：2024客户满意度问卷答题',
  nameFallback: '答题名称',
  descriptionLabel: '答题说明',
  descriptionPlaceholder: '请输入答题说明...',
  linkLabel: '答题链接',
  qrAlt: '答题二维码',
  qrHint: '扫码开始答题',
  qrFileFallback: '答题',
  entryTip: '请根据实际情况完成答题，确保网络连接稳定',
  contactAdminText: '请联系管理员获取有效的答题链接',
  expiredText: '该答题链接已过期',
  notStartedText: '该答题链接暂未开始',
  loadErrorTitle: '加载答题失败',
  loadErrorFallback: '答题链接不存在或已失效',
  startErrorTitle: '开始答题失败',
  startErrorFallback: '开始答题失败，请重试',
  linkMissingText: '答题链接已失效或不存在',
  distributeTitle: '分发答题',
  pageTexts: {
    welcomeText: '欢迎参加本次问卷答题',
    introText: '请根据实际情况填写本次问卷，您的反馈对我们非常重要。',
    guideText: '请按照真实想法作答，题目没有标准答案。',
    privacyText: '您的信息将被严格保密，仅用于本次问卷统计分析。',
    showBasicInfoTitle: true,
    successTitle: '答题完成！',
    successMessage: '感谢您完成本次答题，我们已收到您的答卷。',
    resultText: '我们会对收集到的答卷进行汇总分析。',
    contactText: '',
    showNextSteps: true,
  },
}

export const getQuestionnaireCopy = (
  source?: QuestionnaireCopySource | null,
): QuestionnaireCopy => {
  return resolveQuestionnaireCopyMode(source) === 'answer' ? answerCopy : assessmentCopy
}

export const formatQuestionnaireSystemMessage = (
  message: string,
  source?: QuestionnaireCopySource | null,
): string => {
  if (resolveQuestionnaireCopyMode(source) !== 'answer') return message
  return message
    .replace(/测评链接/g, '答题链接')
    .replace(/该测评/g, '该答题链接')
    .replace(/开始测评/g, '开始答题')
    .replace(/加载测评/g, '加载答题')
    .replace(/测评/g, '答题')
}
