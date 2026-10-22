/** One short line describing what a tool call is about. */
export function summarize(tool: string, input: unknown): string {
  const x = (input ?? {}) as Record<string, unknown>
  const pick = ['file_path', 'command', 'pattern', 'url', 'query', 'description', 'path', 'skill']
  for (const k of pick) {
    const v = x[k]
    if (typeof v === 'string' && v) return v.replace(/\s+/g, ' ').slice(0, 90)
  }
  return tool
}
