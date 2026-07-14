import type { ComputedRef, Ref } from 'vue'
import type { DepartmentRoutingConfig, FormField, PageTexts } from '../api/assessments'

interface UseDistributeConfigStorageOptions {
  storageKey: ComputedRef<string>
  form: Ref<Record<string, any>>
  formFields: Ref<FormField[]>
  pageTexts: Ref<PageTexts>
  routingConfig: Ref<DepartmentRoutingConfig>
}

export const isPlainObject = (value: unknown): value is Record<string, any> => {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}

const repeatCheckByValues = new Set(['phone', 'phone_name', 'name'])

const normalizeRepeatCheckBy = (value: unknown) => {
  const normalized = String(value || '')
  return repeatCheckByValues.has(normalized) ? normalized : 'phone'
}

export function useDistributeConfigStorage(options: UseDistributeConfigStorageOptions) {
  const { storageKey, form, formFields, pageTexts, routingConfig } = options

  const saveConfig = () => {
    try {
      const config = {
        form: {
          validityType: form.value.validityType,
          expiryDays: form.value.expiryDays,
          allowRepeat: form.value.allowRepeat,
          repeatCheckBy: form.value.repeatCheckBy,
          repeatIntervalHours: form.value.repeatIntervalHours,
          maxSubmissions: form.value.maxSubmissions,
          anonymousMode: form.value.anonymousMode,
        },
        formFields: formFields.value,
        pageTexts: pageTexts.value,
        routingConfig: routingConfig.value,
      }
      localStorage.setItem(storageKey.value, JSON.stringify(config))
    } catch (e) {
      console.warn('保存分发配置失败:', e)
    }
  }

  const loadConfig = () => {
    try {
      const saved = localStorage.getItem(storageKey.value)
      if (!saved) return
      const config = JSON.parse(saved)

      if (isPlainObject(config.form)) {
        form.value.validityType = config.form.validityType || 'temporary'
        form.value.expiryDays = config.form.expiryDays || 7
        form.value.allowRepeat = config.form.allowRepeat || false
        form.value.repeatCheckBy = normalizeRepeatCheckBy(config.form.repeatCheckBy)
        form.value.repeatIntervalHours = config.form.repeatIntervalHours || 24
        form.value.maxSubmissions = config.form.maxSubmissions || 0
        form.value.anonymousMode = !!config.form.anonymousMode
      }
      if (Array.isArray(config.formFields)) {
        formFields.value = config.formFields
      }
      if (isPlainObject(config.pageTexts)) {
        pageTexts.value = { ...pageTexts.value, ...config.pageTexts }
      }
      if (isPlainObject(config.routingConfig)) {
        routingConfig.value = {
          enabled: !!config.routingConfig.enabled,
          department_field: config.routingConfig.department_field || 'department',
          fallback_to_default: config.routingConfig.fallback_to_default !== false,
          mappings: Array.isArray(config.routingConfig.mappings) ? config.routingConfig.mappings : [],
        }
      }
    } catch (e) {
      console.warn('加载分发配置失败:', e)
    }
  }

  return { saveConfig, loadConfig }
}
