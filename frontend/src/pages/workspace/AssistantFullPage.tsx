import type { FormEvent } from 'react'
import { AssistantChat } from '../../components/chat/AssistantChat'
import { PageTitle } from '../../components/common/ui'
import type { ChatMessage, Citation } from '../../types/api'

export function AssistantFullPage({
  input,
  messages,
  disabled,
  onInput,
  onSubmit,
  onEvidence,
}: {
  input: string
  messages: ChatMessage[]
  disabled: boolean
  onInput: (value: string) => void
  onSubmit: (event?: FormEvent) => void
  onEvidence: (citation: Citation) => void
}) {
  return (
    <div>
      <PageTitle title="AI Assistant" subtitle="Ask grounded questions about architecture, API flow, debugging, onboarding, and impact." />
      <AssistantChat input={input} messages={messages} disabled={disabled} onInput={onInput} onSubmit={onSubmit} onEvidence={onEvidence} full />
    </div>
  )
}
