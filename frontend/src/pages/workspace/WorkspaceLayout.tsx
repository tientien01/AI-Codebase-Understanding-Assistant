import type { ReactNode } from 'react'

export function WorkspacePage({ main, side, compactSide = false }: { main: ReactNode; side: ReactNode; compactSide?: boolean }) {
  return (
    <div className={`workspace-layout ${compactSide ? 'assistant-workspace-layout' : ''}`}>
      <div>{main}</div>
      <aside>{side}</aside>
    </div>
  )
}
