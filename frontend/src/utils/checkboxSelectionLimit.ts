export interface CheckboxQuestionLike {
  selectionRule?: CheckboxSelectionRuleMode | string | null
  selection_rule?: CheckboxSelectionRuleMode | string | null
  minSelections?: number | string | null
  min_selections?: number | string | null
  maxSelections?: number | string | null
  max_selections?: number | string | null
  options?: unknown[] | null
}

export type CheckboxSelectionRuleMode = 'none' | 'max' | 'min' | 'exact' | 'range'

export interface CheckboxSelectionRule {
  mode: CheckboxSelectionRuleMode
  minSelections: number | null
  maxSelections: number | null
  label: string
  counterText: string
}

export interface CheckboxSelectionResult {
  selection: string[]
  changed: boolean
  limitReached: boolean
}

export interface CheckboxValidationResult {
  valid: boolean
  message: string
  selectedCount: number
}

const toPositiveInteger = (value: unknown): number | null => {
  if (value === null || value === undefined || value === '') return null

  const parsed = Number(value)
  if (!Number.isFinite(parsed) || parsed < 1) return null

  return Math.floor(parsed)
}

const normalizeMode = (mode: unknown): CheckboxSelectionRuleMode | null => {
  if (mode === 'none' || mode === 'max' || mode === 'min' || mode === 'exact' || mode === 'range') {
    return mode
  }
  return null
}

const clampToOptionCount = (value: number | null, optionCount: number): number | null => {
  if (value === null) return null
  return optionCount > 0 ? Math.min(value, optionCount) : value
}

const inferModeFromBounds = (
  minSelections: number | null,
  maxSelections: number | null,
): CheckboxSelectionRuleMode => {
  if (minSelections && maxSelections) return minSelections === maxSelections ? 'exact' : 'range'
  if (minSelections) return 'min'
  if (maxSelections) return 'max'
  return 'none'
}

const buildRuleCopy = (
  mode: CheckboxSelectionRuleMode,
  minSelections: number | null,
  maxSelections: number | null,
) => {
  if (mode === 'exact' && minSelections) {
    return { label: `必须选择 ${minSelections} 项`, counterText: `必须 ${minSelections} 项` }
  }
  if (mode === 'range' && minSelections && maxSelections) {
    return { label: `请选择 ${minSelections} 至 ${maxSelections} 项`, counterText: `${minSelections} 至 ${maxSelections} 项` }
  }
  if (mode === 'min' && minSelections) {
    return { label: `至少选择 ${minSelections} 项`, counterText: `至少 ${minSelections} 项` }
  }
  if (mode === 'max' && maxSelections) {
    return { label: `最多选择 ${maxSelections} 项`, counterText: `最多 ${maxSelections} 项` }
  }
  if (minSelections) {
    return { label: `至少选择 ${minSelections} 项`, counterText: `至少 ${minSelections} 项` }
  }
  return { label: '', counterText: '' }
}

export const getCheckboxSelectionRule = (
  question?: CheckboxQuestionLike | null,
  required = false,
): CheckboxSelectionRule => {
  if (!question) {
    return {
      mode: 'none',
      minSelections: null,
      maxSelections: null,
      label: '',
      counterText: '',
    }
  }
  const optionCount = Array.isArray(question.options) ? question.options.length : 0
  const configuredMode = normalizeMode(question.selectionRule ?? question.selection_rule)
  const rawMin = toPositiveInteger(question.minSelections ?? question.min_selections)
  const rawMax = toPositiveInteger(question.maxSelections ?? question.max_selections)

  const mode = configuredMode ?? inferModeFromBounds(rawMin, rawMax)
  let minSelections: number | null = null
  let maxSelections: number | null = null

  if (mode === 'max') {
    maxSelections = clampToOptionCount(rawMax, optionCount)
    minSelections = required ? clampToOptionCount(1, optionCount) : null
  } else if (mode === 'min') {
    minSelections = clampToOptionCount(rawMin, optionCount)
  } else if (mode === 'exact') {
    const exactSelections = clampToOptionCount(rawMin ?? rawMax, optionCount)
    minSelections = exactSelections
    maxSelections = exactSelections
  } else if (mode === 'range') {
    minSelections = clampToOptionCount(rawMin, optionCount)
    maxSelections = clampToOptionCount(rawMax, optionCount)
  } else if (required) {
    minSelections = clampToOptionCount(1, optionCount)
  }

  const copy = buildRuleCopy(mode, minSelections, maxSelections)
  return { mode, minSelections, maxSelections, ...copy }
}

export const getCheckboxMaxSelections = (question?: CheckboxQuestionLike | null): number | null => {
  return getCheckboxSelectionRule(question).maxSelections
}

export const toggleCheckboxSelection = (
  currentSelection: unknown,
  value: string,
  maxSelections?: number | null,
): CheckboxSelectionResult => {
  const selection = Array.isArray(currentSelection)
    ? currentSelection.map(item => String(item))
    : []
  const normalizedValue = String(value)
  const existingIndex = selection.indexOf(normalizedValue)

  if (existingIndex >= 0) {
    const nextSelection = [...selection]
    nextSelection.splice(existingIndex, 1)
    return { selection: nextSelection, changed: true, limitReached: false }
  }

  if (maxSelections && selection.length >= maxSelections) {
    return { selection, changed: false, limitReached: true }
  }

  return {
    selection: [...selection, normalizedValue],
    changed: true,
    limitReached: false,
  }
}

export const validateCheckboxSelection = (
  question: CheckboxQuestionLike | null | undefined,
  currentSelection: unknown,
  required = false,
): CheckboxValidationResult => {
  const selectedCount = Array.isArray(currentSelection) ? currentSelection.length : 0
  const rule = getCheckboxSelectionRule(question, required)

  if (rule.minSelections && selectedCount < rule.minSelections) {
    if (rule.mode === 'exact') {
      return { valid: false, message: `本题必须选择 ${rule.minSelections} 项`, selectedCount }
    }
    if (rule.mode === 'range' && rule.maxSelections) {
      return { valid: false, message: `本题需要选择 ${rule.minSelections} 至 ${rule.maxSelections} 项`, selectedCount }
    }
    return { valid: false, message: `本题至少需要选择 ${rule.minSelections} 项`, selectedCount }
  }

  if (rule.maxSelections && selectedCount > rule.maxSelections) {
    if (rule.mode === 'exact') {
      return { valid: false, message: `本题必须选择 ${rule.maxSelections} 项`, selectedCount }
    }
    if (rule.mode === 'range' && rule.minSelections) {
      return { valid: false, message: `本题需要选择 ${rule.minSelections} 至 ${rule.maxSelections} 项`, selectedCount }
    }
    return { valid: false, message: `本题最多可选择 ${rule.maxSelections} 项`, selectedCount }
  }

  return { valid: true, message: '', selectedCount }
}
