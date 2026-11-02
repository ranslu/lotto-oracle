export type Lag = { game: string; have: string; want: string }
export type Readiness = { checkedAt: string; behind: Lag[]; next: string; error?: string }

declare module 'claude-code' {
  interface PluginState {
    'lotto-ready': { readiness: Readiness | null; isRefreshing: boolean }
  }
}
