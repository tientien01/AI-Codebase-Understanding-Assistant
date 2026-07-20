import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'
import { AssistantChat } from './AssistantChat'

afterEach(cleanup)

describe('AssistantChat provider disclosure', () => {
  it('renders only server-declared generation and retrieval outcomes', () => {
    render(<AssistantChat input="" disabled={false} messages={[
      { role: 'assistant', content: 'Grounded', generationMode: 'ollama', providerState: 'ready', retrievalMode: 'hybrid' },
      { role: 'assistant', content: 'Fallback', generationMode: 'deterministic_fallback', providerState: 'degraded', retrievalMode: 'sparse' },
      { role: 'assistant', content: 'Historical outcome unknown' },
    ]} onInput={() => undefined} onSubmit={() => undefined} onEvidence={() => undefined} />)

    expect(screen.getByText('Ollama')).toBeTruthy()
    expect(screen.getByText('Hybrid retrieval')).toBeTruthy()
    expect(screen.getByText('Deterministic fallback')).toBeTruthy()
    expect(screen.getByText('Sparse retrieval')).toBeTruthy()
    expect(screen.getAllByLabelText('Assistant response outcome')).toHaveLength(2)
  })
})
