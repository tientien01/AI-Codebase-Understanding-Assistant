import type { FormEvent } from 'react'
import { AssistantChat, ConversationHistory } from '../../components/chat/AssistantChat'
import { PageTitle } from '../../components/common/ui'
import type { ChatMessage, Citation, ConversationSummary } from '../../types/api'

export function AssistantFullPage({
  input,
  messages,
  disabled,
  conversations,
  activeConversationId,
  activeConversationStale,
  pending,
  replayLoading,
  replayError,
  onInput,
  onSubmit,
  onEvidence,
  onNewChat,
  onSelectConversation,
  onDeleteConversation,
}: {
  input: string
  messages: ChatMessage[]
  disabled: boolean
  conversations: ConversationSummary[]
  activeConversationId?: string
  activeConversationStale: boolean
  pending: boolean
  replayLoading: boolean
  replayError: boolean
  onInput: (value: string) => void
  onSubmit: (event?: FormEvent) => void
  onEvidence: (citation: Citation) => void
  onNewChat: () => void
  onSelectConversation: (conversationId: string) => void
  onDeleteConversation: (conversationId: string) => void
}) {
  return (
    <div>
      <PageTitle title="AI Assistant" subtitle="Ask grounded questions about architecture, API flow, debugging, onboarding, and impact." />
      <div className="assistant-full-layout">
        <aside className="assistant-full-history">
          <button className="primary" type="button" onClick={onNewChat}>New Chat</button>
          <ConversationHistory
            conversations={conversations}
            activeConversationId={activeConversationId}
            onSelect={onSelectConversation}
            onDelete={onDeleteConversation}
          />
        </aside>
        <section className="assistant-conversation" aria-label="Current conversation">
          {!activeConversationId && <div className="assistant-new-chat-label">New Chat <span>This repository has no selected conversation yet.</span></div>}
          <AssistantChat
          input={input}
          messages={messages}
          disabled={disabled}
          activeConversationStale={activeConversationStale}
          pending={pending}
          replayLoading={replayLoading}
          replayError={replayError}
          onInput={onInput}
          onSubmit={onSubmit}
          onEvidence={onEvidence}
            full
          />
        </section>
      </div>
    </div>
  )
}
