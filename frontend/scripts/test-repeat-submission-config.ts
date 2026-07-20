import assert from 'node:assert/strict'

import { useDistributeConfigStorage } from '../src/components/distributeConfigStorage'

const savedConfigs = new Map<string, string>()
Object.defineProperty(globalThis, 'localStorage', {
  value: {
    getItem: (key: string) => savedConfigs.get(key) ?? null,
    setItem: (key: string, value: string) => savedConfigs.set(key, value),
  },
})

const loadRepeatConfig = (allowRepeat: boolean, repeatCheckBy: string) => {
  const storageKey = { value: 'repeat-config-test' }
  const form = { value: {} as Record<string, unknown> }
  const formFields = { value: [] }
  const pageTexts = { value: {} }
  const routingConfig = { value: {} }

  savedConfigs.set(storageKey.value, JSON.stringify({
    form: { allowRepeat, repeatCheckBy },
  }))

  useDistributeConfigStorage({
    storageKey,
    form,
    formFields,
    pageTexts,
    routingConfig,
  }).loadConfig()

  return form.value.repeatCheckBy
}

assert.equal(loadRepeatConfig(false, 'name'), 'phone')
assert.equal(loadRepeatConfig(true, 'name'), 'name')
assert.equal(loadRepeatConfig(true, 'unknown'), 'phone')

console.log('repeat submission config tests passed')
