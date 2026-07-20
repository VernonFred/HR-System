export type QuestionnaireLibraryStatusFilter = 'all' | 'active' | 'inactive'
export type QuestionnaireLibraryTypeFilter = 'all' | 'scored' | 'non_scored'
export type QuestionnaireLibrarySort = 'updated_desc' | 'created_desc'
export type QuestionnairePaginationItem = number | 'ellipsis'

export interface QuestionnaireLibraryFilterState {
  libraryCategoryId: number | null
  tagIds: number[]
  creator: string
  status: QuestionnaireLibraryStatusFilter
  customType: QuestionnaireLibraryTypeFilter
  keyword: string
  sort: QuestionnaireLibrarySort
}

export interface QuestionnaireLibraryQueryState extends QuestionnaireLibraryFilterState {
  page: number
  pageSize: number
}

export interface QuestionnaireLibraryQuery {
  skip: number
  limit: number
  category: 'custom'
  library_category_id?: number
  tag_ids?: number[]
  creator?: string
  status?: 'active' | 'inactive'
  custom_type?: 'scored' | 'non_scored'
  keyword?: string
  sort: QuestionnaireLibrarySort
}

const toPositiveInteger = (value: number, fallback: number) => {
  const normalized = Math.trunc(value)
  return normalized > 0 ? normalized : fallback
}

export function buildQuestionnaireLibraryQuery(
  state: QuestionnaireLibraryQueryState,
): QuestionnaireLibraryQuery {
  const page = toPositiveInteger(state.page, 1)
  const pageSize = toPositiveInteger(state.pageSize, 12)
  const query: QuestionnaireLibraryQuery = {
    skip: (page - 1) * pageSize,
    limit: pageSize,
    category: 'custom',
    sort: state.sort,
  }

  if (state.libraryCategoryId !== null) query.library_category_id = state.libraryCategoryId
  if (state.tagIds.length) query.tag_ids = [...new Set(state.tagIds)]

  const creator = state.creator.trim()
  const keyword = state.keyword.trim()
  if (creator) query.creator = creator
  if (keyword) query.keyword = keyword
  if (state.status !== 'all') query.status = state.status
  if (state.customType !== 'all') query.custom_type = state.customType

  return query
}

export function normalizeQuestionnaireLibraryPage(
  requestedPage: number,
  total: number,
  pageSize: number,
) {
  const normalizedPageSize = toPositiveInteger(pageSize, 12)
  const totalPages = Math.max(1, Math.ceil(Math.max(0, total) / normalizedPageSize))
  return Math.min(Math.max(1, Math.trunc(requestedPage) || 1), totalPages)
}

export function getPaginationItems(
  currentPage: number,
  totalPages: number,
): QuestionnairePaginationItem[] {
  const total = Math.max(1, Math.trunc(totalPages) || 1)
  const current = Math.min(Math.max(1, Math.trunc(currentPage) || 1), total)

  if (total <= 7) return Array.from({ length: total }, (_, index) => index + 1)

  let start = Math.max(2, current - 2)
  let end = Math.min(total - 1, current + 2)
  if (current <= 3) end = 5
  else if (current === 4) end = 6
  if (current >= total - 3) start = total - 4

  const items: QuestionnairePaginationItem[] = [1]
  if (start > 2) items.push('ellipsis')
  for (let page = start; page <= end; page += 1) items.push(page)
  if (end < total - 1) items.push('ellipsis')
  items.push(total)
  return items
}

export function hasActiveQuestionnaireLibraryFilters(
  state: QuestionnaireLibraryFilterState,
) {
  return Boolean(
    state.libraryCategoryId !== null
      || state.tagIds.length
      || state.creator.trim()
      || state.status !== 'all'
      || state.customType !== 'all'
      || state.keyword.trim()
      || state.sort !== 'updated_desc',
  )
}
