import type { IconName, Page } from '../types/api'

export const managementNav: { page: Page; label: string; icon: IconName }[] = [
  { page: 'dashboard', label: 'Dashboard', icon: 'home' },
  { page: 'dashboard', label: 'Projects', icon: 'folder' },
  { page: 'dashboard', label: 'Recent', icon: 'clock' },
  { page: 'dashboard', label: 'Favorites', icon: 'star' },
  { page: 'indexing', label: 'Index Jobs', icon: 'layers' },
  { page: 'settings', label: 'Settings', icon: 'settings' },
]

export const workspaceNav: { page: Page; label: string; icon: IconName }[] = [
  { page: 'overview', label: 'Overview', icon: 'home' },
  { page: 'code', label: 'Code Explorer', icon: 'nodes' },
  { page: 'graph', label: 'Graph View', icon: 'share' },
  { page: 'api', label: 'API Explorer', icon: 'sliders' },
  { page: 'assistant', label: 'AI Assistant', icon: 'spark' },
  { page: 'impact', label: 'Impact Analysis', icon: 'target' },
  { page: 'search', label: 'Search', icon: 'search' },
  { page: 'evaluation', label: 'Evaluation', icon: 'chart' },
  { page: 'settings', label: 'Settings', icon: 'settings' },
]

export const pipelineSteps = [
  'Scan repository files',
  'Apply ignore rules',
  'Parse Python AST',
  'Parse JavaScript / TypeScript',
  'Detect FastAPI endpoints',
  'Build code graph',
  'Chunk source code',
  'Generate embeddings',
  'Store vector index',
  'Validate citations',
  'Post-process and finalize',
]
