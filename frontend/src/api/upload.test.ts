import { afterEach, describe, expect, it, vi } from 'vitest'
import { uploadFormData } from './upload'

describe('uploadFormData', () => {
  afterEach(() => vi.unstubAllGlobals())

  it('surfaces FastAPI multipart detail instead of a generic 400 message', async () => {
    class FailedUploadRequest {
      status = 400
      responseText = JSON.stringify({ detail: 'Too many files. Maximum number of files is 1000.' })
      upload: { onprogress: ((event: ProgressEvent) => void) | null } = { onprogress: null }
      onload: (() => void) | null = null
      onerror: (() => void) | null = null

      open() {}
      send() { this.onload?.() }
    }
    vi.stubGlobal('XMLHttpRequest', FailedUploadRequest)

    await expect(uploadFormData({
      url: '/upload',
      formData: new FormData(),
      onProgress: vi.fn(),
    })).rejects.toMatchObject({
      message: 'Too many files. Maximum number of files is 1000.',
      status: 400,
    })
  })
})
