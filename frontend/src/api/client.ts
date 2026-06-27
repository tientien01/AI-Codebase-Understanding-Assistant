export const API_BASE = 'http://localhost:8000'
export const API_V1 = `${API_BASE}/api/v1`

type ErrorPayload = {
  error?: {
    message?: string
  }
}

export async function requestJson<T>(url: string, options?: RequestInit): Promise<T> {
  const response = await fetch(url, options)
  if (!response.ok) {
    const payload = (await response.json().catch(() => null)) as ErrorPayload | null
    throw new Error(payload?.error?.message ?? `Request failed with status ${response.status}`)
  }
  return response.json() as Promise<T>
}
