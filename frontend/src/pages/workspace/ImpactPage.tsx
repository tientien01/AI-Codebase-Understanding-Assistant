import { InDevelopmentInline, ListRow, PageTitle, Panel } from '../../components/common/ui'
import type { Overview } from '../../types/api'

export function ImpactPage({ overview }: { overview: Overview | null }) {
  return (
    <div>
      <PageTitle title="Impact Analysis" subtitle="Understand direct and indirect effects before changing a file, symbol, endpoint, or model." />
      <div className="impact-grid">
        <Panel title="Target">
          <label>
            Target type
            <select defaultValue="symbol"><option>symbol</option><option>file</option><option>endpoint</option><option>model</option></select>
          </label>
          <label>
            Target reference
            <input defaultValue="authenticate_user" />
          </label>
          <button className="primary" disabled>Run Impact Analysis</button>
        </Panel>
        <Panel title="Impact Result">
          <InDevelopmentInline text="Backend impact API is dang phat trien. Current graph has enough foundation for file/symbol/endpoint neighbors." />
          <div className="impact-columns">
            <ListRow title="Direct impact" detail={`${overview?.endpoints.length ?? 0} endpoints can be considered after graph query support.`} />
            <ListRow title="Affected tests" detail="Requires test parser and tested_by relations." />
            <ListRow title="Suggested checks" detail="Login success, invalid password, token validation." />
          </div>
        </Panel>
      </div>
    </div>
  )
}
