export const API_BASE = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'
export const API_V1 = `${API_BASE}/api/v1`

type ErrorPayload = {
  error?: {
    message?: string
  }
}

const DEFAULT_TIMEOUT_MS = 30_000

export async function requestJson<T>(url: string, options?: RequestInit): Promise<T> {
  const controller = options?.signal ? null : new AbortController()
  const timeout = controller
    ? window.setTimeout(() => controller.abort(), DEFAULT_TIMEOUT_MS)
    : null
  try {
    const response = await fetch(url, { ...options, signal: options?.signal ?? controller?.signal })
    if (!response.ok) {
      const payload = (await response.json().catch(() => null)) as ErrorPayload | null
      throw new Error(payload?.error?.message ?? `Request failed with status ${response.status}`)
    }
    return response.json() as Promise<T>
  } catch (error) {
    if (error instanceof DOMException && error.name === 'AbortError') {
      throw new Error('Request timed out. Please try again.', { cause: error })
    }
    throw error
  } finally {
    if (timeout) window.clearTimeout(timeout)
  }
}
