import { ConfigRow, PageTitle, Panel } from '../../components/common/ui'

export function SettingsPage({ isWorkspace }: { isWorkspace: boolean }) {
  return (
    <div>
      <PageTitle title="Settings" subtitle={isWorkspace ? 'Workspace parser, RAG, LLM, and storage configuration.' : 'Project management and import settings.'} />
      <div className="settings-grid">
        <Panel title="Project Settings">
          <ConfigRow label="Default indexing profile" value="Balanced" />
          <ConfigRow label="Repository import" value="Folder and ZIP uploads enabled" />
        </Panel>
        <Panel title="Indexing Settings">
          <ConfigRow label="Ignore folders" value="node_modules, .venv, dist, build" />
          <ConfigRow label="Max file size" value="1 MB" />
          <ConfigRow label="Re-index mode" value="Full rebuild" />
        </Panel>
        <Panel title="Parser Settings">
          <ConfigRow label="Language registry" value="Enabled" />
          <ConfigRow label="Python AST" value="Enabled" />
          <ConfigRow label="Tree-sitter parsers" value="Enabled for supported source languages" />
        </Panel>
        <Panel title="RAG and LLM Settings">
          <ConfigRow label="Current retrieval" value="Keyword + metadata MVP" />
          <ConfigRow label="Vector embeddings" value="Dang phat trien" />
          <ConfigRow label="LLM provider" value="Dang phat trien" />
        </Panel>
        <Panel title="Danger Zone">
          <button className="secondary" disabled>Delete Project</button>
        </Panel>
      </div>
    </div>
  )
}
