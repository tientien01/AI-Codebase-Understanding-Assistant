import type { ReactNode } from 'react'
import { Icon } from './Icon'

export function Panel({ title, action, children }: { title: string; action?: string; children: ReactNode }) {
  return (
    <section className="panel">
      <div className="panel-head">
        <h2>{title}</h2>
        {action && <button>{action}</button>}
      </div>
      {children}
    </section>
  )
}

export function SideInfo({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="side-info">
      <h2>{title}</h2>
      {children}
    </section>
  )
}

export function PageTitle({ title, subtitle }: { title: string; subtitle: string }) {
  return (
    <div className="page-title">
      <h1>{title}</h1>
      <p>{subtitle}</p>
    </div>
  )
}

export function Metric({ label, value }: { label: string; value?: string | number }) {
  return (
    <div className="metric">
      <span>{label}</span>
      <strong>{value ?? 0}</strong>
    </div>
  )
}

export function StatCell({ label, value }: { label: string; value?: string | number }) {
  return (
    <div className="stat-cell">
      <span>{label}</span>
      <strong>{value ?? 0}</strong>
    </div>
  )
}

export function ListRow({ title, detail, meta }: { title: string; detail: string; meta?: string }) {
  return (
    <div className="list-row">
      <strong>{title}</strong>
      <p>{detail}</p>
      {meta && <span>{meta}</span>}
    </div>
  )
}

export function EmptyState({ title, description, action, onAction }: { title: string; description: string; action?: string; onAction?: () => void }) {
  return (
    <div className="empty-state">
      <h2>{title}</h2>
      <p>{description}</p>
      {action && <button className="primary" onClick={onAction}>{action}</button>}
    </div>
  )
}

export function PreviewLine({ label, value }: { label: string; value: string }) {
  return <div className="preview-line"><span>{label}</span><strong>{value}</strong></div>
}

export function ConfigRow({ label, value }: { label: string; value: string }) {
  return <div className="config-row"><span>{label}</span><strong>{value}</strong></div>
}

export function LanguageBar({ label, value }: { label: string; value: number }) {
  return (
    <div className="language-bar">
      <PreviewLine label={label} value={`${value}%`} />
      <Progress value={value} />
    </div>
  )
}

export function Progress({ value }: { value: number }) {
  return (
    <div className="progress">
      <span style={{ width: `${Math.max(0, Math.min(100, value))}%` }} />
    </div>
  )
}

export function InDevelopmentInline({ text }: { text: string }) {
  return (
    <div className="developing-inline">
      <span>Dang phat trien</span>
      <p>{text}</p>
    </div>
  )
}

export function InDevelopmentPanel({ title, detail }: { title: string; detail: string }) {
  return (
    <Panel title={title}>
      <InDevelopmentInline text={detail} />
    </Panel>
  )
}

export function WizardSteps({ activeStep = 0 }: { activeStep?: number }) {
  return (
    <div className="wizard">
      {['Import', 'Preview', 'Index'].map((step, index) => (
        <div className={`wizard-step ${index === activeStep ? 'active' : ''}`} key={step}>
          <span>{index + 1}</span>{step}
        </div>
      ))}
    </div>
  )
}

export function SourceCard({ label, detail, active, onClick }: { label: string; detail: string; active: boolean; onClick: () => void }) {
  return (
    <button type="button" className={`source-card ${active ? 'active' : ''}`} onClick={onClick}>
      <strong>{label}</strong>
      <span>{detail}</span>
    </button>
  )
}

export function ProfileCard({ title, detail, active = false }: { title: string; detail: string; active?: boolean }) {
  return (
    <div className={`profile-card ${active ? 'active' : ''}`}>
      <strong>{title}</strong>
      <p>{detail}</p>
      {active && <span>Recommended</span>}
    </div>
  )
}

export function Checklist({ items, done }: { items: string[]; done: number }) {
  return (
    <div className="checklist">
      {items.map((item, index) => (
        <div key={item} className={index < done ? 'done' : ''}>
          <span>{index < done ? 'Done' : 'Todo'}</span>
          {item}
        </div>
      ))}
      <Progress value={(done / items.length) * 100} />
    </div>
  )
}

export function Activity({ text, meta, tone = 'success' }: { text: string; meta: string; tone?: 'success' | 'running' | 'danger' | 'neutral' }) {
  return (
    <div className="activity">
      <span className={`activity-icon ${tone}`}>
        <Icon name={tone === 'danger' ? 'warning' : tone === 'running' ? 'refresh' : 'check'} />
      </span>
      <span>{text}</span>
      <b>{meta}</b>
    </div>
  )
}
