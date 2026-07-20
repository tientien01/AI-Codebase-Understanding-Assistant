export const API_BASE = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'
export const API_V1 = `${API_BASE}/api/v1`

type ErrorPayload = {
  error?: {
    code?: string
    message?: string
  }
}

const DEFAULT_TIMEOUT_MS = 30_000

export class ApiError extends Error {
  readonly status: number
  readonly code?: string
  readonly retryable: boolean

  constructor(message: string, options: { status: number; code?: string; retryable: boolean; cause?: unknown }) {
    super(message, { cause: options.cause })
    this.name = 'ApiError'
    this.status = options.status
    this.code = options.code
    this.retryable = options.retryable
  }
}

export async function requestJson<T>(
  url: string,
  options?: RequestInit,
  timeoutMs = DEFAULT_TIMEOUT_MS,
): Promise<T> {
  const controller = options?.signal ? null : new AbortController()
  const timeout = controller
    ? window.setTimeout(() => controller.abort(), timeoutMs)
    : null
  try {
    const response = await fetch(url, { ...options, signal: options?.signal ?? controller?.signal })
    if (!response.ok) {
      const payload = (await response.json().catch(() => null)) as ErrorPayload | null
      throw new ApiError(safeMessage(payload?.error?.message, response.status), {
        status: response.status,
        code: payload?.error?.code,
        retryable: isRetryableStatus(response.status),
      })
    }
    return response.json() as Promise<T>
  } catch (error) {
    if (error instanceof DOMException && error.name === 'AbortError') {
      if (options?.signal?.aborted) throw error
      throw new ApiError('Request timed out. Please try again.', {
        status: 408,
        code: 'request_timeout',
        retryable: true,
        cause: error,
      })
    }
    throw error
  } finally {
    if (timeout) window.clearTimeout(timeout)
  }
}

export function isRequestCancelled(error: unknown): boolean {
  return error instanceof DOMException && error.name === 'AbortError'
}

export function safeErrorMessage(error: unknown): string {
  if (isRequestCancelled(error)) return 'Request cancelled.'
  if (error instanceof ApiError || error instanceof Error) return sanitizeMessage(error.message)
  return 'Request failed. Please try again.'
}

function isRetryableStatus(status: number) {
  return status === 408 || status === 429 || status >= 500
}

function safeMessage(message: string | undefined, status: number) {
  return message ? sanitizeMessage(message) : `Request failed with status ${status}`
}

function sanitizeMessage(message: string) {
  const safe = [...message]
    .filter((character) => {
      const code = character.charCodeAt(0)
      return code >= 32 && code !== 127
    })
    .join('')
    .trim()
  return (safe || 'Request failed. Please try again.').slice(0, 300)
}
