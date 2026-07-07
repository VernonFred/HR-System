import assert from 'node:assert/strict'

import {
  getCheckboxMaxSelections,
  getCheckboxSelectionRule,
  toggleCheckboxSelection,
  validateCheckboxSelection,
} from '../src/utils/checkboxSelectionLimit'

const options = [
  { value: 'a', label: 'A' },
  { value: 'b', label: 'B' },
  { value: 'c', label: 'C' },
]

assert.equal(getCheckboxMaxSelections({ maxSelections: 2, options }), 2)
assert.equal(getCheckboxMaxSelections({ max_selections: '3', options }), 3)
assert.equal(getCheckboxMaxSelections({ maxSelections: 0, options }), null)
assert.equal(getCheckboxMaxSelections({ maxSelections: 10, options }), 3)
assert.equal(getCheckboxMaxSelections({ selectionRule: 'min', minSelections: 2, options }), null)
assert.equal(getCheckboxMaxSelections({ selection_rule: 'exact', min_selections: '2', max_selections: '2', options }), 2)

assert.deepEqual(
  getCheckboxSelectionRule({ options }, false),
  {
    mode: 'none',
    minSelections: null,
    maxSelections: null,
    label: '',
    counterText: '',
  },
)

assert.deepEqual(
  getCheckboxSelectionRule({ options }, true),
  {
    mode: 'none',
    minSelections: 1,
    maxSelections: null,
    label: '至少选择 1 项',
    counterText: '至少 1 项',
  },
)

assert.deepEqual(
  getCheckboxSelectionRule({ selectionRule: 'max', maxSelections: 2, options }, false),
  {
    mode: 'max',
    minSelections: null,
    maxSelections: 2,
    label: '最多选择 2 项',
    counterText: '最多 2 项',
  },
)

assert.deepEqual(
  getCheckboxSelectionRule({ selectionRule: 'min', minSelections: 2, options }, false),
  {
    mode: 'min',
    minSelections: 2,
    maxSelections: null,
    label: '至少选择 2 项',
    counterText: '至少 2 项',
  },
)

assert.deepEqual(
  getCheckboxSelectionRule({ selectionRule: 'exact', minSelections: 2, maxSelections: 2, options }, false),
  {
    mode: 'exact',
    minSelections: 2,
    maxSelections: 2,
    label: '必须选择 2 项',
    counterText: '必须 2 项',
  },
)

assert.deepEqual(
  getCheckboxSelectionRule({ selection_rule: 'range', min_selections: '2', max_selections: '3', options }, false),
  {
    mode: 'range',
    minSelections: 2,
    maxSelections: 3,
    label: '请选择 2 至 3 项',
    counterText: '2 至 3 项',
  },
)

assert.equal(getCheckboxSelectionRule({ min_selections: '2', options }).mode, 'min')
assert.equal(getCheckboxSelectionRule({ min_selections: '2', max_selections: '2', options }).mode, 'exact')
assert.equal(getCheckboxSelectionRule({ min_selections: '2', max_selections: '3', options }).mode, 'range')

assert.deepEqual(
  toggleCheckboxSelection(['a'], 'b', null),
  { selection: ['a', 'b'], changed: true, limitReached: false },
)

assert.deepEqual(
  toggleCheckboxSelection(['a', 'b'], 'c', 2),
  { selection: ['a', 'b'], changed: false, limitReached: true },
)

assert.deepEqual(
  toggleCheckboxSelection(['a', 'b'], 'b', 2),
  { selection: ['a'], changed: true, limitReached: false },
)

assert.deepEqual(
  toggleCheckboxSelection(['a', 'b'], 'a', 1),
  { selection: ['b'], changed: true, limitReached: false },
)

assert.deepEqual(
  toggleCheckboxSelection(['a', 'b'], 'c', getCheckboxSelectionRule({ selectionRule: 'min', minSelections: 2, options }).maxSelections),
  { selection: ['a', 'b', 'c'], changed: true, limitReached: false },
)

assert.deepEqual(
  toggleCheckboxSelection(['a', 'b'], 'c', getCheckboxSelectionRule({ selectionRule: 'exact', minSelections: 2, maxSelections: 2, options }).maxSelections),
  { selection: ['a', 'b'], changed: false, limitReached: true },
)

assert.deepEqual(
  validateCheckboxSelection({ options }, [], false),
  { valid: true, message: '', selectedCount: 0 },
)

assert.deepEqual(
  validateCheckboxSelection({ options }, [], true),
  { valid: false, message: '本题至少需要选择 1 项', selectedCount: 0 },
)

assert.deepEqual(
  validateCheckboxSelection({ selectionRule: 'max', maxSelections: 2, options }, ['a', 'b', 'c'], false),
  { valid: false, message: '本题最多可选择 2 项', selectedCount: 3 },
)

assert.deepEqual(
  validateCheckboxSelection({ selectionRule: 'min', minSelections: 2, options }, ['a'], false),
  { valid: false, message: '本题至少需要选择 2 项', selectedCount: 1 },
)

assert.deepEqual(
  validateCheckboxSelection({ selectionRule: 'min', minSelections: 2, options }, ['a', 'b', 'c'], false),
  { valid: true, message: '', selectedCount: 3 },
)

assert.deepEqual(
  validateCheckboxSelection({ selectionRule: 'exact', minSelections: 2, maxSelections: 2, options }, ['a'], false),
  { valid: false, message: '本题必须选择 2 项', selectedCount: 1 },
)

assert.deepEqual(
  validateCheckboxSelection({ selectionRule: 'exact', minSelections: 2, maxSelections: 2, options }, ['a', 'b'], false),
  { valid: true, message: '', selectedCount: 2 },
)

assert.deepEqual(
  validateCheckboxSelection({ selectionRule: 'range', minSelections: 2, maxSelections: 3, options }, ['a'], false),
  { valid: false, message: '本题需要选择 2 至 3 项', selectedCount: 1 },
)

assert.deepEqual(
  validateCheckboxSelection({ selectionRule: 'range', minSelections: 2, maxSelections: 3, options }, ['a', 'b', 'c'], false),
  { valid: true, message: '', selectedCount: 3 },
)

console.log('checkbox selection rule tests passed')
