import { describe, expect, it } from 'vitest'
import { isSafeRelativeSourcePath, pathForPage, resolveAppRoute } from './routes'

describe('canonical application routes', () => {
  it.each([
    ['/projects', 'projects'],
    ['/import', 'import'],
    ['/index-jobs', 'indexing'],
    ['/settings', 'settings'],
    ['/repositories/repo-1/overview', 'overview'],
    ['/repositories/repo-1/evaluation', 'evaluation'],
  ])('resolves %s', (pathname, page) => {
    expect(resolveAppRoute({ pathname, search: '' })).toMatchObject({ status: 'valid', page })
  })

  it('round-trips encoded repository, source, and line context', () => {
    const path = pathForPage('code', 'repo/team', { filePath: 'src/auth flow.ts', line: 42 })

    expect(path).toBe('/repositories/repo%2Fteam/code?path=src%2Fauth+flow.ts&line=42')
    expect(resolveAppRoute({ pathname: '/repositories/repo%2Fteam/code', search: '?path=src%2Fauth+flow.ts&line=42' })).toMatchObject({
      status: 'valid',
      page: 'code',
      repositoryId: 'repo/team',
      filePath: 'src/auth flow.ts',
      line: 42,
    })
  })

  it('builds canonical stateful workspace URLs', () => {
    expect(pathForPage('graph', 'repo-1', { graphView: 'api-flow', graphRoot: 'route:/login', graphDepth: 3 }))
      .toBe('/repositories/repo-1/graph?view=api-flow&root=route%3A%2Flogin&depth=3')
    expect(pathForPage('impact', 'repo-1', { impactTarget: 'symbol:login', compareIndexVersionId: 'idx-2' }))
      .toBe('/repositories/repo-1/impact?target=symbol%3Alogin&compare=idx-2')
    expect(pathForPage('search', 'repo-1', { searchQuery: 'login token', searchTypes: 'symbol,endpoint' }))
      .toBe('/repositories/repo-1/search?q=login+token&types=symbol%2Cendpoint')
    expect(pathForPage('assistant', 'repo-1', { conversationId: 'conversation/7' }))
      .toBe('/repositories/repo-1/assistant/conversation%2F7')
    expect(pathForPage('evidence', 'repo-1', { evidenceId: 'evidence/9' }))
      .toBe('/repositories/repo-1/evidence/evidence%2F9')
  })

  it('classifies symbol, conversation, and evidence detail routes', () => {
    expect(resolveAppRoute({ pathname: '/repositories/r/symbols/pkg%3Alogin', search: '' })).toMatchObject({ detail: 'symbol', symbolKey: 'pkg:login' })
    expect(resolveAppRoute({ pathname: '/repositories/r/assistant/c-1', search: '' })).toMatchObject({ detail: 'conversation', conversationId: 'c-1' })
    expect(resolveAppRoute({ pathname: '/repositories/r/evidence/e-1', search: '' })).toMatchObject({ detail: 'evidence', evidenceId: 'e-1' })
  })

  it.each(['/absolute/file.ts', 'C:/secret/file.ts', '../secret', 'src/../secret', 'src\\secret.ts', 'src//file.ts'])(
    'rejects unsafe source path %s',
    (filePath) => expect(isSafeRelativeSourcePath(filePath)).toBe(false),
  )

  it('fails closed for unknown, malformed, and unsafe routes', () => {
    expect(resolveAppRoute({ pathname: '/unknown', search: '' })).toMatchObject({ status: 'invalid', reason: 'unknown_route' })
    expect(resolveAppRoute({ pathname: '/repositories/%E0%A4%A/overview', search: '' })).toMatchObject({ status: 'invalid', reason: 'malformed_identifier' })
    expect(resolveAppRoute({ pathname: '/repositories/repo/code', search: '?path=C%3A%2Fsecret.txt' })).toMatchObject({ status: 'invalid', reason: 'unsafe_source_path' })
    expect(resolveAppRoute({ pathname: '/repositories/repo/code', search: '?line=-1' })).toMatchObject({ status: 'invalid', reason: 'invalid_parameter' })
    expect(resolveAppRoute({ pathname: '/repositories/repo/graph', search: '?view=unbounded&depth=all' })).toMatchObject({ status: 'invalid', reason: 'invalid_parameter' })
  })
})
