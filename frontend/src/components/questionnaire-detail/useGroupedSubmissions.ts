import { computed, ref, watch, type ComputedRef, type Ref } from 'vue'
import type { Submission } from '../../api/assessments'

export interface GroupedCandidate {
  phone: string
  name: string
  submissions: Submission[]
  totalSubmissions: number
  latestSubmission: Submission | null
  completedCount: number
  __anonymousAggregate?: boolean
}

const ANONYMOUS_NAMES = new Set(['匿名', '未知', 'unknown', 'n/a', 'na', '-', '--', 'null', ''])

const isAnonymousSubmission = (name?: string, phone?: string) => {
  const safeName = (name || '').trim().toLowerCase()
  const safePhone = (phone || '').trim()
  if (safePhone) return false
  return !safeName || ANONYMOUS_NAMES.has(safeName)
}

const getLatestSubmission = (subs: Submission[]) => {
  let latest: Submission | null = null
  subs.forEach(sub => {
    const time = sub.submitted_at || sub.started_at
    if (!time) return
    if (!latest) {
      latest = sub
      return
    }
    const latestTime = latest.submitted_at || latest.started_at
    if (latestTime && new Date(time) > new Date(latestTime)) {
      latest = sub
    }
  })
  return latest
}

export function useGroupedSubmissions(
  filteredSubmissions: ComputedRef<Submission[]>,
  expandedCandidates: Ref<Set<string>>,
) {
  const groupPageSize = 10
  const groupPageMap = ref<Record<string, number>>({})
  const groupListPageSize = 10
  const groupListPage = ref(1)

  const getGroupKey = (group: GroupedCandidate) => {
    if (group.__anonymousAggregate) return '__anonymous__'
    return group.phone || group.name || 'unknown'
  }

  const getGroupDisplayName = (group: GroupedCandidate) => {
    if (group.__anonymousAggregate || isAnonymousSubmission(group.name, group.phone)) {
      return `匿名填写（${group.totalSubmissions}人）`
    }
    return group.name || '未知'
  }

  const getGroupInitial = (group: GroupedCandidate) => {
    const name = getGroupDisplayName(group)
    return name ? name[0].toUpperCase() : 'U'
  }

  const getGroupPage = (group: GroupedCandidate) => {
    return groupPageMap.value[getGroupKey(group)] || 1
  }

  const setGroupPage = (group: GroupedCandidate, page: number) => {
    groupPageMap.value = {
      ...groupPageMap.value,
      [getGroupKey(group)]: page,
    }
  }

  const getGroupTotalPages = (group: GroupedCandidate) => {
    return Math.max(1, Math.ceil(group.submissions.length / groupPageSize))
  }

  const getGroupSubmissions = (group: GroupedCandidate) => {
    const page = getGroupPage(group)
    const start = (page - 1) * groupPageSize
    return group.submissions.slice(start, start + groupPageSize)
  }

  const getGroupPendingCount = (group: GroupedCandidate) => {
    return Math.max(0, group.totalSubmissions - group.completedCount)
  }

  const changeGroupPage = (group: GroupedCandidate, page: number) => {
    const totalPages = getGroupTotalPages(group)
    if (page < 1 || page > totalPages) return
    setGroupPage(group, page)
  }

  const groupedSubmissions = computed<GroupedCandidate[]>(() => {
    const groups = new Map<string, GroupedCandidate>()
    const anonymousSubs = filteredSubmissions.value.filter(sub =>
      isAnonymousSubmission(sub.candidate_name, sub.candidate_phone),
    )

    if (anonymousSubs.length > 0) {
      groups.set('__anonymous__', {
        phone: '',
        name: `匿名填写（${anonymousSubs.length}人）`,
        submissions: anonymousSubs,
        totalSubmissions: anonymousSubs.length,
        latestSubmission: getLatestSubmission(anonymousSubs),
        completedCount: anonymousSubs.filter(s => s.status === 'completed').length,
        __anonymousAggregate: true,
      })
    }

    filteredSubmissions.value.forEach(sub => {
      if (isAnonymousSubmission(sub.candidate_name, sub.candidate_phone)) return
      const key = sub.candidate_phone || sub.candidate_name || 'unknown'

      if (!groups.has(key)) {
        groups.set(key, {
          phone: sub.candidate_phone || '',
          name: sub.candidate_name || '',
          submissions: [],
          totalSubmissions: 0,
          latestSubmission: null,
          completedCount: 0,
        })
      }

      const group = groups.get(key)!
      group.submissions.push(sub)
      group.totalSubmissions++
      if (sub.status === 'completed') group.completedCount++

      if (!group.latestSubmission ||
          (sub.submitted_at && group.latestSubmission.submitted_at &&
           new Date(sub.submitted_at) > new Date(group.latestSubmission.submitted_at))) {
        group.latestSubmission = sub
      }
    })

    return Array.from(groups.values()).sort((a, b) => {
      const timeA = a.latestSubmission?.submitted_at ? new Date(a.latestSubmission.submitted_at).getTime() : 0
      const timeB = b.latestSubmission?.submitted_at ? new Date(b.latestSubmission.submitted_at).getTime() : 0
      return timeB - timeA
    })
  })

  const groupListTotalPages = computed(() =>
    Math.ceil(groupedSubmissions.value.length / groupListPageSize) || 1,
  )

  const paginatedGroupedSubmissions = computed<GroupedCandidate[]>(() => {
    const start = (groupListPage.value - 1) * groupListPageSize
    return groupedSubmissions.value.slice(start, start + groupListPageSize)
  })

  const visibleGroupKeys = computed(() =>
    paginatedGroupedSubmissions.value.map(group => getGroupKey(group)),
  )

  const areVisibleGroupsExpanded = computed(() => {
    if (visibleGroupKeys.value.length === 0) return false
    return visibleGroupKeys.value.every(key => expandedCandidates.value.has(key))
  })

  const changeGroupListPage = (page: number) => {
    if (page < 1 || page > groupListTotalPages.value) return
    groupListPage.value = page
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
    getGroupKey,
    getGroupDisplayName,
    getGroupInitial,
    getGroupPage,
    setGroupPage,
    getGroupTotalPages,
    getGroupSubmissions,
    getGroupPendingCount,
    changeGroupPage,
    changeGroupListPage,
    groupedSubmissions,
    groupListTotalPages,
    paginatedGroupedSubmissions,
    visibleGroupKeys,
    areVisibleGroupsExpanded,
  }
}
