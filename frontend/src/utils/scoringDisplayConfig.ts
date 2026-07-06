export type ScoringDisplayPreset = 'survey_feedback' | 'assessment_rating' | 'exam_score' | 'custom'

export interface ScoringDisplayConfig {
  preset: ScoringDisplayPreset
  distributionTitle: string
  rateLabel: string
  unitLabel: string
  averageLabel: string
}

export interface GradeConfigItem {
  grade?: string
  name?: string
  label?: string
  minScore?: number
  maxScore?: number
  min_score?: number
  max_score?: number
  color?: string
}

export interface DistributionRow {
  grade: string
  label: string
  minScore: number
  maxScore: number
  count: number
  color: string
}

type ScoringConfigLike = {
  displayConfig?: Partial<ScoringDisplayConfig> & { displayName?: string; display_name?: string }
  display_config?: Partial<ScoringDisplayConfig> & { displayName?: string; display_name?: string }
  gradeConfig?: GradeConfigItem[]
  grades?: GradeConfigItem[]
}

const GRADE_COLORS: Record<string, string> = {
  A: '#10b981',
  B: '#3b82f6',
  C: '#f59e0b',
  D: '#ef4444',
}

const DISPLAY_DEFAULTS: Record<ScoringDisplayPreset, ScoringDisplayConfig> = {
  survey_feedback: {
    preset: 'survey_feedback',
    distributionTitle: '课程评价分布',
    rateLabel: '高认可率',
    unitLabel: '份答卷',
    averageLabel: '课程综合评分',
  },
  assessment_rating: {
    preset: 'assessment_rating',
    distributionTitle: '测评等级分布',
    rateLabel: '优良率',
    unitLabel: '人',
    averageLabel: '测评平均分',
  },
  exam_score: {
    preset: 'exam_score',
    distributionTitle: '考试成绩分布',
    rateLabel: '通过率',
    unitLabel: '人',
    averageLabel: '考试平均分',
  },
  custom: {
    preset: 'custom',
    distributionTitle: '得分分布',
    rateLabel: '高分率',
    unitLabel: '份',
    averageLabel: '平均分',
  },
}

export const createDefaultDisplayConfig = (purpose?: string | null): ScoringDisplayConfig => {
  if (purpose === 'assessment') return { ...DISPLAY_DEFAULTS.assessment_rating }
  if (purpose === 'exam') return { ...DISPLAY_DEFAULTS.exam_score }
  return { ...DISPLAY_DEFAULTS.survey_feedback }
}

export const createDefaultGradeConfig = (purpose?: string | null): GradeConfigItem[] => {
  const labels = purpose === 'assessment'
    ? ['优秀', '良好', '合格', '待提升']
    : purpose === 'exam'
      ? ['优秀', '良好', '及格', '不及格']
      : ['高度认可', '整体满意', '基本认可', '需重点改进']

  return [
    { grade: 'A', label: labels[0], minScore: 90, maxScore: 100 },
    { grade: 'B', label: labels[1], minScore: 75, maxScore: 89 },
    { grade: 'C', label: labels[2], minScore: 60, maxScore: 74 },
    { grade: 'D', label: labels[3], minScore: 0, maxScore: 59 },
  ]
}

export const buildScoringDisplayConfig = ({
  purpose,
  scoringConfig,
}: {
  purpose?: string | null
  scoringConfig?: ScoringConfigLike | null
}): ScoringDisplayConfig => {
  const rawDisplay = scoringConfig?.displayConfig || scoringConfig?.display_config || {}
  const preset = rawDisplay.preset || createDefaultDisplayConfig(purpose).preset
  const base = preset in DISPLAY_DEFAULTS
    ? DISPLAY_DEFAULTS[preset as ScoringDisplayPreset]
    : createDefaultDisplayConfig(purpose)

  return {
    preset: (rawDisplay.preset as ScoringDisplayPreset) || base.preset,
    distributionTitle:
      rawDisplay.distributionTitle ||
      rawDisplay.displayName ||
      rawDisplay.display_name ||
      base.distributionTitle,
    rateLabel: rawDisplay.rateLabel || base.rateLabel,
    unitLabel: rawDisplay.unitLabel || base.unitLabel,
    averageLabel: rawDisplay.averageLabel || base.averageLabel,
  }
}

export const normalizeGradeConfig = (
  scoringConfig?: ScoringConfigLike | null,
  purpose?: string | null,
): GradeConfigItem[] => {
  const rawGrades = scoringConfig?.gradeConfig || scoringConfig?.grades
  const hasDisplayConfig = Boolean(scoringConfig?.displayConfig || scoringConfig?.display_config)
  const defaultGrades = createDefaultGradeConfig(purpose)
  if (Array.isArray(rawGrades) && rawGrades.length > 0) {
    return rawGrades.map((item, index) => ({
      grade: item.grade || item.name || String.fromCharCode(65 + index),
      label: hasDisplayConfig
        ? item.label || item.grade || item.name || String.fromCharCode(65 + index)
        : defaultGrades[index]?.label || item.label || item.grade || item.name || String.fromCharCode(65 + index),
      minScore: item.minScore ?? item.min_score ?? 0,
      maxScore: item.maxScore ?? item.max_score ?? 0,
      color: item.color,
    }))
  }
  return createDefaultGradeConfig(purpose)
}

export const getDistributionRows = (
  scoringConfig: ScoringConfigLike | null | undefined,
  gradeDistribution: Record<string, number>,
  purpose?: string | null,
): DistributionRow[] => {
  return normalizeGradeConfig(scoringConfig, purpose).map((item, index) => {
    const grade = String(item.grade || item.name || String.fromCharCode(65 + index)).toUpperCase()
    return {
      grade,
      label: item.label || grade,
      minScore: Number(item.minScore ?? item.min_score ?? 0),
      maxScore: Number(item.maxScore ?? item.max_score ?? 0),
      count: Number(gradeDistribution[grade] || 0),
      color: item.color || GRADE_COLORS[grade] || '#64748b',
    }
  })
}
