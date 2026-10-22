export type Step = { id: string; tool: string; what: string; state: 'run' | 'ok' | 'err'; ms: number }
export type Turn = {
  prompt: string
  startedAt: number
  endedAt: number | null
  steps: Step[]
}

declare module 'claude-code' {
  interface PluginState {
    'savvy-progress': { turn: Turn | null; history: Turn[]; now: number }
  }
}
