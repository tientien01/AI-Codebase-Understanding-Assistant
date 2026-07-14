import { cleanup, fireEvent, render, screen, within } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import type { GraphData, GraphProjectionInput, GraphView } from '../../types/api'
import { GraphPage } from './GraphPage'

const projection: GraphProjectionInput = {
  indexVersion: 7,
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

describe('GraphPage guided bounded projection UX', () => {
  it('starts with relationship questions instead of duplicating the architecture overview', () => {
    const onGraphView = vi.fn()
    const onProjection = vi.fn()

    renderGraph(graphFixture(4), { graphView: 'project-map', onGraphView, onProjection })

    expect(screen.getByRole('heading', { name: 'What do you want to understand?' })).toBeTruthy()
    expect(screen.getByRole('button', { name: /Dependencies/ })).toBeTruthy()
    expect(screen.getByRole('button', { name: /Request Flow/ })).toBeTruthy()
    expect(screen.getByRole('button', { name: /Call Flow/ })).toBeTruthy()
    expect(screen.queryByLabelText('Graph nodes')).toBeNull()

    fireEvent.click(screen.getByRole('button', { name: /Request Flow/ }))

    expect(onGraphView).toHaveBeenCalledWith('api-flow')
    expect(onProjection).toHaveBeenCalledWith({
      rootKeys: [],
      nodeTypes: ['endpoint', 'api_call', 'call_site', 'function', 'method'],
      edgeTypes: ['exposes_endpoint', 'contains_call', 'calls', 'calls_api'],
      supportLevels: [],
    })
  })

  it('renders every server-included node and keeps the complete relation alternative collapsed', () => {
    const graph = graphFixture(220)

    renderGraph(graph)

    expect(within(screen.getByLabelText('Graph nodes')).getAllByRole('button')).toHaveLength(220)
    expect(screen.getByText('Relations (219)')).toBeTruthy()
    expect(screen.getByText(/Showing 220 nodes and 219 relationships/)).toBeTruthy()
    expect(screen.getByText('A → B means A imports B.')).toBeTruthy()
    expect(screen.getByText('Relations (219)').closest('details')?.hasAttribute('open')).toBe(false)
  })

  it('does not dim unrelated nodes until the user explicitly selects one', () => {
    const { container } = renderGraph(graphFixture(4))

    expect(container.querySelectorAll('.graph-node.dimmed')).toHaveLength(0)

    fireEvent.click(within(screen.getByLabelText('Graph nodes')).getByRole('button', { name: /Node 1/ }))

    expect(container.querySelectorAll('.graph-node.dimmed').length).toBeGreaterThan(0)
    expect(screen.getByRole('button', { name: 'Clear selection' })).toBeTruthy()
  })

  it('discloses truncation and requests a larger bounded projection', () => {
    const onProjection = vi.fn()
    const graph = graphFixture(40, {
      counts: { available_nodes: 100, included_nodes: 40, available_edges: 99, included_edges: 39, available_counts_are_estimates: false },
      coverage: { state: 'limited', measured: {}, unknown: [] },
      truncation: { truncated: true, reason: 'node_budget' },
      can_expand: true,
    })

    renderGraph(graph, { onProjection })
    expect(screen.getByText('Limited projection')).toBeTruthy()
    expect(screen.getByText('Reason: node budget.')).toBeTruthy()

    fireEvent.click(screen.getByRole('button', { name: 'Expand bounded result' }))

    expect(onProjection).toHaveBeenCalledWith({ maxNodes: 80, maxEdges: 160 })
  })

  it('uses human-readable focus and direction controls without exposing canonical root input', () => {
    const onProjection = vi.fn()
    renderGraph(graphFixture(3), { onProjection })

    fireEvent.change(screen.getByLabelText('Direction'), { target: { value: 'outgoing' } })
    fireEvent.change(screen.getByLabelText('File or module'), { target: { value: 'node-2' } })

    expect(onProjection).toHaveBeenCalledWith({ direction: 'outgoing' })
    expect(onProjection).toHaveBeenCalledWith({ rootKeys: ['node-2'] })
    expect(screen.queryByLabelText('Root key')).toBeNull()
  })

  it('explains a valid no-edge result instead of leaving an ambiguous canvas', () => {
    renderGraph(graphFixture(1))

    expect(screen.getAllByText('No supported arrows in this result')).toHaveLength(2)
    expect(screen.getByText(/valid leaf result or an unresolved static-analysis target/)).toBeTruthy()
  })

  it('draws every returned relationship and exposes selected-node context', () => {
    const { container } = renderGraph(graphFixture(4))

    expect(container.querySelectorAll('.graph-edge')).toHaveLength(3)
    fireEvent.click(within(screen.getByLabelText('Graph nodes')).getByRole('button', { name: /Node 2/ }))

    const inspector = screen.getByLabelText('Selected graph entity')
    expect(within(inspector).getByRole('heading', { name: 'Node 2' })).toBeTruthy()
    expect(screen.getByText('Relations (3)')).toBeTruthy()
  })
})

function renderGraph(
  graph: GraphData,
  options: {
    graphView?: GraphView
    onGraphView?: (view: GraphView) => void
    onProjection?: (patch: Partial<GraphProjectionInput>) => void
  } = {},
) {
  return render(
    <GraphPage
      graph={graph}
      graphView={options.graphView ?? 'dependencies'}
      projection={projection}
      overview={null}
      onGraphView={options.onGraphView ?? vi.fn()}
      onProjection={options.onProjection ?? vi.fn()}
      onAnalyzeArea={vi.fn()}
    />,
  )
}

function graphFixture(nodeCount: number, overrides: Partial<GraphData> = {}): GraphData {
  const nodes = Array.from({ length: nodeCount }, (_, index) => ({
    id: `node-${index}`,
    type: 'file',
    label: `Node ${index}`,
    file_path: `src/node-${index}.py`,
    coverage: 'deep_indexed' as const,
  }))
  const edges = Array.from({ length: Math.max(0, nodeCount - 1) }, (_, index) => ({
    source: `node-${index}`,
    target: `node-${index + 1}`,
    type: 'imports',
    confidence: 0.9,
    evidence_level: 'deep' as const,
  }))
  return {
    nodes,
    edges,
    counts: { available_nodes: nodeCount, included_nodes: nodeCount, available_edges: edges.length, included_edges: edges.length, available_counts_are_estimates: false },
    coverage: { state: 'ready', measured: {}, unknown: [] },
    truncation: { truncated: false },
    provenance: { source: 'active_index_compatibility_graph', deterministic_order: true, support_levels: ['deep'] },
    ...overrides,
  }
}
