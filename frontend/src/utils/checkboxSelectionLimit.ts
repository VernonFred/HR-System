export interface CheckboxQuestionLike {
  maxSelections?: number | string | null
  max_selections?: number | string | null
  options?: unknown[] | null
}

export interface CheckboxSelectionResult {
  selection: string[]
  changed: boolean
  limitReached: boolean
}

const toPositiveInteger = (value: unknown): number | null => {
  if (value === null || value === undefined || value === '') return null

  const parsed = Number(value)
  if (!Number.isFinite(parsed) || parsed < 1) return null

  return Math.floor(parsed)
}

export const getCheckboxMaxSelections = (question?: CheckboxQuestionLike | null): number | null => {
  if (!question) return null

  const parsed = toPositiveInteger(question.maxSelections ?? question.max_selections)
  if (parsed === null) return null

  const optionCount = Array.isArray(question.options) ? question.options.length : 0
  return optionCount > 0 ? Math.min(parsed, optionCount) : parsed
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
