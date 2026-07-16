export type ValueTraceContext =
  | { kind: 'token'; filePath: string; line: number; value: string }
  | { kind: 'scope'; filePath: string; startLine: number; endLine?: number; label?: string }

const VALUE_TRACE_CONTEXT_PREFIX = 'value-context:v1:'

export function encodeValueTraceContext(context: ValueTraceContext): string {
  const payload = context.kind === 'token'
    ? { k: 'token', f: context.filePath, l: context.line, v: context.value }
    : { k: 'scope', f: context.filePath, s: context.startLine, e: context.endLine ?? context.startLine, n: context.label }
  return `${VALUE_TRACE_CONTEXT_PREFIX}${encodeURIComponent(JSON.stringify(payload))}`
}

export function isValueTraceContext(value?: string): boolean {
  return Boolean(value?.startsWith(VALUE_TRACE_CONTEXT_PREFIX))
}

export function decodeValueTraceContext(value?: string): ValueTraceContext | undefined {
  if (!isValueTraceContext(value)) return undefined
  try {
    const payload = JSON.parse(decodeURIComponent(value!.slice(VALUE_TRACE_CONTEXT_PREFIX.length))) as Record<string, unknown>
    if (payload.k === 'token' && typeof payload.f === 'string' && typeof payload.l === 'number' && typeof payload.v === 'string') {
      return { kind: 'token', filePath: payload.f, line: payload.l, value: payload.v }
    }
    if (payload.k === 'scope' && typeof payload.f === 'string' && typeof payload.s === 'number') {
      return {
        kind: 'scope',
        filePath: payload.f,
        startLine: payload.s,
        endLine: typeof payload.e === 'number' ? payload.e : undefined,
        label: typeof payload.n === 'string' ? payload.n : undefined,
      }
    }
  } catch {
    return undefined
  }
  return undefined
}

export function valueTraceContextLabel(value?: string): string {
  if (!isValueTraceContext(value)) return 'Selected indexed value'
  try {
    const payload = JSON.parse(decodeURIComponent(value!.slice(VALUE_TRACE_CONTEXT_PREFIX.length))) as Record<string, unknown>
    if (payload.k === 'token') return `${String(payload.v)} · ${String(payload.f)}:${String(payload.l)}`
    return `${String(payload.n || 'Selected scope')} · ${String(payload.f)}:${String(payload.s)}-${String(payload.e)}`
  } catch {
    return 'Selected source context'
  }
}
