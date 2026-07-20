import assert from 'node:assert/strict'

import {
  buildQuestionnaireLibraryQuery,
  getPaginationItems,
  hasActiveQuestionnaireLibraryFilters,
  reorderQuestionnaireLibraryItems,
  normalizeQuestionnaireLibraryPage,
} from '../src/utils/questionnaireLibrary'

const query = buildQuestionnaireLibraryQuery({
  page: 3,
  pageSize: 12,
  libraryCategoryId: 7,
  tagIds: [4, 9],
  creator: ' Wang_jun ',
  status: 'active',
  customType: 'scored',
  keyword: ' 培训 ',
  sort: 'created_desc',
})

assert.deepEqual(query, {
  skip: 24,
  limit: 12,
  category: 'custom',
  library_category_id: 7,
  tag_ids: [4, 9],
  creator: 'Wang_jun',
  status: 'active',
  custom_type: 'scored',
  keyword: '培训',
  sort: 'created_desc',
})

assert.deepEqual(
  buildQuestionnaireLibraryQuery({
    page: 0,
    pageSize: 0,
    libraryCategoryId: null,
    tagIds: [],
    creator: ' ',
    status: 'all',
    customType: 'all',
    keyword: '',
    sort: 'updated_desc',
  }),
  { skip: 0, limit: 12, category: 'custom', sort: 'updated_desc' },
)

assert.equal(normalizeQuestionnaireLibraryPage(5, 0, 12), 1)
assert.equal(normalizeQuestionnaireLibraryPage(5, 13, 12), 2)
assert.equal(normalizeQuestionnaireLibraryPage(0, 100, 12), 1)

assert.deepEqual(getPaginationItems(1, 1), [1])
assert.deepEqual(getPaginationItems(1, 8), [1, 2, 3, 4, 5, 'ellipsis', 8])
assert.deepEqual(getPaginationItems(4, 8), [1, 2, 3, 4, 5, 6, 'ellipsis', 8])
assert.deepEqual(getPaginationItems(8, 8), [1, 'ellipsis', 4, 5, 6, 7, 8])

assert.equal(
  hasActiveQuestionnaireLibraryFilters({
    libraryCategoryId: null,
    tagIds: [],
    creator: '',
    status: 'all',
    customType: 'all',
    keyword: '',
    sort: 'updated_desc',
  }),
  false,
)
assert.equal(
  hasActiveQuestionnaireLibraryFilters({
    libraryCategoryId: null,
    tagIds: [4],
    creator: '',
    status: 'all',
    customType: 'all',
    keyword: '',
    sort: 'updated_desc',
  }),
  true,
)

const originalCategoryOrder = [11, 22, 33, 44]
assert.deepEqual(reorderQuestionnaireLibraryItems(originalCategoryOrder, 1, 3), [11, 33, 44, 22])
assert.deepEqual(reorderQuestionnaireLibraryItems(originalCategoryOrder, 3, 0), [44, 11, 22, 33])
assert.deepEqual(reorderQuestionnaireLibraryItems(originalCategoryOrder, -1, 2), originalCategoryOrder)
assert.deepEqual(reorderQuestionnaireLibraryItems(originalCategoryOrder, 0, 8), originalCategoryOrder)
assert.deepEqual(originalCategoryOrder, [11, 22, 33, 44])

console.log('questionnaire library utilities: all assertions passed')
