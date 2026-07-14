import { cleanup, fireEvent, render, screen, within } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import type { GraphData, GraphProjectionInput } from '../../types/api'
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

describe('GraphPage bounded projection UX', () => {
  it('renders every server-included node and the complete accessible relation list', () => {
    const graph = graphFixture(220)

    renderGraph(graph)

    expect(within(screen.getByLabelText('Graph nodes')).getAllByRole('button')).toHaveLength(220)
    expect(screen.getByText('Accessible relation list (219)')).toBeTruthy()
    expect(screen.getByText('220 of 220 nodes and 219 of 219 relationships included.')).toBeTruthy()
  })

  it('discloses truncation and requests a larger bounded projection', () => {
    const onProjection = vi.fn()
    const graph = graphFixture(40, {
      counts: { available_nodes: 100, included_nodes: 40, available_edges: 99, included_edges: 39, available_counts_are_estimates: false },
      coverage: { state: 'limited', measured: {}, unknown: [] },
      truncation: { truncated: true, reason: 'node_budget' },
      can_expand: true,
    })

    renderGraph(graph, onProjection)
    expect(screen.getByText('Limited projection')).toBeTruthy()
    expect(screen.getByText('Reason: node budget.')).toBeTruthy()

    fireEvent.click(screen.getByRole('button', { name: 'Request a larger bounded projection' }))

    expect(onProjection).toHaveBeenCalledWith({ maxNodes: 80, maxEdges: 160 })
  })

  it('exposes keyboard-native root and direction controls', () => {
    const onProjection = vi.fn()
    renderGraph(graphFixture(3), onProjection)

    fireEvent.change(screen.getByLabelText('Direction'), { target: { value: 'outgoing' } })
    fireEvent.change(screen.getByLabelText('Root key'), { target: { value: 'node-2' } })
    fireEvent.click(screen.getByRole('button', { name: 'Apply root' }))

    expect(onProjection).toHaveBeenCalledWith({ direction: 'outgoing' })
    expect(onProjection).toHaveBeenCalledWith({ rootKeys: ['node-2'] })
  })
})

function renderGraph(graph: GraphData, onProjection = vi.fn()) {
  return render(
    <GraphPage
      graph={graph}
      graphView="project-map"
      projection={projection}
      overview={null}
      onGraphView={vi.fn()}
      onProjection={onProjection}
      onAnalyzeArea={vi.fn()}
    />,
  )
}

function graphFixture(nodeCount: number, overrides: Partial<GraphData> = {}): GraphData {
  const nodes = Array.from({ length: nodeCount }, (_, index) => ({
    id: `node-${index}`,
    type: 'function',
    label: `Node ${index}`,
    coverage: 'deep_indexed' as const,
  }))
  const edges = Array.from({ length: Math.max(0, nodeCount - 1) }, (_, index) => ({
    source: `node-${index}`,
    target: `node-${index + 1}`,
    type: 'calls',
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
