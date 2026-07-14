import type { Page, Route } from '@playwright/test'

const repositoryId = 'repo-ui004'

export async function installUi004Api(page: Page, graphSize = 12) {
  await page.route('**/api/v1/**', async (route) => {
    const request = route.request()
    const url = new URL(request.url())
    const path = url.pathname

    if (path === '/api/v1/repositories') return json(route, [repository])
    if (path.endsWith(`/${repositoryId}/index/status`)) return json(route, indexStatus)
    if (path.endsWith(`/${repositoryId}/overview`)) return json(route, overview)
    if (path.includes(`/${repositoryId}/graph/`) && !path.endsWith('/expand')) return json(route, graphFixture(graphSize))
    if (path.endsWith(`/${repositoryId}/files/tree`)) return json(route, fileTree)
    if (path.endsWith(`/${repositoryId}/files/content`)) return json(route, fileContent)
    if (path.endsWith(`/${repositoryId}/impact`) && request.method() === 'POST') return json(route, impactResult)
    if (path.endsWith(`/${repositoryId}/graph/expand`) && request.method() === 'POST') return json(route, { accepted: true })

    return json(route, { error: { code: 'fixture_route_missing', message: `No UI-004 fixture for ${request.method()} ${path}` } }, 404)
  })
}

export function graphFixture(nodeCount: number) {
  const types = ['endpoint', 'router', 'service', 'repository', 'database', 'model']
  const nodes = Array.from({ length: nodeCount }, (_, index) => {
    const type = types[index % types.length]
    return {
      id: `node-${index}`,
      type,
      label: `${title(type)} ${index}`,
      file_path: `src/${type}-${index}.ts`,
      start_line: 1,
      end_line: 20,
      summary: `Deterministic ${type} fixture ${index}.`,
      coverage: 'deep_indexed',
      role: type,
    }
  })
  const edges = Array.from({ length: Math.max(0, nodeCount - 1) }, (_, index) => ({
    source: `node-${index}`,
    target: `node-${index + 1}`,
    type: index % 2 ? 'depends_on' : 'calls',
    confidence: index % 5 ? 1 : 0.7,
    evidence_level: index % 5 ? 'deep' : 'inferred',
  }))
  return {
    repository_id: repositoryId,
    index_version: 22,
    view: 'project-map',
    nodes,
    edges,
    counts: {
      available_nodes: nodeCount,
      included_nodes: nodeCount,
      available_edges: edges.length,
      included_edges: edges.length,
      available_counts_are_estimates: false,
    },
    coverage: { state: 'ready', measured: { graph_nodes: nodeCount }, unknown: [] },
    truncation: { truncated: false, reason: null, continuation_token: null },
    unsupported_hops: [],
    can_expand: false,
    provenance: { source: 'ui004_deterministic_fixture', deterministic_order: true, support_levels: ['deep', 'inferred'] },
  }
}

const repository = {
  id: repositoryId,
  name: 'UI-004 Reference Repository',
  source_type: 'upload_folder',
  status: 'indexed',
  current_index_version: 22,
  detected_stack: ['React', 'FastAPI', 'PostgreSQL'],
  total_files: 48,
  indexed_files: 48,
  symbols: 190,
  endpoints: 8,
  chunks: 420,
  graph_nodes: 220,
}

const indexStatus = {
  repository_id: repositoryId,
  index_version: 22,
  status: 'completed',
  current_step: 'completed',
  total_files: 48,
  processed_files: 48,
  skipped_files: 0,
  failed_files: 0,
  progress: 100,
  stats: {},
  logs: [],
  warnings: [],
}

const overview = {
  repository_id: repositoryId,
  name: repository.name,
  detected_stack: repository.detected_stack,
  important_files: [
    { file_path: 'src/main.ts', reason: 'Registers the application entrypoint and public boundaries.' },
    { file_path: 'src/auth-service.ts', reason: 'Owns authentication behavior used by the API layer.' },
  ],
  modules: [
    { name: 'Authentication', summary: 'Login, session and authorization behavior.', file_count: 8 },
    { name: 'Persistence', summary: 'Repository and database adapters.', file_count: 10 },
  ],
  endpoints: [{ method: 'POST', path: '/login', handler: 'login', file_path: 'src/routes.ts', start_line: 12, end_line: 30 }],
  documentation_gaps: ['Authentication decisions'],
  stats: { files: 48, functions: 120, classes: 35, endpoints: 8, graph_nodes: 220, chunks: 420 },
}

const fileTree = [{ name: 'src', path: 'src', type: 'directory', children: [{ name: 'main.ts', path: 'src/main.ts', type: 'file', children: [] }] }]

const fileContent = {
  file_path: 'src/main.ts',
  language: 'typescript',
  content: 'export function bootstrap() {\n  return createApplication()\n}',
  lines: ['export function bootstrap() {', '  return createApplication()', '}'],
  symbols: [],
}

const directImpact = { node_id: 'node-1', node_type: 'endpoint', label: 'POST /login', file_path: 'src/routes.ts', depth: 1, confidence: 1, via_edge: 'calls', reason: 'Resolved static call.' }
const inferredImpact = { node_id: 'node-7', node_type: 'service', label: 'Audit Service', file_path: 'src/audit.ts', depth: 2, confidence: 0.7, via_edge: 'may_call', reason: 'Heuristic relation requiring verification.' }

const impactResult = {
  repository_id: repositoryId,
  target: { node_id: 'node-2', node_type: 'service', label: 'Service 2', file_path: 'src/service-2.ts', line_range: '1-20' },
  risk_level: 'medium',
  risk_score: 0.5,
  direct: [directImpact],
  indirect: [inferredImpact],
  affected_files: [directImpact, inferredImpact],
  affected_endpoints: [directImpact],
  affected_tests: [{ ...directImpact, node_id: 'test-login', node_type: 'test', label: 'login flow test', file_path: 'tests/login.spec.ts' }],
  affected_symbols: [inferredImpact],
  suggested_checks: ['Run authentication tests.', 'Verify audit delivery.'],
  missing_relations: ['Dynamic provider dispatch is not resolved.'],
}

function json(route: Route, body: unknown, status = 200) {
  return route.fulfill({ status, contentType: 'application/json', body: JSON.stringify(body) })
}

function title(value: string) {
  return `${value.charAt(0).toUpperCase()}${value.slice(1)}`
}
