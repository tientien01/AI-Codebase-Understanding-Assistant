import type { ReactNode } from 'react'

export function WorkspacePage({ main, side }: { main: ReactNode; side: ReactNode }) {
  return (
    <div className="workspace-layout">
      <div>{main}</div>
      <aside>{side}</aside>
    </div>
  )
}
