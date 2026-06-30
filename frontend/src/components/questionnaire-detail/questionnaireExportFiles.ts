export const delay = (ms: number) => new Promise(resolve => setTimeout(resolve, ms))

export const pad2 = (value: number | string) => String(value).padStart(2, '0')

export const sanitizeFileName = (name: string) => {
  return name.replace(/[\/:*?"<>|]/g, '_').replace(/\s+/g, '_').slice(0, 80)
}

export const downloadHref = (href: string, fileName: string) => {
  const link = document.createElement('a')
  link.href = href
  link.download = fileName
  document.body.appendChild(link)
  link.click()
  link.remove()
}

export const downloadBlob = (blob: Blob, fileName: string) => {
  const url = URL.createObjectURL(blob)
  downloadHref(url, fileName)
  setTimeout(() => URL.revokeObjectURL(url), 1000)
}
