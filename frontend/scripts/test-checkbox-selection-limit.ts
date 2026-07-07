import assert from 'node:assert/strict'

import {
  getCheckboxMaxSelections,
  toggleCheckboxSelection,
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

console.log('checkbox selection limit tests passed')
