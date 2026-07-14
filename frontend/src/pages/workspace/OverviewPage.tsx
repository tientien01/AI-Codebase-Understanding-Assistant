import { useMemo, useState } from 'react'
import { Icon } from '../../components/common/Icon'
import { EmptyState, PageTitle, Panel } from '../../components/common/ui'
import type { ArchitectureComponent, ArchitectureOverview, ArchitectureRelation, IconName, Overview } from '../../types/api'

const COMPACT_ITEM_LIMIT = 4

export function OverviewPage({
  overview,
  onExploreArchitecture,
  onExploreFlow,
  onOpenFile,
}: {
  overview: Overview | null
  onQuestion: (question: string) => void
  onExploreArchitecture?: () => void
  onExploreFlow?: () => void
  onOpenFile?: (filePath: string) => void
}) {
  const [tourOpen, setTourOpen] = useState(false)
  const [tourIndex, setTourIndex] = useState(0)
  const [showAllFiles, setShowAllFiles] = useState(false)
  const [showAllAreas, setShowAllAreas] = useState(false)
  const [expandedFlowId, setExpandedFlowId] = useState<string | null>(null)
  const tourSteps = useMemo(() => buildTourSteps(overview), [overview])

  if (!overview) return <EmptyState title="Repository is not indexed" description="Open an indexed repository to view the workspace overview." />

  const architecture = overview.architecture ?? fallbackArchitecture(overview)
  const visibleFiles = showAllFiles ? overview.important_files : overview.important_files.slice(0, COMPACT_ITEM_LIMIT)
  const keyAreas = architecture.components.filter((component) => (
    ['api', 'application', 'domain', 'data_access', 'messaging', 'external_adapter', 'infrastructure'].includes(component.kind)
    || (component.kind === 'module' && Boolean(architecture.style))
  ))
  const visibleAreas = showAllAreas ? keyAreas : keyAreas.slice(0, COMPACT_ITEM_LIMIT)
  const confirmedRelations = architecture.relations.filter((relation) => relation.support === 'confirmed').length
  const activeStep = tourSteps[tourIndex]

  return (
    <div className="overview-page sixty-second-overview">
      <PageTitle title={overview.name} subtitle={architecture.summary} />
      <div className="technology-strip" aria-label="Detected technologies">
        <span className={`architecture-state ${architecture.coverage_state}`}>{architecture.system_type}</span>
        {architecture.style ? <span className="architecture-style-chip" title={architecture.style_reason}>{architectureStyleLabel(architecture.style)}</span> : null}
        {architecture.technologies.slice(0, 7).map((technology) => <span key={technology}>{technology}</span>)}
      </div>
      <div className="overview-fact-strip" aria-label="Repository architecture summary">
        <Fact icon="file" value={overview.stats.files ?? 0} label="files" />
        <Fact icon="route" value={overview.stats.endpoints ?? 0} label="endpoints" />
        <Fact icon="layers" value={architecture.components.filter((item) => !['actor', 'container'].includes(item.kind)).length} label="architecture areas" />
        <Fact icon="check" value={confirmedRelations} label="confirmed relations" />
      </div>

      <section className="architecture-hero architecture-system-hero" aria-labelledby="architecture-title">
        <div className="architecture-hero-head">
          <div>
            <span className="eyebrow">Repository mental model</span>
            <h2 id="architecture-title">Architecture Overview</h2>
            <p>Understand the system in 60 seconds.</p>
          </div>
          <div className="architecture-actions">
            <button
              className="secondary"
              type="button"
              aria-label="Start Guided Tour"
              disabled={!tourSteps.length}
              onClick={() => { setTourOpen(true); setTourIndex(0) }}
            >
              Take Repository Tour
            </button>
            <button className="primary" type="button" aria-label="Explore Architecture" onClick={onExploreArchitecture}>Explore Graph</button>
          </div>
        </div>

        <ArchitectureMap architecture={architecture} onExplore={onExploreArchitecture} />

        <div className="architecture-map-footer">
          <div className="architecture-legend" aria-label="Relationship support legend">
            <span><i className="solid" />Confirmed relation</span>
            <span><i className="dashed" />Inferred relation</span>
          </div>
          <span>Generated from indexed endpoints, symbols, imports, technology markers, and graph evidence.</span>
        </div>
        {architecture.unknowns.length ? (
          <details className="architecture-unknowns">
            <summary>{architecture.unknowns.length} architecture limitation{architecture.unknowns.length === 1 ? '' : 's'}</summary>
            <ul>{architecture.unknowns.map((unknown) => <li key={unknown}>{unknown}</li>)}</ul>
          </details>
        ) : null}
      </section>

      {tourOpen && activeStep ? (
        <section className="guided-tour compact" aria-labelledby="guided-tour-title">
          <div className="tour-progress"><span>Repository Tour</span><strong>Step {tourIndex + 1} of {tourSteps.length}</strong></div>
          <div className="tour-body">
            <ol aria-label="Tour steps">
              {tourSteps.map((step, index) => (
                <li className={index === tourIndex ? 'active' : index < tourIndex ? 'done' : ''} key={`${step.title}-${index}`}>
                  <button type="button" onClick={() => setTourIndex(index)}>{index + 1}. {step.title}</button>
                </li>
              ))}
            </ol>
            <div className="tour-step-detail">
              <span className="eyebrow">Why this step</span>
              <h2 id="guided-tour-title">{activeStep.title}</h2>
              <p>{activeStep.reason}</p>
              <div className="tour-signal"><strong>Indexed signal</strong><span>{activeStep.signal}</span></div>
              {activeStep.filePath ? <button className="secondary" type="button" onClick={() => onOpenFile?.(activeStep.filePath!)}>Open Source</button> : null}
            </div>
          </div>
          <div className="tour-actions">
            <button type="button" onClick={() => setTourOpen(false)}>Exit tour</button>
            <button type="button" disabled={tourIndex === 0} onClick={() => setTourIndex((value) => Math.max(0, value - 1))}>Previous</button>
            <button className="primary" type="button" disabled={tourIndex === tourSteps.length - 1} onClick={() => setTourIndex((value) => Math.min(tourSteps.length - 1, value + 1))}>Next step</button>
          </div>
        </section>
      ) : null}

      <div className="overview-detail-grid">
        <Panel title="Primary Flows">
          <div className="primary-flow-list">
            {architecture.primary_flows.length ? architecture.primary_flows.slice(0, 3).map((flow) => {
              const expanded = expandedFlowId === flow.id
              const panelId = `primary-flow-${flow.id.replace(/[^a-zA-Z0-9_-]/g, '-')}`
              return (
                <article className={`primary-flow-item ${expanded ? 'expanded' : ''}`} key={flow.id}>
                  <button
                    className="primary-flow-card"
                    type="button"
                    aria-label={`${expanded ? 'Collapse' : 'Show'} ${flow.label}`}
                    aria-expanded={expanded}
                    aria-controls={panelId}
                    onClick={() => setExpandedFlowId((current) => current === flow.id ? null : flow.id)}
                  >
                    <span className="semantic-icon"><Icon name="route" /></span>
                    <span className="primary-flow-copy">
                      <strong>{flow.label}</strong>
                      <small>{flow.steps.map((step) => step.label).join(' → ')}</small>
                    </span>
                    <span className="primary-flow-action">View flow <Icon name="chevronRight" size={13} /></span>
                  </button>
                  {expanded ? (
                    <div className="primary-flow-details" id={panelId}>
                      <ol className="primary-flow-diagram" aria-label={`${flow.label} steps`}>
                        {flow.steps.map((step, index) => (
                          <li className={`support-${step.support}`} key={`${step.component_id}-${index}`}>
                            <span className="flow-step-index">{index + 1}</span>
                            <span><strong>{step.label}</strong><small>{supportLabel(step.support)}</small></span>
                          </li>
                        ))}
                      </ol>
                      <div className="primary-flow-footer">
                        <span>{flow.summary}</span>
                        <button className="secondary" type="button" onClick={onExploreFlow}>Open in Graph <Icon name="chevronRight" size={13} /></button>
                      </div>
                    </div>
                  ) : null}
                </article>
              )
            }) : <p>No supported primary flow is available yet.</p>}
          </div>
        </Panel>

        <Panel title="Recommended Reading">
          <div className="compact-overview-list">
            {visibleFiles.length ? visibleFiles.map((file) => (
              <button type="button" key={file.file_path} onClick={() => onOpenFile?.(file.file_path)}>
                <span className="semantic-icon" aria-hidden="true"><Icon name={fileIcon(file.file_path, file.reason)} /></span>
                <span><strong>{file.file_path}</strong><small>{file.reason}</small></span>
                <span aria-hidden="true">›</span>
              </button>
            )) : <p>No important-file signal is available; no reading order is being invented.</p>}
          </div>
          {overview.important_files.length > COMPACT_ITEM_LIMIT ? (
            <button className="overview-more" type="button" aria-expanded={showAllFiles} onClick={() => setShowAllFiles((value) => !value)}>
              {showAllFiles ? 'Show fewer files' : `View all ${overview.important_files.length} files`}
            </button>
          ) : null}
        </Panel>

        <Panel title="Key Areas">
          <div className="compact-overview-list area-list">
            {visibleAreas.length ? visibleAreas.map((area) => (
              <button type="button" key={area.id} onClick={onExploreArchitecture}>
                <span className="semantic-icon" aria-hidden="true"><Icon name={componentIcon(area)} /></span>
                <span><strong>{area.label}</strong><small>{area.summary}</small></span>
                <span>{area.endpoint_count ? `${area.endpoint_count} API` : area.technology ?? ''}</span>
              </button>
            )) : <p>No key architecture area is supported by the current index.</p>}
          </div>
          {keyAreas.length > COMPACT_ITEM_LIMIT ? (
            <button className="overview-more" type="button" aria-expanded={showAllAreas} onClick={() => setShowAllAreas((value) => !value)}>
              {showAllAreas ? 'Show fewer areas' : `View all ${keyAreas.length} areas`}
            </button>
          ) : null}
        </Panel>
      </div>
    </div>
  )
}

function ArchitectureMap({ architecture, onExplore }: { architecture: ArchitectureOverview; onExplore?: () => void }) {
  const components = architecture.components
  const actor = components.find((item) => item.kind === 'actor')
  const presentation = components.find((item) => item.kind === 'presentation')
  const backend = components.find((item) => item.kind === 'container')
  const api = components.filter((item) => item.kind === 'api' && item.role !== 'operational')
  const operational = components.filter((item) => item.kind === 'api' && item.role === 'operational')
  const application = components.filter((item) => item.kind === 'application')
  const domain = components.filter((item) => item.kind === 'domain')
  const dataAccess = components.filter((item) => item.kind === 'data_access')
  const messaging = components.filter((item) => item.kind === 'messaging')
  const integrations = components.filter((item) => item.kind === 'external_adapter')
  const entrypoints = components.filter((item) => item.kind === 'entrypoint')
  const modules = components.filter((item) => item.kind === 'module')
  const infrastructure = components.filter((item) => item.kind === 'infrastructure')
  const presentationRelation = relationFor(architecture.relations, presentation?.id, backend?.id)
  const apiApplication = layerRelation(architecture.relations, api, application)
  const applicationData = layerRelation(architecture.relations, application, dataAccess)

  if (['mvc', 'event_driven', 'library', 'cli', 'package_map'].includes(architecture.style ?? '') || (Boolean(architecture.style) && modules.length > 0)) {
    return <AdaptiveArchitectureMap architecture={architecture} onExplore={onExplore} />
  }

  if (!actor && !presentation && !backend && !api.length && !application.length && !dataAccess.length) {
    return <div className="architecture-empty"><strong>Architecture coverage is limited.</strong><span>The current index does not expose enough application boundaries to draw a supported system map.</span></div>
  }

  return (
    <>
    <div className="architecture-system-map" aria-label="High-level repository architecture">
      <div className="architecture-entry-chain">
        {actor ? <ArchitectureNode component={actor} onExplore={onExplore} /> : null}
        {actor && presentation ? <MapConnector relation={relationFor(architecture.relations, actor.id, presentation.id)} fallbackLabel="uses" /> : null}
        {presentation ? <ArchitectureNode component={presentation} onExplore={onExplore} /> : null}
        {presentation && backend ? <MapConnector relation={presentationRelation} fallbackLabel="HTTPS / JSON" direction="horizontal" /> : null}
      </div>

      {backend || api.length || application.length || dataAccess.length ? (
        <div className="backend-architecture-container">
          <div className="backend-container-title"><span className="semantic-icon"><Icon name="server" /></span><strong>{backend?.label ?? 'Application Backend'}</strong><small>{backend?.technology}</small></div>
          {entrypoints.length ? <ArchitectureLayer label="Entrypoints" components={entrypoints} onExplore={onExplore} empty="" /> : null}
          <ArchitectureLayer label="API Layer" components={api} onExplore={onExplore} empty="No API boundary detected" />
          {operational.length ? <ArchitectureLayer label="Operational" components={operational} onExplore={onExplore} empty="" /> : null}
          {(api.length && application.length) ? <VerticalConnector relation={apiApplication} fallbackLabel="calls" /> : null}
          <ArchitectureLayer label="Application Layer" components={application} onExplore={onExplore} empty="No service boundary detected" />
          {domain.length ? <ArchitectureLayer label="Domain Layer" components={domain} onExplore={onExplore} empty="" /> : null}
          {(application.length && dataAccess.length) ? <VerticalConnector relation={applicationData} fallbackLabel="reads / writes" /> : null}
          <ArchitectureLayer label="Data Access Layer" components={dataAccess} onExplore={onExplore} empty="No data-access boundary detected" />
          {messaging.length ? <ArchitectureLayer label="Messaging / Workers" components={messaging} onExplore={onExplore} empty="" /> : null}
          {integrations.length ? <ArchitectureLayer label="External Adapters" components={integrations} onExplore={onExplore} empty="" /> : null}
        </div>
      ) : null}

      {infrastructure.length ? (
        <div className="infrastructure-zone">
          <span>Infrastructure &amp; External Systems</span>
          <div>{infrastructure.map((component) => {
            const relation = architecture.relations.find((item) => item.target === component.id)
            return (
              <div className={`infrastructure-node ${relation?.support ?? 'unknown'}`} key={component.id}>
                <span className="infrastructure-link-label">{relation?.label ?? 'uses'}</span>
                <ArchitectureNode component={component} onExplore={onExplore} compact />
              </div>
            )
          })}</div>
        </div>
      ) : null}
    </div>
    </>
  )
}

function AdaptiveArchitectureMap({ architecture, onExplore }: { architecture: ArchitectureOverview; onExplore?: () => void }) {
  const visible = architecture.components.filter((component) => !['actor', 'container', 'infrastructure'].includes(component.kind))
  const groups = Array.from(new Set(visible.map((component) => component.layer))).map((layer) => ({
    layer,
    components: visible.filter((component) => component.layer === layer),
  }))
  const infrastructure = architecture.components.filter((component) => component.kind === 'infrastructure')

  return (
    <>
    <div className={`adaptive-architecture-map style-${architecture.style ?? 'package_map'}`} aria-label="Adaptive repository architecture">
      <div className="adaptive-layer-chain">
        {groups.map((group, index) => (
          <section className="adaptive-layer" key={group.layer}>
            <span>{architectureLayerLabel(group.layer)}</span>
            <div>{group.components.map((component) => <ArchitectureNode key={component.id} component={component} onExplore={onExplore} compact />)}</div>
            {index < groups.length - 1 ? <i className="adaptive-layer-arrow" aria-hidden="true" /> : null}
          </section>
        ))}
      </div>
      {infrastructure.length ? (
        <section className="adaptive-infrastructure">
          <span>Infrastructure &amp; External Systems</span>
          <div>{infrastructure.map((component) => <ArchitectureNode key={component.id} component={component} onExplore={onExplore} compact />)}</div>
        </section>
      ) : null}
    </div>
    </>
  )
}

function ArchitectureLayer({ label, components, onExplore, empty }: { label: string; components: ArchitectureComponent[]; onExplore?: () => void; empty: string }) {
  return (
    <section className="architecture-component-layer">
      <span>{label}</span>
      <div>{components.length ? components.map((component) => <ArchitectureNode key={component.id} component={component} onExplore={onExplore} compact />) : <small>{empty}</small>}</div>
    </section>
  )
}

function ArchitectureNode({ component, onExplore, compact = false }: { component: ArchitectureComponent; onExplore?: () => void; compact?: boolean }) {
  return (
    <button className={`architecture-map-node kind-${component.kind} ${compact ? 'compact' : ''}`} type="button" onClick={onExplore}>
      <span className="semantic-icon"><Icon name={componentIcon(component)} /></span>
      <span><strong>{component.label}</strong><small>{component.technology ?? component.summary}</small></span>
    </button>
  )
}

function MapConnector({ relation, fallbackLabel, direction = 'vertical' }: { relation?: ArchitectureRelation; fallbackLabel: string; direction?: 'vertical' | 'horizontal' }) {
  return <div className={`map-connector ${direction} ${relation?.support ?? 'unknown'}`}><span>{relation?.label ?? fallbackLabel}</span><i aria-hidden="true" /></div>
}

function VerticalConnector({ relation, fallbackLabel }: { relation?: ArchitectureRelation; fallbackLabel: string }) {
  if (!relation) return <div className="vertical-map-connector unknown"><span>{fallbackLabel}: relationship not confirmed</span></div>
  return <div className={`vertical-map-connector ${relation.support}`}><i aria-hidden="true" /><span>{relation.label}</span></div>
}

function Fact({ icon, value, label }: { icon: IconName; value: number; label: string }) {
  return <span><Icon name={icon} /><strong>{value}</strong>{label}</span>
}

function relationFor(relations: ArchitectureRelation[], source?: string, target?: string) {
  return relations.find((relation) => relation.source === source && relation.target === target)
}

function layerRelation(relations: ArchitectureRelation[], sources: ArchitectureComponent[], targets: ArchitectureComponent[]) {
  const sourceIds = new Set(sources.map((item) => item.id))
  const targetIds = new Set(targets.map((item) => item.id))
  return relations.find((relation) => sourceIds.has(relation.source) && targetIds.has(relation.target))
}

function componentIcon(component: ArchitectureComponent): IconName {
  const label = component.label.toLowerCase()
  if (component.kind === 'actor') return 'home'
  if (component.kind === 'presentation') return 'monitor'
  if (component.kind === 'container') return 'server'
  if (component.kind === 'api') return label.includes('auth') ? 'shield' : 'route'
  if (component.kind === 'application') return label.includes('recommend') ? 'spark' : 'layers'
  if (component.kind === 'domain') return 'box'
  if (component.kind === 'data_access' || component.kind === 'infrastructure') return 'database'
  if (component.kind === 'messaging') return 'bell'
  if (component.kind === 'external_adapter') return 'share'
  if (component.kind === 'entrypoint') return 'code'
  return 'box'
}

function architectureStyleLabel(style: NonNullable<ArchitectureOverview['style']>) {
  return ({ layered_web: 'Layered Web', backend_api: 'Backend API', mvc: 'MVC', modular: 'Modular', event_driven: 'Event-driven', library: 'Library / SDK', cli: 'CLI', package_map: 'Package Map' })[style]
}

function architectureLayerLabel(layer: string) {
  return ({ entrypoint: 'Entrypoints', presentation: 'Presentation', api: 'API', application: 'Application', domain: 'Domain', data_access: 'Data Access', messaging: 'Messaging / Workers', integration: 'External Adapters', package: 'Packages' } as Record<string, string>)[layer] ?? layer.replaceAll('_', ' ')
}

function supportLabel(support: 'confirmed' | 'inferred' | 'unknown') {
  if (support === 'confirmed') return 'Confirmed by indexed evidence'
  if (support === 'inferred') return 'Inferred from repository structure'
  return 'Relationship support is unknown'
}

function fileIcon(path: string, reason: string): IconName {
  const value = `${path} ${reason}`.toLowerCase()
  if (value.includes('readme') || value.includes('overview')) return 'book'
  if (value.includes('route') || value.includes('api')) return 'route'
  if (value.includes('service')) return 'layers'
  if (value.includes('model') || value.includes('repository') || value.includes('schema')) return 'database'
  if (value.includes('main') || value.includes('entrypoint')) return 'monitor'
  return 'file'
}

function fallbackArchitecture(overview: Overview): ArchitectureOverview {
  return {
    system_type: 'Indexed codebase',
    summary: 'Architecture classification is unavailable for this compatibility response.',
    technologies: overview.detected_stack,
    components: overview.modules.slice(0, 6).map((module) => ({
      id: `module:${module.name}`, label: module.name, kind: 'module', layer: 'module', summary: module.summary,
      file_paths: [], endpoint_count: 0, evidence: [],
    })),
    relations: [],
    primary_flows: [],
    coverage_state: 'limited',
    unknowns: ['Relationships remain unknown here until Graph Explorer confirms them.'],
  }
}

function buildTourSteps(overview: Overview | null) {
  if (!overview) return []
  const fileSteps = overview.important_files.slice(0, 6).map((file) => ({
    title: file.file_path,
    reason: file.reason,
    signal: 'Important-file reason produced by the current index.',
    filePath: file.file_path,
  }))
  if (fileSteps.length) return fileSteps
  return overview.modules.slice(0, 6).map((module) => ({
    title: module.name,
    reason: module.summary,
    signal: `${module.file_count} files grouped by current indexing rules. No source entrypoint was reported.`,
    filePath: undefined,
  }))
}
