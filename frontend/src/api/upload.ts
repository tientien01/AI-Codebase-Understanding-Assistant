import { ApiError } from './client'

type UploadOptions = {
  url: string
  formData: FormData
  onProgress: (progress: number) => void
}

type ErrorPayload = {
  error?: {
    code?: string
    message?: string
  }
  detail?: string | { msg?: string }[]
}

export function uploadFormData<T>({ url, formData, onProgress }: UploadOptions): Promise<T> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest()
    xhr.open('POST', url)
    xhr.upload.onprogress = (event) => {
      if (!event.lengthComputable) return
      onProgress(Math.round((event.loaded / event.total) * 100))
    }
    xhr.onload = () => {
      const payload = parseResponse(xhr.responseText)
      if (xhr.status >= 200 && xhr.status < 300) {
        resolve(payload as T)
        return
      }
      const errorPayload = payload as ErrorPayload | null
      reject(new ApiError(uploadErrorMessage(errorPayload, xhr.status), {
        status: xhr.status,
        code: errorPayload?.error?.code,
        retryable: xhr.status === 408 || xhr.status === 429 || xhr.status >= 500,
      }))
    }
    xhr.onerror = () => reject(new Error('Network error during upload'))
    xhr.send(formData)
  })
}

function uploadErrorMessage(payload: ErrorPayload | null, status: number) {
  if (payload?.error?.message) return payload.error.message
  if (typeof payload?.detail === 'string') return payload.detail
  const validationMessage = payload?.detail?.find((item) => item.msg)?.msg
  return validationMessage ?? `Upload failed with status ${status}`
}

function parseResponse(responseText: string) {
  if (!responseText) return null
  try {
    return JSON.parse(responseText)
  } catch {
    return null
  }
}
