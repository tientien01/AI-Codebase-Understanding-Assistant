type UploadOptions = {
  url: string
  formData: FormData
  onProgress: (progress: number) => void
}

type ErrorPayload = {
  error?: {
    message?: string
  }
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
      reject(new Error((payload as ErrorPayload | null)?.error?.message ?? `Upload failed with status ${xhr.status}`))
    }
    xhr.onerror = () => reject(new Error('Network error during upload'))
    xhr.send(formData)
  })
}

function parseResponse(responseText: string) {
  if (!responseText) return null
  try {
    return JSON.parse(responseText)
  } catch {
    return null
  }
}
