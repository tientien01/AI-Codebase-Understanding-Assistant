import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import type { GraphData, GraphProjectionInput, GraphView } from '../../types/api'
import { encodeValueTraceContext } from '../../utils/valueTrace'
import type { ValueTraceContext } from '../../utils/valueTrace'
import { GraphPage, ValueTracePanel } from './GraphPage'

const projection: GraphProjectionInput = {
  indexVersion: 7,
  projectionMode: 'seeds',
  dependencyScope: 'adaptive',
  seedLimit: 12,
  neighborOffset: 0,
  rootKeys: [],
  nodeTypes: [],
  edgeTypes: [],
  direction: 'both',
  maxDepth: 2,
  maxNodes: 40,
  maxEdges: 80,
  minConfidence: 0,
  supportLevels: [],
}

afterEach(cleanup)

describe('GraphPage progressive dependency UX', () => {
  it('starts with relationship questions instead of duplicating the architecture overview', () => {
    const onGraphView = vi.fn()
    const onProjection = vi.fn()

    renderGraph(seedGraph(4), { graphView: 'project-map', onGraphView, onProjection })

    expect(screen.getByRole('heading', { name: 'What do you want to understand?' })).toBeTruthy()
    expect(screen.getByRole('button', { name: /Dependencies/ })).toBeTruthy()
    expect(screen.queryByRole('button', { name: /Value Flow|Value Trace/ })).toBeNull()
    expect(screen.queryByLabelText('Graph nodes')).toBeNull()

    fireEvent.click(screen.getByRole('button', { name: /Request Flow/ }))
    expect(onGraphView).toHaveBeenCalledWith('api-flow')
  })

  it('enters adaptive dependencies without carrying the detected-import edge filter', () => {
    const onGraphView = vi.fn()
    const onProjection = vi.fn()
    renderGraph(seedGraph(4), { graphView: 'project-map', onGraphView, onProjection })

    fireEvent.click(screen.getByRole('button', { name: /Dependencies/ }))

    expect(onProjection).toHaveBeenCalledWith({
      rootKeys: [],
      nodeTypes: [],
      edgeTypes: [],
      supportLevels: [],
      direction: 'both',
      projectionMode: 'seeds',
      dependencyScope: 'adaptive',
      neighborOffset: 0,
    })
    expect(onGraphView).toHaveBeenCalledWith('dependencies')
  })

  it('renders the server-selected starting points without padding to a fixed count', () => {
    renderGraph(seedGraph(3))

    expect(within(screen.getByLabelText('Graph nodes')).getAllByRole('button')).toHaveLength(3)
    expect(screen.getByText('3 suggested starting points')).toBeTruthy()
    expect(screen.getByText(/Application entrypoint/)).toBeTruthy()
    expect(screen.getByText(/qualified points are outside this bounded overview/)).toBeTruthy()
    expect(screen.queryByText('Projection size')).toBeNull()
    expect(screen.queryByText('Depth')).toBeNull()
    expect(screen.getByText('Relations (0)').closest('details')?.hasAttribute('open')).toBe(false)
  })

  it('expands one bounded branch and dims unrelated starting points', async () => {
    const onExpandNode = vi.fn().mockResolvedValue(expansionGraph('seed-0', ['child-0']))
    const { container } = renderGraph(seedGraph(3), { onExpandNode })
    const seed = within(screen.getByLabelText('Graph nodes')).getByRole('button', { name: /Seed 0/ })
    const initialLeft = seed.getAttribute('style')

    fireEvent.click(seed)

    expect(onExpandNode).toHaveBeenCalledWith('seed-0', 'both', 0)
    await waitFor(() => expect(within(screen.getByLabelText('Graph nodes')).getAllByRole('button')).toHaveLength(4))
    expect(container.querySelectorAll('.dependency-node.dimmed')).toHaveLength(2)
    expect(seed.getAttribute('style')).toBe(initialLeft)
    expect(screen.getByText('Relations (1)')).toBeTruthy()
  })

  it('continues a busy node from the server-provided neighbor offset', async () => {
    const first = expansionGraph('seed-0', ['child-0'], { remaining: 2, nextOffset: 1 })
    const second = expansionGraph('seed-0', ['child-1', 'child-2'], { remaining: 0, nextOffset: null })
    const onExpandNode = vi.fn().mockResolvedValueOnce(first).mockResolvedValueOnce(second)
    renderGraph(seedGraph(1), { onExpandNode })

    const seed = within(screen.getByLabelText('Graph nodes')).getByRole('button', { name: /Seed 0/ })
    fireEvent.click(seed)
    await waitFor(() => expect(onExpandNode).toHaveBeenCalledWith('seed-0', 'both', 0))
    await waitFor(() => expect(screen.getAllByText('2 more to load')).toHaveLength(2))

    fireEvent.click(seed)
    await waitFor(() => expect(onExpandNode).toHaveBeenLastCalledWith('seed-0', 'both', 1))
    await waitFor(() => expect(within(screen.getByLabelText('Graph nodes')).getAllByRole('button')).toHaveLength(4))
    expect(screen.getAllByText('Fully expanded')).toHaveLength(2)
  })

  it('changes relation scope explicitly and keeps canonical filters out of the main canvas', () => {
    const onProjection = vi.fn()
    renderGraph(seedGraph(2), { onProjection })

    fireEvent.click(screen.getByRole('button', { name: 'Resolved internal' }))

    expect(onProjection).toHaveBeenCalledWith({
      dependencyScope: 'internal',
      projectionMode: 'seeds',
      rootKeys: [],
      nodeTypes: ['file'],
      edgeTypes: ['imports_internal'],
      supportLevels: [],
    })
    expect(screen.queryByLabelText('Root key')).toBeNull()
  })

  it('returns to starting points when relationship direction changes', async () => {
    const onExpandNode = vi.fn().mockResolvedValue(expansionGraph('seed-0', ['child-0']))
    renderGraph(seedGraph(2), { onExpandNode })

    fireEvent.click(within(screen.getByLabelText('Graph nodes')).getByRole('button', { name: /Seed 0/ }))
    await waitFor(() => expect(screen.getByText('Relations (1)')).toBeTruthy())

    fireEvent.click(within(screen.getByLabelText('Relationship direction')).getByRole('button', { name: 'Dependencies' }))

    expect(screen.getByText('Relations (0)')).toBeTruthy()
    expect(screen.queryByLabelText('Selected graph entity')).toBeNull()
    expect(within(screen.getByLabelText('Graph nodes')).getAllByRole('button')).toHaveLength(2)
  })

  it('disables expansion for a confirmed leaf and hides the irrelevant branch action', async () => {
    const onExpandNode = vi.fn().mockResolvedValue(expansionGraph('seed-0', []))
    renderGraph(seedGraph(1), { onExpandNode })

    fireEvent.click(within(screen.getByLabelText('Graph nodes')).getByRole('button', { name: /Seed 0/ }))

    await waitFor(() => expect(screen.getByRole('button', { name: 'No more relations' }).hasAttribute('disabled')).toBe(true))
    expect(screen.queryByRole('button', { name: 'Hide branch' })).toBeNull()
  })

  it('automatically replaces the previous expanded branch when focus changes', async () => {
    const onExpandNode = vi.fn()
      .mockResolvedValueOnce(expansionGraph('seed-0', ['child-0']))
      .mockResolvedValueOnce(expansionGraph('seed-1', ['child-1']))
    renderGraph(seedGraph(2), { onExpandNode })

    fireEvent.click(within(screen.getByLabelText('Graph nodes')).getByRole('button', { name: /Seed 0/ }))
    await waitFor(() => expect(within(screen.getByLabelText('Graph nodes')).getByRole('button', { name: /child-0/ })).toBeTruthy())
    fireEvent.click(within(screen.getByLabelText('Graph nodes')).getByRole('button', { name: /Seed 1/ }))

    await waitFor(() => expect(onExpandNode).toHaveBeenCalledTimes(2))
    await waitFor(() => expect(within(screen.getByLabelText('Graph nodes')).getByRole('button', { name: /child-1/ })).toBeTruthy())
    expect(within(screen.getByLabelText('Graph nodes')).queryByRole('button', { name: /child-0/ })).toBeNull()
    expect(screen.queryByRole('button', { name: 'Hide branch' })).toBeNull()
  })

  it('shows honest limited coverage and an accessible relation alternative', () => {
    const graph = seedGraph(2, {
      coverage: { state: 'limited', measured: {}, unknown: ['internal_dependency_resolution_unavailable'] },
      truncation: { truncated: true, reason: 'seed_budget' },
    })
    renderGraph(graph)

    expect(screen.getByText(/absence of an edge is not proof/)).toBeTruthy()
    expect(screen.getByText('Relations (0)')).toBeTruthy()
    expect(screen.getByText(/Keyboard and screen-reader alternative/)).toBeTruthy()
  })
})

describe('GraphPage progressive request-flow UX', () => {
  it('starts from request entry points without rendering call-site noise', () => {
    renderGraph(requestSeedGraph(), { graphView: 'api-flow', projection: requestProjection })

    expect(screen.getByRole('heading', { name: 'Request Flow' })).toBeTruthy()
    expect(screen.getByText('2 of 2 entry points loaded')).toBeTruthy()
    expect(screen.getByRole('button', { name: 'All (2)' })).toBeTruthy()
    expect(screen.getByRole('button', { name: 'Server (1)' })).toBeTruthy()
    expect(screen.getByRole('button', { name: 'Client (1)' })).toBeTruthy()
    expect(screen.getByRole('button', { name: /GET \/notes/ })).toBeTruthy()
    expect(screen.getByRole('button', { name: /loadNotes/ })).toBeTruthy()
    expect(screen.queryByText('fetch_notes()')).toBeNull()
    expect(screen.getByText('Relations (0)')).toBeTruthy()
  })

  it('launches a contextual value trace from a selected request endpoint', async () => {
    const onTraceValue = vi.fn()
    const onExpandNode = vi.fn().mockResolvedValue(requestExpansionGraph('endpoint', [], []))
    renderGraph(requestSeedGraph(), { graphView: 'api-flow', projection: requestProjection, onExpandNode, onTraceValue })

    fireEvent.click(screen.getByRole('button', { name: /GET \/notes/ }))
    await waitFor(() => expect(screen.getByLabelText('Selected request flow entity')).toBeTruthy())
    fireEvent.click(screen.getByRole('button', { name: /Trace values in this scope/ }))

    expect(onTraceValue).toHaveBeenCalledWith({ kind: 'scope', filePath: 'api/routes.py', startLine: 20, endLine: 26, label: 'GET /notes' })
  })

  it('opens one supported hop, inspects without expanding, then continues explicitly', async () => {
    const onExpandNode = vi.fn()
      .mockResolvedValueOnce(requestExpansionGraph('endpoint', [
        { id: 'client-call', type: 'api_call', label: 'loadNotes', file_path: 'web/api.ts' },
        { id: 'handler', type: 'function', label: 'list_notes', file_path: 'api/routes.py' },
      ], [
        { source: 'client-call', target: 'endpoint', type: 'calls_api', confidence: 0.95, evidence_level: 'deep' },
        { source: 'endpoint', target: 'handler', type: 'exposes_endpoint', confidence: 1, evidence_level: 'deep' },
      ]))
      .mockResolvedValueOnce(requestExpansionGraph('handler', [
        { id: 'service', type: 'function', label: 'fetch_notes', file_path: 'services/notes.py' },
      ], [
        { source: 'handler', target: 'service', type: 'calls', confidence: 0.9, evidence_level: 'deep' },
      ]))
    renderGraph(requestSeedGraph(), { graphView: 'api-flow', projection: requestProjection, onExpandNode })

    fireEvent.click(screen.getByRole('button', { name: /GET \/notes/ }))
    await waitFor(() => expect(onExpandNode).toHaveBeenCalledWith('endpoint', 'both', 0))
    await waitFor(() => expect(within(screen.getByLabelText('Request flow nodes')).getByRole('button', { name: /list_notes/ })).toBeTruthy())
    expect(screen.getByText('Relations (2)')).toBeTruthy()

    fireEvent.click(within(screen.getByLabelText('Request flow nodes')).getByRole('button', { name: /list_notes/ }))
    expect(onExpandNode).toHaveBeenCalledTimes(1)
    fireEvent.click(screen.getByRole('button', { name: 'Continue from here' }))

    await waitFor(() => expect(onExpandNode).toHaveBeenLastCalledWith('handler', 'both', 0))
    await waitFor(() => expect(within(screen.getByLabelText('Request flow nodes')).getByRole('button', { name: /fetch_notes/ })).toBeTruthy())
    expect(screen.getByText('Relations (3)')).toBeTruthy()
    expect(Number.parseFloat((screen.getByLabelText('Request flow nodes') as HTMLElement).style.width)).toBeGreaterThan(1240)
  })

  it('keeps the selected node and reprojects from it when request direction changes', async () => {
    const onExpandNode = vi.fn()
      .mockResolvedValueOnce(requestExpansionGraph('endpoint', [
        { id: 'handler', type: 'function', label: 'list_notes', file_path: 'api/routes.py' },
      ], [
        { source: 'endpoint', target: 'handler', type: 'exposes_endpoint', confidence: 1, evidence_level: 'deep' },
      ]))
      .mockResolvedValueOnce(requestExpansionGraph('handler', [
        { id: 'endpoint', type: 'endpoint', label: 'GET /notes', file_path: 'api/routes.py' },
      ], [
        { source: 'endpoint', target: 'handler', type: 'exposes_endpoint', confidence: 1, evidence_level: 'deep' },
      ]))
    renderGraph(requestSeedGraph(), { graphView: 'api-flow', projection: requestProjection, onExpandNode })

    fireEvent.click(screen.getByRole('button', { name: /GET \/notes/ }))
    await waitFor(() => expect(onExpandNode).toHaveBeenCalledTimes(1))
    fireEvent.click(within(screen.getByLabelText('Request flow nodes')).getByRole('button', { name: /list_notes/ }))
    fireEvent.click(within(screen.getByLabelText('Request path direction')).getByRole('button', { name: 'Upstream' }))

    await waitFor(() => expect(onExpandNode).toHaveBeenLastCalledWith('handler', 'incoming', 0))
    expect(screen.queryByText('2 of 2 entry points loaded')).toBeNull()
    expect(screen.getByLabelText('Selected request flow entity')).toBeTruthy()
    expect(screen.getByRole('heading', { name: 'list_notes' })).toBeTruthy()
    expect(screen.getByText('Relations (1)')).toBeTruthy()
  })

  it('explains why a client call has no upstream hop', async () => {
    const onExpandNode = vi.fn().mockResolvedValue(requestExpansionGraph('client-call', [], []))
    renderGraph(requestSeedGraph(), { graphView: 'api-flow', projection: requestProjection, onExpandNode })

    fireEvent.click(within(screen.getByLabelText('Request path direction')).getByRole('button', { name: 'Upstream' }))
    fireEvent.click(screen.getByRole('button', { name: /loadNotes/ }))

    await waitFor(() => expect(onExpandNode).toHaveBeenCalledWith('client-call', 'incoming', 0))
    expect(screen.getByRole('button', { name: 'Client call is the first indexed boundary' }).hasAttribute('disabled')).toBe(true)
  })

  it('discloses hidden entry points and requests the next deterministic page', () => {
    const onProjection = vi.fn()
    const graph = requestSeedGraph()
    graph.counts!.available_nodes = 5
    graph.additional_starting_points = 3
    const rendered = renderGraph(graph, { graphView: 'api-flow', projection: requestProjection, onProjection })

    expect(screen.getByText('2 of 5 entry points loaded')).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: 'Load next 3' }))

    expect(onProjection).toHaveBeenCalledWith({
      projectionMode: 'seeds',
      seedLimit: 3,
      maxNodes: 40,
      neighborOffset: 2,
    })

    const nextPage = requestSeedGraph()
    nextPage.nodes = [{ id: 'endpoint-more', type: 'endpoint', label: 'GET /more', file_path: 'api/more.py', coverage: 'deep_indexed' }]
    nextPage.seeds = [{ node_id: 'endpoint-more', reason_codes: ['server_endpoint', 'handler_resolved'], incoming_available: 0, outgoing_available: 1 }]
    nextPage.counts = { available_nodes: 5, included_nodes: 1, available_edges: 0, included_edges: 0, available_counts_are_estimates: false }
    nextPage.additional_starting_points = 2
    rendered.rerender(
      <GraphPage
        graph={nextPage}
        graphView="api-flow"
        projection={{ ...requestProjection, neighborOffset: 2, seedLimit: 3 }}
        overview={null}
        onGraphView={vi.fn()}
        onProjection={onProjection}
        onExpandNode={vi.fn()}
        onAnalyzeArea={vi.fn()}
      />,
    )

    expect(screen.getByText('3 of 5 entry points loaded')).toBeTruthy()
  })
})

describe('GraphPage focused call-flow UX', () => {
  it('starts from ranked callables instead of an arbitrary repository graph slice', () => {
    renderGraph(callSeedGraph(), { graphView: 'function-flow', projection: callProjection })

    expect(screen.getByRole('heading', { name: 'Call Flow' })).toBeTruthy()
    expect(screen.getByText('2 of 2 callables loaded')).toBeTruthy()
    expect(screen.getByRole('button', { name: 'Calls' })).toBeTruthy()
    expect(screen.getByRole('button', { name: 'Called by' })).toBeTruthy()
    expect(screen.getByRole('button', { name: 'Both' })).toBeTruthy()
    expect(screen.queryByText('validate()')).toBeNull()
    expect(screen.getByText('Relations (0)')).toBeTruthy()
  })

  it('launches a contextual value trace from a selected callable', async () => {
    const onTraceValue = vi.fn()
    const onExpandNode = vi.fn().mockResolvedValue(callExpansionGraph())
    renderGraph(callSeedGraph(), { graphView: 'function-flow', projection: callProjection, onExpandNode, onTraceValue })

    fireEvent.click(screen.getByRole('button', { name: /ReservationService\.create/ }))
    await waitFor(() => expect(screen.getByLabelText('Selected call flow entity')).toBeTruthy())
    fireEvent.click(screen.getByRole('button', { name: /Trace values in this function/ }))

    expect(onTraceValue).toHaveBeenCalledWith({ kind: 'scope', filePath: 'services/reservation.py', startLine: 40, endLine: 72, label: 'ReservationService.create' })
  })

  it('opens callers and callees, inspects an edge, and does not expand on node selection', async () => {
    const onExpandNode = vi.fn().mockResolvedValue(callExpansionGraph())
    renderGraph(callSeedGraph(), { graphView: 'function-flow', projection: callProjection, onExpandNode })

    fireEvent.click(screen.getByRole('button', { name: /ReservationService.create/ }))
    await waitFor(() => expect(onExpandNode).toHaveBeenCalledWith('root', 'both', 0))
    await waitFor(() => expect(screen.getByText('Relations (3)')).toBeTruthy())

    fireEvent.click(within(screen.getByLabelText('Call flow nodes')).getByRole('button', { name: 'Function validate' }))
    expect(onExpandNode).toHaveBeenCalledTimes(1)
    expect(screen.getByLabelText('Selected call flow entity')).toBeTruthy()
    expect(screen.getByText('Direct callers visible')).toBeTruthy()

    fireEvent.click(screen.getByRole('button', { name: /ReservationService.create Resolved call validate/ }))
    expect(screen.getByLabelText('Selected call relation')).toBeTruthy()
    expect(screen.getByText('services/reservation.py:45')).toBeTruthy()
    expect(screen.getByText('Static symbol resolution')).toBeTruthy()
    expect(screen.getByText(/not runtime observations or calibrated probabilities/)).toBeTruthy()
  })

  it('shows unresolved targets explicitly and reprojects from the selected callable on direction change', async () => {
    const onExpandNode = vi.fn()
      .mockResolvedValueOnce(callExpansionGraph())
      .mockResolvedValueOnce(callExpansionGraph('callee', 'incoming'))
    renderGraph(callSeedGraph(), { graphView: 'function-flow', projection: callProjection, onExpandNode })

    fireEvent.click(screen.getByRole('button', { name: /ReservationService.create/ }))
    await waitFor(() => expect(screen.getByText('Unresolved target')).toBeTruthy())
    expect(screen.getByText(/Target could not be statically resolved/)).toBeTruthy()

    fireEvent.click(within(screen.getByLabelText('Call flow nodes')).getByRole('button', { name: 'Function validate' }))
    fireEvent.click(within(screen.getByLabelText('Call direction')).getByRole('button', { name: 'Called by' }))

    await waitFor(() => expect(onExpandNode).toHaveBeenLastCalledWith('callee', 'incoming', 0))
    expect(screen.getByRole('heading', { name: 'validate' })).toBeTruthy()
  })

  it('places dense callers and callees in separate non-overlapping rectangles', async () => {
    const dense = denseCallExpansionGraph(9, 11)
    const onExpandNode = vi.fn().mockResolvedValue(dense)
    const { container } = renderGraph(callSeedGraph(), { graphView: 'function-flow', projection: callProjection, onExpandNode })

    fireEvent.click(screen.getByRole('button', { name: /ReservationService.create/ }))
    await waitFor(() => expect(within(screen.getByLabelText('Call flow nodes')).getAllByRole('button')).toHaveLength(21 + dense.edges.length))

    const nodeButtons = [...container.querySelectorAll<HTMLElement>('.call-flow-node')]
    expect(nodeButtons).toHaveLength(21)
    expect(rectangleOverlaps(nodeButtons, 190, 86)).toEqual([])
  })

  it('pans the canvas and drags a node without turning the drag into selection', async () => {
    const onExpandNode = vi.fn().mockResolvedValue(callExpansionGraph())
    const { container } = renderGraph(callSeedGraph(), { graphView: 'function-flow', projection: callProjection, onExpandNode })
    fireEvent.click(screen.getByRole('button', { name: /ReservationService.create/ }))
    await waitFor(() => expect(screen.getByText('Relations (3)')).toBeTruthy())

    const viewport = screen.getByRole('region', { name: /Pannable call canvas/ }) as HTMLElement
    fireEvent.pointerDown(viewport, { pointerId: 1, button: 0, clientX: 320, clientY: 220 })
    fireEvent.pointerMove(viewport, { pointerId: 1, clientX: 120, clientY: 90 })
    expect(viewport.scrollLeft).toBe(200)
    expect(viewport.scrollTop).toBe(130)
    expect(viewport.classList.contains('panning')).toBe(true)
    fireEvent.pointerUp(viewport, { pointerId: 1 })
    expect(viewport.classList.contains('panning')).toBe(false)

    const callee = within(screen.getByLabelText('Call flow nodes')).getByRole('button', { name: 'Function validate' }) as HTMLElement
    const edge = screen.getByRole('button', { name: /ReservationService.create Resolved call validate/ })
    const initialLeft = callee.style.left
    const initialPath = edge.getAttribute('d')
    fireEvent.pointerDown(callee, { pointerId: 2, button: 0, clientX: 100, clientY: 100 })
    fireEvent.pointerMove(callee, { pointerId: 2, clientX: 180, clientY: 155 })
    fireEvent.pointerUp(callee, { pointerId: 2 })

    expect(callee.style.left).not.toBe(initialLeft)
    expect(edge.getAttribute('d')).not.toBe(initialPath)
    fireEvent.click(callee)
    expect(screen.getByRole('heading', { name: 'ReservationService.create' })).toBeTruthy()
    fireEvent.click(callee)
    expect(screen.getByRole('heading', { name: 'validate' })).toBeTruthy()
    expect(container.querySelectorAll('.draggable-graph-node').length).toBeGreaterThan(0)
  })
})

describe('GraphPage progressive value-flow UX', () => {
  it('embeds the trace beside source and offers explicit close and full-graph actions', () => {
    const onCloseEmbedded = vi.fn()
    const onOpenFullGraph = vi.fn()
    render(
      <ValueTracePanel
        graph={valueSeedGraph()}
        projection={valueProjection}
        overview={null}
        onGraphView={vi.fn()}
        onProjection={vi.fn()}
        onAnalyzeArea={vi.fn()}
        onCloseEmbedded={onCloseEmbedded}
        onOpenFullGraph={onOpenFullGraph}
      />,
    )

    expect(screen.getByRole('heading', { name: 'Value Trace' })).toBeTruthy()
    expect(screen.queryByLabelText('Relationship views')).toBeNull()
    fireEvent.click(screen.getByRole('button', { name: /Open full graph/ }))
    fireEvent.click(screen.getByRole('button', { name: 'Close embedded value trace' }))
    expect(onOpenFullGraph).toHaveBeenCalledOnce()
    expect(onCloseEmbedded).toHaveBeenCalledOnce()
  })

  it('returns a full value graph to its source context', () => {
    const onReturnToSource = vi.fn()
    render(
      <GraphPage
        graph={valueSeedGraph()}
        graphView="data-flow"
        projection={valueProjection}
        overview={null}
        onGraphView={vi.fn()}
        onProjection={vi.fn()}
        onAnalyzeArea={vi.fn()}
        onReturnToSource={onReturnToSource}
      />,
    )

    fireEvent.click(screen.getByRole('button', { name: /Back to source/ }))
    expect(onReturnToSource).toHaveBeenCalledOnce()
  })

  it('starts from semantic indexed values and explains the supported traversal language', () => {
    renderGraph(valueSeedGraph(), { graphView: 'data-flow', projection: valueProjection })

    expect(screen.getByRole('heading', { name: 'Value Trace' })).toBeTruthy()
    expect(screen.getByRole('button', { name: 'Comes from' })).toBeTruthy()
    expect(screen.getByRole('button', { name: 'Flows to' })).toBeTruthy()
    expect(screen.getByRole('button', { name: 'Both' })).toBeTruthy()
    expect(screen.getByText('3 of 5 values loaded')).toBeTruthy()
    expect(screen.getByRole('button', { name: 'Parameter price' })).toBeTruthy()
    expect(screen.getByRole('button', { name: 'Definition subtotal' })).toBeTruthy()
    expect(screen.getByText(/cross-function flow is unavailable/i)).toBeTruthy()
    expect(screen.getByText('Relations (0)')).toBeTruthy()
  })

  it('shows contextual guidance instead of a repository-wide value catalogue', () => {
    renderGraph({ ...valueSeedGraph(), nodes: [], seeds: [], counts: { available_nodes: 0, included_nodes: 0, available_edges: 0, included_edges: 0, available_counts_are_estimates: false } }, {
      graphView: 'data-flow',
      projection: { ...valueProjection, rootKeys: [] },
    })

    expect(screen.getByRole('heading', { name: 'Start from a value in context' })).toBeTruthy()
    expect(screen.getAllByText(/Code Explorer.*Request Flow.*Call Flow/i)).toHaveLength(2)
    expect(screen.queryByText(/Load next/)).toBeNull()
  })

  it('expands one value step, inspects evidence, and reprojects with user-facing direction', async () => {
    const onExpandNode = vi.fn()
      .mockResolvedValueOnce(valueExpansionGraph('both'))
      .mockResolvedValueOnce(valueExpansionGraph('incoming'))
    renderGraph(valueSeedGraph(), { graphView: 'data-flow', projection: valueProjection, onExpandNode })

    fireEvent.click(screen.getByRole('button', { name: 'Definition subtotal' }))
    await waitFor(() => expect(onExpandNode).toHaveBeenCalledWith('definition', 'both', 0))
    await waitFor(() => expect(screen.getByText('Relations (2)')).toBeTruthy())

    expect(within(screen.getByLabelText('Value flow nodes')).getByRole('button', { name: 'Use price' })).toBeTruthy()
    const edge = screen.getByRole('button', { name: /price Contributes to definition subtotal/ })
    fireEvent.click(edge)
    expect(screen.getByLabelText('Selected value relation')).toBeTruthy()
    expect(screen.getByText('Intraprocedural')).toBeTruthy()
    expect(screen.getByText(/not a runtime trace or calibrated probability/)).toBeTruthy()

    fireEvent.click(within(screen.getByLabelText('Value direction')).getByRole('button', { name: 'Comes from' }))
    await waitFor(() => expect(onExpandNode).toHaveBeenLastCalledWith('definition', 'incoming', 0))
  })

  it('explains resolved direct-call argument bindings without claiming complete global flow', async () => {
    const onExpandNode = vi.fn().mockResolvedValue(interproceduralValueExpansionGraph())
    renderGraph(interproceduralValueSeedGraph(), { graphView: 'data-flow', projection: valueProjection, onExpandNode })

    expect(screen.getByText(/resolved direct Python calls are traced/i)).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: 'Call argument raw' }))
    await waitFor(() => expect(onExpandNode).toHaveBeenCalledWith('argument', 'both', 0))

    const edge = await screen.findByRole('button', { name: /raw Binds to callee parameter value/ })
    fireEvent.click(edge)
    expect(screen.getByText('Resolved direct Python call boundary')).toBeTruthy()
    expect(screen.getByText(/not a runtime trace/i)).toBeTruthy()
  })
})

function renderGraph(
  graph: GraphData,
  options: {
    graphView?: GraphView
    onGraphView?: (view: GraphView) => void
    onProjection?: (patch: Partial<GraphProjectionInput>) => void
    onExpandNode?: (nodeId: string, direction: GraphProjectionInput['direction'], neighborOffset?: number) => Promise<GraphData | null>
    onTraceValue?: (context: ValueTraceContext) => void
    projection?: GraphProjectionInput
  } = {},
) {
  return render(
    <GraphPage
      graph={graph}
      graphView={options.graphView ?? 'dependencies'}
      projection={options.projection ?? projection}
      overview={null}
      onGraphView={options.onGraphView ?? vi.fn()}
      onProjection={options.onProjection ?? vi.fn()}
      onExpandNode={options.onExpandNode}
      onTraceValue={options.onTraceValue}
      onAnalyzeArea={vi.fn()}
    />,
  )
}

const requestProjection: GraphProjectionInput = {
  ...projection,
  projectionMode: 'seeds',
  dependencyScope: undefined,
  nodeTypes: ['endpoint', 'api_call'],
  edgeTypes: ['calls_api', 'exposes_endpoint', 'calls'],
  seedLimit: 24,
}

const callProjection: GraphProjectionInput = {
  ...projection,
  projectionMode: 'seeds',
  dependencyScope: undefined,
  direction: 'both',
  maxDepth: 1,
  nodeTypes: ['function', 'method', 'external_call', 'unresolved_call'],
  edgeTypes: ['calls', 'calls_external', 'calls_unresolved'],
  seedLimit: 24,
}

const valueProjection: GraphProjectionInput = {
  ...projection,
  projectionMode: 'seeds',
  dependencyScope: undefined,
  direction: 'both',
  maxDepth: 1,
  rootKeys: [encodeValueTraceContext({ kind: 'scope', filePath: 'domain/totals.py', startLine: 4, endLine: 8, label: 'calculate_total' })],
  nodeTypes: ['dfg_node'],
  edgeTypes: [],
  seedLimit: 24,
}

function callSeedGraph(): GraphData {
  return {
    nodes: [
      { id: 'root', type: 'method', label: 'ReservationService.create', file_path: 'services/reservation.py', start_line: 40, end_line: 72, coverage: 'deep_indexed' },
      { id: 'recursive', type: 'function', label: 'walk_tree', file_path: 'core/tree.py', start_line: 21, coverage: 'deep_indexed' },
    ],
    edges: [],
    counts: { available_nodes: 2, included_nodes: 2, available_edges: 4, included_edges: 0, available_counts_are_estimates: false },
    coverage: { state: 'limited', measured: { indexed_callables: 2, resolved_call_relations: 2, external_call_relations: 0, unresolved_call_relations: 1, direct_recursive_callables: 1 }, unknown: ['unresolved_call_targets'] },
    truncation: { truncated: false },
    provenance: { source: 'active_index_compatibility_graph', deterministic_order: true, support_levels: ['deep'] },
    seed_strategy: 'callable-starting-points/v1',
    seeds: [
      { node_id: 'root', reason_codes: ['many_callees'], incoming_available: 1, outgoing_available: 2 },
      { node_id: 'recursive', reason_codes: ['direct_recursion'], incoming_available: 1, outgoing_available: 1 },
    ],
    additional_starting_points: 0,
  }
}

function callExpansionGraph(rootId = 'root', direction: GraphProjectionInput['direction'] = 'both'): GraphData {
  const root = rootId === 'callee'
    ? { id: 'callee', type: 'function', label: 'validate', file_path: 'services/validation.py', start_line: 8, coverage: 'deep_indexed' as const }
    : { id: 'root', type: 'method', label: 'ReservationService.create', file_path: 'services/reservation.py', start_line: 40, end_line: 72, coverage: 'deep_indexed' as const }
  const allNodes: GraphData['nodes'] = [
    root,
    { id: 'root', type: 'method', label: 'ReservationService.create', file_path: 'services/reservation.py', start_line: 40, end_line: 72, coverage: 'deep_indexed' },
    { id: 'caller', type: 'function', label: 'create_endpoint', file_path: 'api/routes.py', coverage: 'deep_indexed' },
    { id: 'callee', type: 'function', label: 'validate', file_path: 'services/validation.py', start_line: 8, coverage: 'deep_indexed' },
    { id: 'unresolved', type: 'unresolved_call', label: 'plugin.execute', file_path: 'services/reservation.py', start_line: 66, coverage: 'deep_indexed' },
  ]
  const allEdges: GraphData['edges'] = [
    { source: 'caller', target: 'root', type: 'calls', confidence: 0.96, evidence_level: 'deep' },
    { source: 'root', target: 'callee', type: 'calls', confidence: 0.94, evidence_level: 'deep', metadata: { path: 'services/reservation.py', line: '45' } },
    { source: 'root', target: 'unresolved', type: 'calls_unresolved', confidence: 0.25, evidence_level: 'deep' },
  ]
  const edges = rootId === 'callee' ? allEdges.filter((edge) => edge.target === 'callee') : allEdges
  const visibleIds = new Set([rootId, ...edges.flatMap((edge) => [edge.source, edge.target])])
  const nodes = [...new Map(allNodes.map((node) => [node.id, node])).values()].filter((node) => visibleIds.has(node.id))
  return {
    nodes,
    edges,
    counts: { available_nodes: nodes.length, included_nodes: nodes.length, available_edges: edges.length, included_edges: edges.length, available_counts_are_estimates: false },
    coverage: { state: rootId === 'root' ? 'limited' : 'ready', measured: {}, unknown: rootId === 'root' ? ['unresolved_call_targets'] : [] },
    truncation: { truncated: false },
    provenance: { source: 'active_index_compatibility_graph', deterministic_order: true, support_levels: ['deep'] },
    expansion: { root_key: rootId, incoming_available: edges.filter((edge) => edge.target === rootId).length, outgoing_available: edges.filter((edge) => edge.source === rootId).length, included_neighbors: nodes.length - 1, remaining_neighbors: 0, next_neighbor_offset: null, leaf: false, limited: false },
    projection: { root_keys: [rootId], node_types: callProjection.nodeTypes, edge_types: callProjection.edgeTypes, direction, max_depth: 1, max_nodes: 13, max_edges: 24, min_confidence: 0, support_levels: [], projection_mode: 'neighbors', neighbor_offset: 0 },
  }
}

function denseCallExpansionGraph(callerCount: number, calleeCount: number): GraphData {
  const root = { id: 'root', type: 'method', label: 'ReservationService.create', file_path: 'services/reservation.py', coverage: 'deep_indexed' as const }
  const callers = Array.from({ length: callerCount }, (_, index) => ({ id: `caller-${index}`, type: 'function', label: `caller_${index}`, file_path: `api/caller_${index}.py`, coverage: 'deep_indexed' as const }))
  const callees = Array.from({ length: calleeCount }, (_, index) => ({ id: `callee-${index}`, type: 'function', label: `callee_${index}`, file_path: `services/callee_${index}.py`, coverage: 'deep_indexed' as const }))
  const edges: GraphData['edges'] = [
    ...callers.map((node) => ({ source: node.id, target: root.id, type: 'calls', confidence: 0.9, evidence_level: 'deep' as const })),
    ...callees.map((node) => ({ source: root.id, target: node.id, type: 'calls', confidence: 0.9, evidence_level: 'deep' as const })),
  ]
  return {
    nodes: [root, ...callers, ...callees],
    edges,
    counts: { available_nodes: 1 + callerCount + calleeCount, included_nodes: 1 + callerCount + calleeCount, available_edges: edges.length, included_edges: edges.length, available_counts_are_estimates: false },
    coverage: { state: 'ready', measured: {}, unknown: [] },
    truncation: { truncated: false },
    provenance: { source: 'active_index_compatibility_graph', deterministic_order: true, support_levels: ['deep'] },
    expansion: { root_key: root.id, incoming_available: callerCount, outgoing_available: calleeCount, included_neighbors: callerCount + calleeCount, remaining_neighbors: 0, next_neighbor_offset: null, leaf: false, limited: false },
  }
}

function valueSeedGraph(): GraphData {
  const nodes: GraphData['nodes'] = [
    { id: 'parameter', type: 'dfg_node', role: 'parameter', label: 'parameter: price', file_path: 'domain/totals.py', start_line: 4, coverage: 'deep_indexed' },
    { id: 'definition', type: 'dfg_node', role: 'definition', label: 'definition: subtotal', file_path: 'domain/totals.py', start_line: 5, coverage: 'deep_indexed' },
    { id: 'use', type: 'dfg_node', role: 'use', label: 'use: subtotal', file_path: 'domain/totals.py', start_line: 6, coverage: 'deep_indexed' },
  ]
  return {
    nodes,
    edges: [],
    counts: { available_nodes: 5, included_nodes: 3, available_edges: 3, included_edges: 0, available_counts_are_estimates: false },
    coverage: { state: 'limited', measured: { indexed_value_nodes: 5, parameter_nodes: 1, definition_nodes: 1, use_nodes: 3, supported_value_relations: 3 }, unknown: ['interprocedural_value_flow_unavailable'] },
    truncation: { truncated: false },
    provenance: { source: 'active_index_compatibility_graph', deterministic_order: true, support_levels: ['inferred'] },
    seed_strategy: 'value-starting-points/v1',
    seeds: [
      { node_id: 'parameter', reason_codes: ['value_parameter', 'has_supported_use'], incoming_available: 0, outgoing_available: 1 },
      { node_id: 'definition', reason_codes: ['value_definition', 'has_supported_origin', 'has_supported_use'], incoming_available: 1, outgoing_available: 1 },
      { node_id: 'use', reason_codes: ['value_use', 'has_supported_origin'], incoming_available: 1, outgoing_available: 0 },
    ],
    additional_starting_points: 2,
  }
}

function valueExpansionGraph(direction: GraphProjectionInput['direction']): GraphData {
  const allNodes: GraphData['nodes'] = [
    { id: 'origin-use', type: 'dfg_node', role: 'use', label: 'use: price', file_path: 'domain/totals.py', start_line: 5, coverage: 'deep_indexed' },
    { id: 'definition', type: 'dfg_node', role: 'definition', label: 'definition: subtotal', file_path: 'domain/totals.py', start_line: 5, coverage: 'deep_indexed' },
    { id: 'return-use', type: 'dfg_node', role: 'use', label: 'use: subtotal', file_path: 'domain/totals.py', start_line: 6, coverage: 'deep_indexed' },
  ]
  const allEdges: GraphData['edges'] = [
    { source: 'origin-use', target: 'definition', type: 'dfg_computed_from', confidence: 0.85, evidence_level: 'inferred' },
    { source: 'definition', target: 'return-use', type: 'dfg_returned', confidence: 0.85, evidence_level: 'inferred' },
  ]
  const edges = direction === 'incoming' ? allEdges.slice(0, 1) : allEdges
  const visibleIds = new Set(['definition', ...edges.flatMap((edge) => [edge.source, edge.target])])
  const nodes = allNodes.filter((node) => visibleIds.has(node.id))
  return {
    nodes,
    edges,
    counts: { available_nodes: nodes.length, included_nodes: nodes.length, available_edges: edges.length, included_edges: edges.length, available_counts_are_estimates: false },
    coverage: { state: 'ready', measured: {}, unknown: [] },
    truncation: { truncated: false },
    provenance: { source: 'active_index_compatibility_graph', deterministic_order: true, support_levels: ['inferred'] },
    expansion: { root_key: 'definition', incoming_available: 1, outgoing_available: direction === 'incoming' ? 0 : 1, included_neighbors: nodes.length - 1, remaining_neighbors: 0, next_neighbor_offset: null, leaf: false, limited: false },
  }
}

function interproceduralValueSeedGraph(): GraphData {
  return {
    nodes: [{ id: 'argument', type: 'dfg_node', role: 'argument', label: 'argument: raw', file_path: 'api/orders.py', start_line: 12, coverage: 'deep_indexed' }],
    edges: [],
    counts: { available_nodes: 1, included_nodes: 1, available_edges: 1, included_edges: 0, available_counts_are_estimates: false },
    coverage: { state: 'limited', measured: { indexed_value_nodes: 1, parameter_nodes: 0, definition_nodes: 0, use_nodes: 0, supported_value_relations: 1 }, unknown: ['interprocedural_value_flow_limited'] },
    truncation: { truncated: false },
    provenance: { source: 'active_index_compatibility_graph', deterministic_order: true, support_levels: ['inferred'] },
    seed_strategy: 'value-context-starting-points/v1',
    seeds: [{ node_id: 'argument', reason_codes: ['value_role_unresolved', 'has_supported_use'], incoming_available: 0, outgoing_available: 1 }],
    additional_starting_points: 0,
  }
}

function interproceduralValueExpansionGraph(): GraphData {
  return {
    nodes: [
      { id: 'argument', type: 'dfg_node', role: 'argument', label: 'argument: raw', file_path: 'api/orders.py', start_line: 12, coverage: 'deep_indexed' },
      { id: 'parameter', type: 'dfg_node', role: 'parameter', label: 'parameter: value', file_path: 'domain/orders.py', start_line: 4, coverage: 'deep_indexed' },
    ],
    edges: [{ source: 'argument', target: 'parameter', type: 'dfg_argument_to_parameter', confidence: 0.9, evidence_level: 'inferred' }],
    counts: { available_nodes: 2, included_nodes: 2, available_edges: 1, included_edges: 1, available_counts_are_estimates: false },
    coverage: { state: 'limited', measured: {}, unknown: ['interprocedural_value_flow_limited'] },
    truncation: { truncated: false },
    provenance: { source: 'active_index_compatibility_graph', deterministic_order: true, support_levels: ['inferred'] },
    expansion: { root_key: 'argument', incoming_available: 0, outgoing_available: 1, included_neighbors: 1, remaining_neighbors: 0, next_neighbor_offset: null, leaf: false, limited: true },
  }
}

function rectangleOverlaps(elements: HTMLElement[], width: number, height: number) {
  const boxes = elements.map((element) => ({
    label: element.getAttribute('aria-label') ?? '',
    left: Number.parseFloat(element.style.left),
    top: Number.parseFloat(element.style.top),
  }))
  const overlaps: string[] = []
  boxes.forEach((left, index) => boxes.slice(index + 1).forEach((right) => {
    if (Math.abs(left.left - right.left) < width && Math.abs(left.top - right.top) < height) overlaps.push(`${left.label} / ${right.label}`)
  }))
  return overlaps
}

function requestSeedGraph(): GraphData {
  const nodes = [
    { id: 'endpoint', type: 'endpoint', label: 'GET /notes', file_path: 'api/routes.py', start_line: 20, end_line: 26, coverage: 'deep_indexed' as const },
    { id: 'client-call', type: 'api_call', label: 'loadNotes', file_path: 'web/api.ts', coverage: 'deep_indexed' as const },
  ]
  return {
    nodes,
    edges: [],
    counts: { available_nodes: 2, included_nodes: 2, available_edges: 2, included_edges: 0, available_counts_are_estimates: false },
    coverage: { state: 'ready', measured: { indexed_endpoints: 1, resolved_handlers: 1, client_api_calls: 1, matched_client_calls: 1 }, unknown: [] },
    truncation: { truncated: false },
    provenance: { source: 'active_index_compatibility_graph', deterministic_order: true, support_levels: ['deep'] },
    seed_strategy: 'request-entry-points/v1',
    seeds: [
      { node_id: 'endpoint', reason_codes: ['server_endpoint', 'handler_resolved'], incoming_available: 1, outgoing_available: 1 },
      { node_id: 'client-call', reason_codes: ['client_api_call', 'client_call_matched'], incoming_available: 0, outgoing_available: 1 },
    ],
    additional_starting_points: 0,
  }
}

function requestExpansionGraph(
  rootId: string,
  neighbors: GraphData['nodes'],
  edges: GraphData['edges'],
): GraphData {
  const root = rootId === 'endpoint'
    ? { id: rootId, type: 'endpoint', label: 'GET /notes', file_path: 'api/routes.py', start_line: 20, end_line: 26, coverage: 'deep_indexed' as const }
    : rootId === 'client-call'
      ? { id: rootId, type: 'api_call', label: 'loadNotes', file_path: 'web/api.ts', coverage: 'deep_indexed' as const }
      : { id: rootId, type: 'function', label: 'list_notes', file_path: 'api/routes.py', coverage: 'deep_indexed' as const }
  return {
    nodes: [root, ...neighbors],
    edges,
    counts: { available_nodes: neighbors.length + 1, included_nodes: neighbors.length + 1, available_edges: edges.length, included_edges: edges.length, available_counts_are_estimates: false },
    coverage: { state: 'ready', measured: {}, unknown: [] },
    truncation: { truncated: false },
    provenance: { source: 'active_index_compatibility_graph', deterministic_order: true, support_levels: ['deep'] },
    expansion: {
      root_key: rootId,
      incoming_available: edges.filter((edge) => edge.target === rootId).length,
      outgoing_available: edges.filter((edge) => edge.source === rootId).length,
      included_neighbors: neighbors.length,
      remaining_neighbors: 0,
      next_neighbor_offset: null,
      leaf: neighbors.length === 0,
      limited: false,
    },
  }
}

function seedGraph(nodeCount: number, overrides: Partial<GraphData> = {}): GraphData {
  const nodes = Array.from({ length: nodeCount }, (_, index) => ({
    id: `seed-${index}`,
    type: 'file',
    label: `Seed ${index}`,
    file_path: `src/seed-${index}.py`,
    coverage: 'deep_indexed' as const,
  }))
  return {
    nodes,
    edges: [],
    counts: { available_nodes: nodeCount + 4, included_nodes: nodeCount, available_edges: 0, included_edges: 0, available_counts_are_estimates: false },
    coverage: { state: 'ready', measured: {}, unknown: [] },
    truncation: { truncated: false },
    provenance: { source: 'active_index_compatibility_graph', deterministic_order: true, support_levels: ['deep'] },
    dependency_scope_used: 'internal',
    seed_strategy: 'dependency-starting-points/v1',
    seeds: nodes.map((node, index) => ({
      node_id: node.id,
      reason_codes: index ? ['graph_region_representative'] : ['application_entrypoint', 'many_dependents'],
      incoming_available: index,
      outgoing_available: index === 0 ? 2 : 0,
    })),
    additional_starting_points: 4,
    ...overrides,
  }
}

function expansionGraph(
  rootId: string,
  childIds: string[],
  options: { remaining?: number; nextOffset?: number | null } = {},
): GraphData {
  const remaining = options.remaining ?? 0
  return {
    nodes: [
      { id: rootId, type: 'file', label: 'Seed 0', file_path: 'src/seed-0.py', coverage: 'deep_indexed' },
      ...childIds.map((id) => ({ id, type: 'file', label: id, file_path: `src/${id}.py`, coverage: 'deep_indexed' as const })),
    ],
    edges: childIds.map((id) => ({ source: rootId, target: id, type: 'imports_internal', confidence: 1, evidence_level: 'deep' as const })),
    counts: { available_nodes: childIds.length + 1 + remaining, included_nodes: childIds.length + 1, available_edges: childIds.length + remaining, included_edges: childIds.length, available_counts_are_estimates: false },
    coverage: { state: remaining ? 'limited' : 'ready', measured: {}, unknown: [] },
    truncation: { truncated: Boolean(remaining), reason: remaining ? 'node_budget' : undefined },
    provenance: { source: 'active_index_compatibility_graph', deterministic_order: true, support_levels: ['deep'] },
    dependency_scope_used: 'internal',
    expansion: {
      root_key: rootId,
      incoming_available: 0,
      outgoing_available: childIds.length + remaining,
      included_neighbors: childIds.length,
      remaining_neighbors: remaining,
      next_neighbor_offset: options.nextOffset === undefined ? null : options.nextOffset,
      leaf: childIds.length === 0 && remaining === 0,
      limited: Boolean(remaining),
    },
  }
}
