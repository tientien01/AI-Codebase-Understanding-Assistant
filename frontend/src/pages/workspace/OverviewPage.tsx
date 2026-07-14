import { useMemo, useState } from 'react'
import { Activity, EmptyState, ListRow, Metric, PageTitle, Panel } from '../../components/common/ui'
import type { Overview } from '../../types/api'

export function OverviewPage({
  overview,
  onQuestion,
  onExploreArchitecture,
  onOpenFile,
}: {
  overview: Overview | null
  onQuestion: (question: string) => void
  onExploreArchitecture?: () => void
  onOpenFile?: (filePath: string) => void
}) {
  const [tourOpen, setTourOpen] = useState(false)
  const [tourIndex, setTourIndex] = useState(0)
  const tourSteps = useMemo(() => buildTourSteps(overview), [overview])

  if (!overview) return <EmptyState title="Repository is not indexed" description="Open an indexed repository to view the workspace overview." />

  const questions = [
    'How does the login flow work?',
    'Which files are related to authentication?',
    'Where is JWT validation implemented?',
    'Show me the database models.',
  ]
  const activeStep = tourSteps[tourIndex]

  return (
    <div>
      <PageTitle title={overview.name} subtitle="Understand the architecture, follow a justified reading tour, and inspect the indexed signals behind every recommendation." />
      <div className="stats-strip">
        <Metric label="Files" value={overview.stats.files} />
        <Metric label="Functions" value={overview.stats.functions} />
        <Metric label="Classes" value={overview.stats.classes} />
        <Metric label="API Endpoints" value={overview.stats.endpoints} />
        <Metric label="Graph Nodes" value={overview.stats.graph_nodes} />
        <Metric label="Indexed Chunks" value={overview.stats.chunks} />
      </div>
      <section className="architecture-hero" aria-labelledby="architecture-title">
        <div className="architecture-hero-head">
          <div>
            <span className="eyebrow">Repository mental model</span>
            <h2 id="architecture-title">Architecture Overview</h2>
            <p>Move from the public boundary through indexed modules to persistence. Open Graph Explorer to validate every returned relationship.</p>
          </div>
          <div className="architecture-actions">
            <button className="primary" type="button" onClick={onExploreArchitecture}>Explore Architecture</button>
            <button type="button" disabled={!tourSteps.length} onClick={() => { setTourOpen(true); setTourIndex(0) }}>Start Guided Tour</button>
          </div>
        </div>
        <div className="architecture-layers" aria-label="Architecture layers from current indexed signals">
          <ArchitectureLayer tone="blue" label="Client and entrypoints" detail={overview.detected_stack.slice(0, 3).join(' · ') || 'No stack signal reported'} />
          <span className="architecture-flow" aria-hidden="true">↓</span>
          <ArchitectureLayer tone="purple" label="API boundary" detail={`${overview.endpoints.length} indexed endpoint${overview.endpoints.length === 1 ? '' : 's'}`} />
          <span className="architecture-flow" aria-hidden="true">↓</span>
          <ArchitectureLayer tone="cyan" label="Modules and services" detail={`${overview.modules.length} current module signal${overview.modules.length === 1 ? '' : 's'}`} />
          <span className="architecture-flow" aria-hidden="true">↓</span>
          <ArchitectureLayer tone="amber" label="Data and supporting code" detail="Confirm relationships in the bounded graph projection" />
        </div>
        <div className="architecture-disclosure">
          <span>Signals: stack, endpoints, modules, important-file reasons</span>
          <span>Missing graph evidence remains unknown until Graph Explorer confirms it.</span>
        </div>
      </section>
      {tourOpen && activeStep ? (
        <section className="guided-tour" aria-labelledby="guided-tour-title">
          <div className="tour-progress">
            <span>Guided Tour</span>
            <strong>Step {tourIndex + 1} of {tourSteps.length}</strong>
          </div>
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
      <div className="overview-grid">
        <Panel title="Recent Activity">
          <Activity text="Indexed source files" meta="latest run" />
          <Activity text="Updated API schema" meta={`${overview.endpoints.length} endpoints`} />
          <Activity text="Architecture signals refreshed" meta="current index" />
        </Panel>
        <Panel title="Key Modules">
          {overview.modules.length ? overview.modules.map((module) => <ListRow key={module.name} title={module.name} detail={module.summary} meta={`${module.file_count} files`} />) : <p>No module signal is available.</p>}
        </Panel>
        <Panel title="Suggested Questions">
          {questions.map((question) => <button className="question-row" key={question} onClick={() => onQuestion(question)}>{question}</button>)}
        </Panel>
        <Panel title="Important Files">
          {overview.important_files.length ? overview.important_files.map((file) => <button className="tour-file-row" type="button" key={file.file_path} onClick={() => onOpenFile?.(file.file_path)}><strong>{file.file_path}</strong><span>{file.reason}</span></button>) : <p>No important-file signal is available; the tour remains unavailable rather than inventing steps.</p>}
        </Panel>
        <Panel title="Documentation Gaps">
          {overview.documentation_gaps.length ? overview.documentation_gaps.map((gap) => <ListRow key={gap} title={gap} detail="Generated by current indexing rules." />) : <p>No documentation gap was reported by the current index.</p>}
        </Panel>
      </div>
    </div>
  )
}

function ArchitectureLayer({ tone, label, detail }: { tone: string; label: string; detail: string }) {
  return <div className={`architecture-layer tone-${tone}`}><strong>{label}</strong><span>{detail}</span></div>
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
