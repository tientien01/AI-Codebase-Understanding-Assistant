import { useState } from 'react'
import type { FormEvent, KeyboardEvent } from 'react'
import type { AssistantRequestContext, ChatMessage, Citation, ConversationSummary } from '../../types/api'
import { Icon } from '../common/Icon'
import { Panel } from '../common/ui'

type AssistantChatProps = {
  input: string
  messages: ChatMessage[]
  disabled: boolean
  context?: AssistantRequestContext
  conversations?: ConversationSummary[]
  activeConversationId?: string
  activeConversationStale?: boolean
  replayLoading?: boolean
  replayError?: boolean
  full?: boolean
  onInput: (value: string) => void
  onSubmit: (event?: FormEvent) => void
  onEvidence: (citation: Citation) => void
  onRemoveContext?: () => void
  onNewChat?: () => void
  onSelectConversation?: (conversationId: string) => void
}

export function AssistantPanel(props: Omit<AssistantChatProps, 'full'>) {
  return (
    <Panel title="AI Assistant">
      <AssistantChat {...props} full />
    </Panel>
  )
}

export function CollapsibleAssistantPanel(props: Omit<AssistantChatProps, 'full'> & { suggestions?: string[] }) {
  const [open, setOpen] = useState(true)
  const [showHistory, setShowHistory] = useState(false)
  const suggestions = props.suggestions ?? []
  const hasHistory = Boolean(props.conversations?.length)

  const startNewChat = () => {
    props.onNewChat?.()
    setShowHistory(false)
  }

  return (
    <aside className={`assistant-drawer ${open ? 'open' : 'closed'}`} aria-label="AI Assistant drawer">
      <div className="assistant-drawer-header">
        <div className="assistant-drawer-title">
          <Icon name="spark" size={17} />
          {open ? <strong>AI Assistant</strong> : null}
        </div>
        {open ? (
          <div className="assistant-header-actions">
            <button type="button" onClick={startNewChat} aria-label="Start new chat">
              <Icon name="plus" size={15} /> <span>New Chat</span>
            </button>
            <button
              type="button"
              onClick={() => setShowHistory((value) => !value)}
              aria-label={showHistory ? 'Hide chat history' : 'Show chat history'}
              aria-pressed={showHistory}
              disabled={!hasHistory}
              title={hasHistory ? 'Browse saved conversations' : 'No saved conversations yet'}
            >
              <Icon name="history" size={15} />
            </button>
          </div>
        ) : null}
        <button
          className="assistant-drawer-toggle"
          type="button"
          aria-label={open ? 'Collapse AI Assistant' : 'Expand AI Assistant drawer'}
          aria-expanded={open}
          onClick={() => setOpen((value) => !value)}
        >
          <Icon name={open ? 'collapse' : 'expand'} size={16} />
        </button>
      </div>
      {open ? (
        <div className="assistant-drawer-body">
          {showHistory ? (
            <ConversationHistory
              conversations={props.conversations ?? []}
              activeConversationId={props.activeConversationId}
              onSelect={(conversationId) => {
                props.onSelectConversation?.(conversationId)
                setShowHistory(false)
              }}
            />
          ) : null}
          {!showHistory && !props.messages.length ? (
            <div className="assistant-empty-state">
              <Icon name="spark" size={22} />
              <strong>What do you want to understand?</strong>
              <p>Ask about architecture, a code path, or where to begin reading. Answers stay tied to indexed evidence.</p>
            </div>
          ) : null}
          {!showHistory && !props.messages.length && suggestions.length ? (
            <div className="assistant-suggestions" aria-label="Suggested questions">
              {suggestions.map((suggestion) => (
                <button type="button" key={suggestion} onClick={() => props.onInput(suggestion)}>{suggestion}</button>
              ))}
            </div>
          ) : null}
          {!showHistory ? <AssistantChat {...props} /> : null}
        </div>
      ) : (
        <button className="assistant-rail-action" type="button" onClick={() => setOpen(true)} aria-label="Open AI Assistant">
          <Icon name="message" size={18} />
          {props.messages.length ? <span aria-label={`${props.messages.length} messages`}>{props.messages.length}</span> : null}
        </button>
      )}
    </aside>
  )
}

export function AssistantChat({
  input,
  messages,
  disabled,
  context,
  activeConversationStale,
  replayLoading,
  replayError,
  full = false,
  onInput,
  onSubmit,
  onEvidence,
  onRemoveContext,
}: AssistantChatProps) {
  const submitOnEnter = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault()
      onSubmit()
    }
  }

  return (
    <div className={full ? 'assistant-chat full' : 'assistant-chat'}>
      <div className="chat-feed" aria-live="polite">
        {replayLoading ? <p className="assistant-replay-state" role="status">Loading conversation…</p> : null}
        {replayError ? <p className="assistant-replay-state error" role="alert">This conversation could not be loaded.</p> : null}
        {activeConversationStale ? (
          <p className="assistant-stale-notice" role="status">
            This conversation was created from an older index. New answers use only current-index evidence.
          </p>
        ) : null}
        {messages.map((message, index) => (
          <ChatMessageCard message={message} index={index} key={`${message.role}-${index}`} onEvidence={onEvidence} />
        ))}
      </div>
      <form className="chat-form" onSubmit={onSubmit}>
        {context ? (
          <div className="assistant-context-chip" aria-label="Assistant workspace context">
            <Icon name={context.page === 'code' ? 'file' : 'home'} size={14} />
            <span>
              <strong>{context.page === 'code' ? fileName(context.file_path) : 'Overview'}</strong>
              <small>{assistantContextLabel(context)}</small>
            </span>
            <button type="button" onClick={onRemoveContext} aria-label="Remove assistant context">×</button>
          </div>
        ) : null}
        <textarea
          disabled={disabled}
          rows={3}
          value={input}
          onChange={(event) => onInput(event.target.value)}
          onKeyDown={submitOnEnter}
          placeholder={disabled ? 'Index a repository before chatting.' : 'Ask anything about your codebase...'}
          aria-label="Message AI Assistant"
        />
        <div className="chat-composer-actions">
          <div>
            <button type="button" disabled title="Context selection is not available yet" aria-label="Add repository context">@</button>
            <button type="button" disabled title="Attachments are not available yet" aria-label="Attach a file"><Icon name="paperclip" size={16} /></button>
          </div>
          <span>Enter to send · Shift+Enter for a new line</span>
          <button className="primary chat-send" disabled={disabled || !input.trim()} aria-label="Send message">
            <Icon name="send" size={17} />
          </button>
        </div>
      </form>
    </div>
  )
}

export function ConversationHistory({
  conversations,
  activeConversationId,
  onSelect,
}: {
  conversations: ConversationSummary[]
  activeConversationId?: string
  onSelect: (conversationId: string) => void
}) {
  return (
    <nav className="assistant-history" aria-label="Saved conversations">
      <strong>History</strong>
      {!conversations.length ? <p>No saved conversations yet.</p> : null}
      {conversations.map((conversation) => (
        <button
          type="button"
          key={conversation.conversation_id}
          className={conversation.conversation_id === activeConversationId ? 'active' : ''}
          aria-current={conversation.conversation_id === activeConversationId ? 'page' : undefined}
          onClick={() => onSelect(conversation.conversation_id)}
        >
          <span>{conversation.title || 'Untitled conversation'}</span>
          <small>
            {conversation.message_count} messages{conversation.is_stale ? ' · older index' : ''}
          </small>
        </button>
      ))}
    </nav>
  )
}

function ChatMessageCard({ message, index, onEvidence }: { message: ChatMessage; index: number; onEvidence: (citation: Citation) => void }) {
  const citations = message.citations ?? []
  const trace = citations.slice(0, 5)

  return (
    <article className={`chat-message ${message.role}`} aria-label={`${message.role} message ${index + 1}`}>
      <div className="chat-message-author">
        <span className="chat-avatar"><Icon name={message.role === 'user' ? 'user' : 'spark'} size={14} /></span>
        <strong>{message.role === 'user' ? 'You' : 'Assistant'}</strong>
      </div>
      <p>{message.content}</p>
      {citations.length > 0 ? (
        <details className="assistant-evidence">
          <summary><span>Evidence</span><span className="evidence-count">{citations.length}</span></summary>
          <div className="citation-list">
            {citations.map((citation) => (
              <button key={citation.evidence_id} type="button" onClick={() => onEvidence(citation)}>
                <Icon name="file" size={14} />
                <span>{citation.file_path}</span>
                <small>{citation.start_line}–{citation.end_line}</small>
              </button>
            ))}
          </div>
        </details>
      ) : null}
      {trace.length > 1 ? (
        <details className="assistant-evidence evidence-trail">
          <summary><span>Evidence trail</span><span className="evidence-count">{trace.length}</span></summary>
          <div className="evidence-trail-items">
            {trace.map((citation, citationIndex) => (
              <span key={citation.evidence_id}>
                {citationIndex > 0 ? <Icon name="chevronRight" size={12} /> : null}
                <button type="button" onClick={() => onEvidence(citation)}>{fileName(citation.file_path)}</button>
              </span>
            ))}
          </div>
        </details>
      ) : null}
      {message.evidenceSufficient === false ? <span className="badge amber">Insufficient evidence</span> : null}
    </article>
  )
}

function fileName(path: string) {
  return path.split(/[\\/]/).pop() ?? path
}

function assistantContextLabel(context: AssistantRequestContext) {
  if (context.page === 'overview') return 'Current workspace page'
  const details = [context.file_path]
  if (context.start_line && context.end_line) {
    details.push(context.start_line === context.end_line
      ? `line ${context.start_line}`
      : `lines ${context.start_line}–${context.end_line}`)
  }
  if (context.symbol_name) details.push(context.symbol_name)
  return details.join(' · ')
}
