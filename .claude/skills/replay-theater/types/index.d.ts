export type Scene = {
  id: string
  tool: string
  what: string
  out: string
  isError: boolean
  at: number
  ms: number
  turn: number
}

declare module 'claude-code' {
  interface PluginState {
    'replay-theater': { scenes: Scene[]; pos: number; playing: boolean; turn: number }
  }
}
