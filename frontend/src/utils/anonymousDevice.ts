const ANONYMOUS_DEVICE_ID_KEY = 'talentlens_anonymous_device_id'

const createFallbackId = () => {
  const randomPart = Math.random().toString(36).slice(2, 12)
  const timePart = Date.now().toString(36)
  return `anon-${timePart}-${randomPart}`
}

const createDeviceId = () => {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID()
  }
  return createFallbackId()
}

export const getAnonymousDeviceId = () => {
  try {
    const existing = localStorage.getItem(ANONYMOUS_DEVICE_ID_KEY)
    if (existing) return existing

    const next = createDeviceId()
    localStorage.setItem(ANONYMOUS_DEVICE_ID_KEY, next)
    return next
  } catch {
    return createDeviceId()
  }
}
