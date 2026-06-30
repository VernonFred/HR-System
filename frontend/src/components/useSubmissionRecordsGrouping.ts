import { computed, ref, watch, type ComputedRef, type Ref } from 'vue'
import type { Submission } from '../api/assessments'

export type DisplaySubmission = Submission & {
  __anonymousAggregate?: boolean
  anonymous_count?: number
}

export interface GroupedCandidate {
  phone: string
  name: string
  totalSubmissions: number
  completedCount: number
  latestSubmission: Submission | null
  submissions: Submission[]
}

const isEmptyIdentity = (value?: string) => {
  const normalized = (value || '').trim().toLowerCase()
  if (!normalized) return true
  return ['匿名', '未知', 'unknown', 'n/a', 'na', '-', '—', '--', 'null'].includes(normalized)
}

const isAnonymousSubmission = (name?: string, phone?: string) => {
  if (!isEmptyIdentity(phone)) return false
  return isEmptyIdentity(name)
}

const getSubmissionTime = (submission: Submission) => {
  return submission.submitted_at || submission.started_at || ''
}

const getLatestSubmission = (subs: Submission[]) => {
  let latest: Submission | null = null
  for (const sub of subs) {
    const time = getSubmissionTime(sub)
    if (!time) continue
    if (!latest || new Date(time) > new Date(getSubmissionTime(latest))) {
      latest = sub
    }
  }
  return latest || subs[0] || null
}

export const isAggregateSubmission = (submission: Submission | DisplaySubmission) => {
  return Boolean((submission as DisplaySubmission).__anonymousAggregate)
}

export function useSubmissionRecordsGrouping(
  filteredSubmissions: ComputedRef<Submission[]>,
  expandedCandidates: Ref<Set<string>>,
) {
  const groupPageSize = 10
  const groupPage = ref<Record<string, number>>({})
  const groupListPageSize = 10
  const groupListPage = ref(1)

  const getGroupKey = (group: GroupedCandidate) => group.phone || group.name || 'unknown'

  const getGroupDisplayName = (group: GroupedCandidate) => {
    if (isAnonymousSubmission(group.name, group.phone)) {
      return `匿名填写（${group.totalSubmissions}人）`
    }
    return group.name || '未知'
  }

  const anonymousSubmissions = computed(() =>
    filteredSubmissions.value.filter(s => isAnonymousSubmission(s.candidate_name, s.candidate_phone)),
  )

  const displaySubmissions = computed<DisplaySubmission[]>(() => {
    const anonSubs = anonymousSubmissions.value
    const normalSubs = filteredSubmissions.value.filter(
      s => !isAnonymousSubmission(s.candidate_name, s.candidate_phone),
    )

    if (anonSubs.length === 0) return normalSubs

    const questionnaireNames = Array.from(
      new Set(anonSubs.map(s => s.questionnaire_name).filter(Boolean)),
    )
    const questionnaireName = questionnaireNames.length === 1 ? questionnaireNames[0] : '多个问卷'
    const latestSubmission = getLatestSubmission(anonSubs)
    const latestTime = latestSubmission ? getSubmissionTime(latestSubmission) : ''

    const aggregate: DisplaySubmission = {
      id: -1,
      code: `ANON-${anonSubs.length}`,
      candidate_name: `匿名填写（${anonSubs.length}人）`,
      candidate_phone: '',
      questionnaire_name: questionnaireName || '匿名提交',
      questionnaire_type: questionnaireNames.length === 1 ? anonSubs[0]?.questionnaire_type : undefined,
      status: 'anonymous',
      started_at: latestTime || new Date().toISOString(),
      submitted_at: latestTime || undefined,
      __anonymousAggregate: true,
      anonymous_count: anonSubs.length,
    }

    return [aggregate, ...normalSubs]
  })

  const selectableSubmissions = computed(() =>
    displaySubmissions.value.filter(s => !isAggregateSubmission(s)),
  )

  const getGroupPage = (key: string) => groupPage.value[key] || 1

  const setGroupPage = (key: string, page: number) => {
    groupPage.value = { ...groupPage.value, [key]: page }
  }

  const getGroupTotalPages = (group: GroupedCandidate) =>
    Math.max(1, Math.ceil(group.submissions.length / groupPageSize))

  const getGroupSubmissions = (group: GroupedCandidate) => {
    const key = getGroupKey(group)
    const page = getGroupPage(key)
    const start = (page - 1) * groupPageSize
    return group.submissions.slice(start, start + groupPageSize)
  }

  const changeGroupPage = (group: GroupedCandidate, nextPage: number) => {
    const key = getGroupKey(group)
    const total = getGroupTotalPages(group)
    if (nextPage < 1 || nextPage > total) return
    setGroupPage(key, nextPage)
  }

  const groupedSubmissionsAll = computed<GroupedCandidate[]>(() => {
    const groups = new Map<string, GroupedCandidate>()
    const anonSubs = anonymousSubmissions.value

    if (anonSubs.length > 0) {
      groups.set('__anonymous__', {
        phone: '',
        name: `匿名填写（${anonSubs.length}人）`,
        totalSubmissions: anonSubs.length,
        completedCount: anonSubs.filter(s => s.status === 'completed').length,
        latestSubmission: getLatestSubmission(anonSubs),
        submissions: anonSubs,
      })
    }

    for (const sub of filteredSubmissions.value) {
      if (isAnonymousSubmission(sub.candidate_name, sub.candidate_phone)) continue
      const key = sub.candidate_phone || sub.candidate_name || 'unknown'

      if (!groups.has(key)) {
        groups.set(key, {
          phone: sub.candidate_phone || '',
          name: sub.candidate_name || '未知',
          totalSubmissions: 0,
          completedCount: 0,
          latestSubmission: null,
          submissions: [],
        })
      }

      const group = groups.get(key)!
      group.totalSubmissions++
      if (sub.status === 'completed') group.completedCount++
      group.submissions.push(sub)

      if (!group.latestSubmission ||
          (sub.submitted_at && group.latestSubmission.submitted_at &&
           new Date(sub.submitted_at) > new Date(group.latestSubmission.submitted_at))) {
        group.latestSubmission = sub
      }
    }

    return Array.from(groups.values()).sort((a, b) => {
      const timeA = a.latestSubmission?.submitted_at ? new Date(a.latestSubmission.submitted_at).getTime() : 0
      const timeB = b.latestSubmission?.submitted_at ? new Date(b.latestSubmission.submitted_at).getTime() : 0
      return timeB - timeA
    })
  })

  const groupListTotalPages = computed(() => Math.ceil(groupedSubmissionsAll.value.length / groupListPageSize) || 1)

  const getGroupPendingCount = (group: GroupedCandidate) => {
    return Math.max(0, group.totalSubmissions - group.completedCount)
  }

  const paginatedGroupedSubmissions = computed<GroupedCandidate[]>(() => {
    const start = (groupListPage.value - 1) * groupListPageSize
    return groupedSubmissionsAll.value.slice(start, start + groupListPageSize)
  })

  const visibleGroupKeys = computed(() =>
    paginatedGroupedSubmissions.value.map(group => getGroupKey(group)),
  )

  const areVisibleGroupsExpanded = computed(() => {
    if (visibleGroupKeys.value.length === 0) return false
    return visibleGroupKeys.value.every(key => expandedCandidates.value.has(key))
  })

  const changeGroupListPage = (newPage: number) => {
    if (newPage < 1 || newPage > groupListTotalPages.value) return
    groupListPage.value = newPage
  }

  watch(filteredSubmissions, () => {
    groupListPage.value = 1
  })

  watch(groupListTotalPages, total => {
    if (groupListPage.value > total) {
      groupListPage.value = total
    }
  })

  return {
    groupPageSize,
    groupListPageSize,
    groupListPage,
    displaySubmissions,
    selectableSubmissions,
    isAggregateSubmission,
    getGroupKey,
    getGroupDisplayName,
    getGroupPage,
    setGroupPage,
    getGroupTotalPages,
    getGroupSubmissions,
    changeGroupPage,
    changeGroupListPage,
    groupedSubmissionsAll,
    groupListTotalPages,
    getGroupPendingCount,
    paginatedGroupedSubmissions,
    visibleGroupKeys,
    areVisibleGroupsExpanded,
  }
}
