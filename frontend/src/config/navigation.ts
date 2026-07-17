import type { IconName, Page } from '../types/api'

export const managementNav: { page: Page; label: string; icon: IconName }[] = [
  { page: 'projects', label: 'Projects', icon: 'folder' },
  { page: 'indexing', label: 'Index Jobs', icon: 'layers' },
  { page: 'settings', label: 'Settings', icon: 'settings' },
]

export const workspaceNav: { page: Page; label: string; icon: IconName }[] = [
  { page: 'overview', label: 'Overview', icon: 'home' },
  { page: 'code', label: 'Code Explorer', icon: 'nodes' },
  { page: 'graph', label: 'Graph View', icon: 'share' },
  { page: 'api', label: 'API Explorer', icon: 'sliders' },
  { page: 'assistant', label: 'AI Assistant', icon: 'spark' },
]

export const pipelineSteps = [
  'Prepare source',
  'Scan and filter files',
  'Analyze languages',
  'Extract code structure',
  'Create searchable chunks',
  'Build relationship graph',
  'Save index',
  'Finalize',
]
