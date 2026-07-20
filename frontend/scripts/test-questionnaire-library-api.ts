import assert from 'node:assert/strict'

import {
  buildQuestionnaireListSearch,
  QUESTIONNAIRE_LIBRARY_API_PATHS,
} from '../src/api/assessmentTypes'

assert.equal(QUESTIONNAIRE_LIBRARY_API_PATHS.base, '/api/assessments/library')
assert.equal(QUESTIONNAIRE_LIBRARY_API_PATHS.categories, '/api/assessments/library/categories')
assert.equal(
  QUESTIONNAIRE_LIBRARY_API_PATHS.reorderCategories,
  '/api/assessments/library/categories/reorder',
)
assert.equal(QUESTIONNAIRE_LIBRARY_API_PATHS.category(12), '/api/assessments/library/categories/12')
assert.equal(QUESTIONNAIRE_LIBRARY_API_PATHS.tags, '/api/assessments/library/tags')
assert.equal(QUESTIONNAIRE_LIBRARY_API_PATHS.tag(8), '/api/assessments/library/tags/8')
assert.equal(QUESTIONNAIRE_LIBRARY_API_PATHS.mergeTag(8), '/api/assessments/library/tags/8/merge')
assert.equal(QUESTIONNAIRE_LIBRARY_API_PATHS.creators, '/api/assessments/library/creators')
assert.equal(
  QUESTIONNAIRE_LIBRARY_API_PATHS.bulkCategory,
  '/api/assessments/questionnaires/bulk-library-category',
)

const search = buildQuestionnaireListSearch({
  skip: 24,
  limit: 12,
  category: 'custom',
  library_category_id: 7,
  tag_ids: [4, 9, 4],
  creator: ' Wang_jun ',
  status: 'active',
  custom_type: 'scored',
  keyword: ' 培训 ',
  sort: 'created_desc',
})

assert.equal(search.get('skip'), '24')
assert.equal(search.get('limit'), '12')
assert.equal(search.get('category'), 'custom')
assert.equal(search.get('library_category_id'), '7')
assert.deepEqual(search.getAll('tag_ids'), ['4', '9'])
assert.equal(search.get('creator'), 'Wang_jun')
assert.equal(search.get('status'), 'active')
assert.equal(search.get('custom_type'), 'scored')
assert.equal(search.get('keyword'), '培训')
assert.equal(search.get('sort'), 'created_desc')

const defaults = buildQuestionnaireListSearch({ skip: 0, limit: 12, tag_ids: [] })
assert.equal(defaults.get('skip'), '0')
assert.equal(defaults.get('limit'), '12')
assert.equal(defaults.has('tag_ids'), false)

console.log('questionnaire library API query tests passed')
