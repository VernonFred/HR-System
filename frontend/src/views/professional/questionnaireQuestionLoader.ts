import { fetchQuestionnaireDetail, type Questionnaire } from '../../api/assessments'
import { PRESET_QUESTIONS, type PresetQuestion } from '../../data/preset-questions'
import type { EditorQuestion } from '../../components/QuestionEditDialog.vue'

const mapPresetQuestion = (pq: PresetQuestion, idx: number): EditorQuestion => {
  let options: { label: string; value: string; score: number }[] = []

  if (pq.type === 'yesno') {
    options = [
      { label: '是', value: 'yes', score: pq.positive ? 1 : 0 },
      { label: '否', value: 'no', score: pq.positive ? 0 : 1 },
    ]
  } else if (pq.type === 'choice' && pq.optionA && pq.optionB) {
    options = [
      { label: pq.optionA, value: 'A', score: 1 },
      { label: pq.optionB, value: 'B', score: 0 },
    ]
  } else if (pq.options) {
    options = pq.options.map(opt => ({ label: opt.label, value: opt.value, score: 0 }))
  }

  return {
    id: pq.id,
    type: pq.type === 'yesno' ? 'yesno' : (pq.type === 'choice' ? 'radio' : pq.type),
    text: pq.text,
    required: pq.required,
    options,
    dimension: pq.dimension,
    positive: pq.positive,
    scale: pq.scale,
    optionA: pq.optionA,
    optionB: pq.optionB,
    scoreA: pq.optionA ? 1 : undefined,
    scoreB: pq.optionB ? 0 : undefined,
  }
}

const detectPresetKey = (questionnaire: Questionnaire | null): keyof typeof PRESET_QUESTIONS | null => {
  if (!questionnaire) return null
  const qName = questionnaire.name.toUpperCase()
  const qType = questionnaire.type?.toUpperCase() || ''
  if (qName.includes('EPQ') || qType.includes('EPQ')) return 'EPQ'
  if (qName.includes('DISC') || qType.includes('DISC')) return 'DISC'
  if (qName.includes('MBTI') || qType.includes('MBTI')) return 'MBTI'
  return null
}

export const loadProfessionalQuestionnaireQuestions = async (
  id: number,
  questionnaire: Questionnaire | null,
): Promise<EditorQuestion[]> => {
  const presetKey = detectPresetKey(questionnaire)
  if (presetKey) {
    return PRESET_QUESTIONS[presetKey].map(mapPresetQuestion)
  }

  const detail = await fetchQuestionnaireDetail(id)
  return detail.questions_data?.questions?.map((q: any, idx: number) => ({
    id: q.id || `q_${idx}`,
    type: q.type || 'radio',
    text: q.text || q.question || '',
    required: q.required !== false,
    options: q.options?.map((opt: any) => ({
      label: typeof opt === 'string' ? opt : opt.label,
      value: typeof opt === 'string' ? opt : opt.value,
      score: opt.score || opt.dimension_value || 0,
    })) || [],
    scale: q.scale,
    optionA: q.optionA,
    optionB: q.optionB,
    scoreA: q.scoreA,
    scoreB: q.scoreB,
  })) || []
}
