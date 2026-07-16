import type { Page, Route } from '@playwright/test'

const repositoryId = 'repo-ui004'
const ui005RepositoryId = 'repo-ui005'

export async function installUi004Api(page: Page, graphSize = 12) {
  await page.route('**/api/v1/**', async (route) => {
    const request = route.request()
    const url = new URL(request.url())
    const path = url.pathname

    if (path === '/api/v1/repositories') return json(route, [repository])
    if (path.endsWith(`/${repositoryId}/index/status`)) return json(route, indexStatus)
    if (path.endsWith(`/${repositoryId}/overview`)) return json(route, overview)
    if (path.endsWith(`/${repositoryId}/graph/dependencies`)) {
      const mode = url.searchParams.get('projection_mode')
      const root = url.searchParams.get('root_keys')
      return json(route, mode === 'neighbors' && root ? dependencyExpansionFixture(root) : dependencySeedFixture())
    }
    if (path.includes(`/${repositoryId}/graph/`) && !path.endsWith('/expand')) return json(route, graphFixture(graphSize))
    if (path.endsWith(`/${repositoryId}/files/tree`)) return json(route, fileTree)
    if (path.endsWith(`/${repositoryId}/files/content`)) return json(route, fileContent)
    if (path.endsWith(`/${repositoryId}/impact`) && request.method() === 'POST') return json(route, impactResult)
    if (path.endsWith(`/${repositoryId}/graph/expand`) && request.method() === 'POST') return json(route, { accepted: true })

    return json(route, { error: { code: 'fixture_route_missing', message: `No UI-004 fixture for ${request.method()} ${path}` } }, 404)
  })
}

export async function installUi005Api(
  page: Page,
  options: { settingsMode?: 'success' | 'permission' | 'retryable' } = {},
) {
  let settingsRecovered = false
  await page.route('**/api/v1/**', async (route) => {
    const url = new URL(route.request().url())
    const path = url.pathname

    if (path === '/api/v1/repositories') return json(route, [ui005Repository])
    if (path.endsWith(`/${ui005RepositoryId}/index/status`)) return json(route, ui005IndexStatus)
    if (path === '/api/v1/settings/ignore-patterns') return json(route, ui005IgnorePatterns)
    if (path === '/api/v1/settings') {
      if (options.settingsMode === 'permission') {
        return json(route, { error: { code: 'permission_denied', message: 'Settings access is not allowed.' } }, 403)
      }
      if (options.settingsMode === 'retryable' && !settingsRecovered) {
        return json(route, { error: { code: 'settings_unavailable', message: 'Settings are temporarily unavailable.' } }, 503)
      }
      return json(route, ui005Settings)
    }

    return json(route, { error: { code: 'fixture_route_missing', message: `No UI-005 fixture for ${route.request().method()} ${path}` } }, 404)
  })
  return { recoverSettings: () => { settingsRecovered = true } }
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

function dependencySeedFixture() {
  const nodes = [0, 1, 2].map((index) => ({
    id: `seed-${index}`,
    type: 'file',
    label: `Seed ${index}`,
    file_path: `src/seed-${index}.ts`,
    coverage: 'deep_indexed',
  }))
  return {
    repository_id: repositoryId,
    index_version: 22,
    view: 'dependencies',
    nodes,
    edges: [],
    counts: { available_nodes: 7, included_nodes: 3, available_edges: 0, included_edges: 0, available_counts_are_estimates: false },
    coverage: { state: 'ready', measured: { graph_nodes: 3 }, unknown: [] },
    truncation: { truncated: false, reason: null, continuation_token: null },
    unsupported_hops: [],
    can_expand: true,
    provenance: { source: 'ui011_dependency_fixture', deterministic_order: true, support_levels: ['deep'] },
    dependency_scope_used: 'internal',
    seed_strategy: 'dependency-starting-points/v1',
    seeds: nodes.map((node, index) => ({
      node_id: node.id,
      reason_codes: index === 0 ? ['application_entrypoint', 'many_dependents'] : ['graph_region_representative'],
      incoming_available: index,
      outgoing_available: index === 0 ? 1 : 0,
    })),
    additional_starting_points: 4,
  }
}

function dependencyExpansionFixture(root: string) {
  const child = `${root}-dependency`
  return {
    repository_id: repositoryId,
    index_version: 22,
    view: 'dependencies',
    nodes: [
      { id: root, type: 'file', label: root.replace('seed-', 'Seed '), file_path: `src/${root}.ts`, coverage: 'deep_indexed' },
      { id: child, type: 'file', label: 'Resolved dependency', file_path: `src/${child}.ts`, coverage: 'deep_indexed' },
    ],
    edges: [{ source: root, target: child, type: 'imports_internal', confidence: 1, evidence_level: 'deep' }],
    counts: { available_nodes: 2, included_nodes: 2, available_edges: 1, included_edges: 1, available_counts_are_estimates: false },
    coverage: { state: 'ready', measured: { graph_nodes: 2 }, unknown: [] },
    truncation: { truncated: false, reason: null, continuation_token: null },
    unsupported_hops: [],
    can_expand: false,
    provenance: { source: 'ui011_dependency_fixture', deterministic_order: true, support_levels: ['deep'] },
    dependency_scope_used: 'internal',
    expansion: {
      root_key: root,
      incoming_available: 0,
      outgoing_available: 1,
      included_neighbors: 1,
      remaining_neighbors: 0,
      next_neighbor_offset: null,
      leaf: false,
      limited: false,
    },
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

const ui005Repository = {
  id: ui005RepositoryId,
  name: 'UI-005 Truthful Workspace',
  source_type: 'upload_folder',
  status: 'indexed',
  current_index_version: 31,
  detected_stack: ['React', 'FastAPI'],
  total_files: 48,
  indexed_files: 42,
  symbols: 110,
  endpoints: 6,
  chunks: 240,
  graph_nodes: 80,
}

const ui005IndexStatus = {
  repository_id: ui005RepositoryId,
  index_version: 31,
  status: 'completed_with_warnings',
  current_step: 'completed',
  total_files: 48,
  processed_files: 42,
  skipped_files: 6,
  failed_files: 0,
  progress: 100,
  stats: {},
  logs: [],
  warnings: ['Six unsupported files were skipped.'],
}

const ui005Settings = {
  indexing: { default_profile: 'balanced', max_file_size_mb: 1, max_upload_size_mb: 50 },
  providers: {
    llm_provider: 'openai-compatible',
    llm_model: 'operator-selected',
    llm_configured: true,
    embedding_provider: 'local',
    embedding_model: 'deterministic-fixture',
    embedding_configured: false,
    vector_store_provider: 'none',
  },
  security: { secret_scanning_enabled: true },
}

const ui005IgnorePatterns = {
  default_patterns: ['node_modules', '.venv', 'dist', 'build'],
  user_patterns: [],
  effective_patterns: ['node_modules', '.venv', 'dist', 'build', '.env', '.env.*', '*.pem', '*.key'],
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
