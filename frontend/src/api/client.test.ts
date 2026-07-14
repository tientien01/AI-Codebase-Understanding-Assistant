import { afterEach, describe, expect, it, vi } from 'vitest'
import { ApiError, requestJson, safeErrorMessage } from './client'

describe('requestJson', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('preserves the abort error when reporting a timeout', async () => {
    const abortError = new DOMException('The request was aborted.', 'AbortError')
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(abortError))

    const request = requestJson('/slow-endpoint')

    await expect(request).rejects.toMatchObject({
      name: 'ApiError',
      message: 'Request timed out. Please try again.',
      cause: abortError,
      retryable: true,
    })
  })

  it('preserves caller cancellation without reporting a timeout', async () => {
    const controller = new AbortController()
    const abortError = new DOMException('cancelled', 'AbortError')
    controller.abort()
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(abortError))

    await expect(requestJson('/cancelled', { signal: controller.signal })).rejects.toBe(abortError)
  })

  it('classifies permission and retryable server errors', async () => {
    vi.stubGlobal('fetch', vi.fn()
      .mockResolvedValueOnce(errorResponse(403, 'permission_denied', ' Not allowed\n'))
      .mockResolvedValueOnce(errorResponse(503, 'service_unavailable', 'Try later')))

    await expect(requestJson('/forbidden')).rejects.toMatchObject({ status: 403, code: 'permission_denied', retryable: false })
    await expect(requestJson('/unavailable')).rejects.toMatchObject({ status: 503, code: 'service_unavailable', retryable: true })
  })

  it('bounds and sanitizes visible error messages', () => {
    const error = new ApiError(`Unsafe\u0000${'x'.repeat(400)}`, { status: 500, retryable: true })
    const message = safeErrorMessage(error)

    expect(message).not.toContain('\u0000')
    expect(message).toHaveLength(300)
  })
})

function errorResponse(status: number, code: string, message: string) {
  return {
    ok: false,
    status,
    json: async () => ({ error: { code, message } }),
  } as Response
}
