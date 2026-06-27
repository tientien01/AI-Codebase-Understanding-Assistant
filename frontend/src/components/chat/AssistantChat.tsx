import type { FormEvent } from 'react'
import type { ChatMessage, Citation } from '../../types/api'
import { Panel } from '../common/ui'

type AssistantChatProps = {
  input: string
  messages: ChatMessage[]
  disabled: boolean
  full?: boolean
  onInput: (value: string) => void
  onSubmit: (event?: FormEvent) => void
  onEvidence: (citation: Citation) => void
}

export function AssistantPanel(props: Omit<AssistantChatProps, 'full'>) {
  return (
    <Panel title="AI Assistant">
      <AssistantChat {...props} />
    </Panel>
  )
}

export function AssistantChat({
  input,
  messages,
  disabled,
  full = false,
  onInput,
  onSubmit,
  onEvidence,
}: AssistantChatProps) {
  return (
    <div className={full ? 'assistant-chat full' : 'assistant-chat'}>
      <div className="chat-feed">
        {messages.map((message, index) => (
          <article className={`chat-message ${message.role}`} key={`${message.role}-${index}`}>
            <strong>{message.role === 'user' ? 'You' : 'Assistant'}</strong>
            <p>{message.content}</p>
            {message.citations && message.citations.length > 0 && (
              <div className="citation-list">
                {message.citations.map((citation) => (
                  <button key={citation.evidence_id} onClick={() => onEvidence(citation)}>
                    {citation.file_path}:{citation.start_line}-{citation.end_line}
                  </button>
                ))}
              </div>
            )}
            {message.evidenceSufficient === false && <span className="badge amber">Insufficient evidence</span>}
          </article>
        ))}
      </div>
      <form className="chat-form" onSubmit={onSubmit}>
        <input disabled={disabled} value={input} onChange={(event) => onInput(event.target.value)} placeholder={disabled ? 'Index a repository before chatting.' : 'Ask anything about your codebase...'} />
        <button className="primary" disabled={disabled}>Send</button>
      </form>
    </div>
  )
}
