import { afterEach, describe, expect, it, vi } from 'vitest'
import { requestJson } from './client'

describe('requestJson', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('preserves the abort error when reporting a timeout', async () => {
    const abortError = new DOMException('The request was aborted.', 'AbortError')
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(abortError))

    const request = requestJson('/slow-endpoint')

    await expect(request).rejects.toMatchObject({
      message: 'Request timed out. Please try again.',
      cause: abortError,
    })
  })
})
