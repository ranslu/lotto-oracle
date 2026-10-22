/** Absolute path -> 'read' or 'edit' (edit wins). */
export type Touched = Record<string, 'read' | 'edit'>

declare module 'claude-code' {
  interface PluginState {
    'file-tree': { touched: Touched; open: string[]; root: string; rev: number }
  }
}
