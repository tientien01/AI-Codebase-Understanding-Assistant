import { Link } from 'react-router-dom'
import { PageTitle, Panel } from '../../components/common/ui'

export function RouteRecoveryPage({
  title,
  description,
  requestedPath,
  actionPath = '/projects',
  actionLabel = 'Back to Projects',
  onRetry,
}: {
  title: string
  description: string
  requestedPath?: string
  actionPath?: string
  actionLabel?: string
  onRetry?: () => void
}) {
  return (
    <div className="route-recovery" role="status">
      <PageTitle title={title} subtitle={description} />
      <Panel title="Recovery options">
        {requestedPath && (
          <p>
            Requested location: <code>{requestedPath}</code>
          </p>
        )}
        <div className="route-recovery-actions">
          {onRetry && <button className="secondary" onClick={onRetry}>Try Again</button>}
          <Link className="primary" to={actionPath}>{actionLabel}</Link>
        </div>
      </Panel>
    </div>
  )
}
