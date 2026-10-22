import { atom, read, update } from 'claude-code'
import type { EngineInterface, Register } from 'claude-code'

import { markFor } from './mark'

const PANE = 'file-tree'
const SKIP = new Set(['.git', 'node_modules', '__pycache__', '.venv', 'venv', '.next', 'dist', 'build'])
const READS = new Set(['Read', 'Grep', 'Glob'])
const EDITS = new Set(['Edit', 'Write', 'NotebookEdit'])

const touched = atom({ plugin: 'file-tree', key: 'touched' } as const, {})
const open = atom({ plugin: 'file-tree', key: 'open' } as const, [])
const root = atom({ plugin: 'file-tree', key: 'root' } as const, '')
const rev = atom({ plugin: 'file-tree', key: 'rev' } as const, 0)

type Row = { path: string; name: string; depth: number; isDir: boolean }

async function rows($: EngineInterface, dir: string, depth: number, opened: Set<string>, out: Row[], limit: number) {
  if (out.length >= limit) return
  let list
  try {
    list = await $.fs.list(dir)
  } catch {
    return
  }
  const sorted = list
    .filter(f => !SKIP.has(f.name))
    .sort((a, b) => (a.kind === 'dir' ? 0 : 1) - (b.kind === 'dir' ? 0 : 1) || a.name.localeCompare(b.name))
  for (const f of sorted) {
    if (out.length >= limit) return
    const path = `${dir}/${f.name}`
    const isDir = f.kind === 'dir'
    out.push({ path, name: f.name, depth, isDir })
    if (isDir && opened.has(path)) await rows($, path, depth + 1, opened, out, limit)
  }
}

export const register: Register = on => {
  on('session.start', async ($, e, next) => {
    await $.command.register({ name: 'files', description: 'Open the File Tree pane (/files <folder> to change root)' })
    const cwd = await $.session.cwd()
    await update($, root, r => r || cwd)
    return next(e)
  })

  on('command.run', { command: 'files' }, async ($, e) => {
    const arg = e.args.trim()
    if (arg) {
      const cwd = await $.session.cwd()
      const target = arg.startsWith('/') ? arg : `${cwd}/${arg}`
      try {
        await $.fs.list(target)
      } catch {
        return { text: `No folder at ${target}.` }
      }
      await update($, root, () => target.replace(/\/+$/, ''))
    }
    await $.ui.open({ id: PANE, title: 'File Tree' })
    return { text: `File Tree: ${await read($, root)}` }
  })

  on('tool.call', async ($, e, next) => {
    const ran = await next(e)
    const kind: 'edit' | 'read' | null = EDITS.has(e.tool) ? 'edit' : READS.has(e.tool) ? 'read' : null
    const x = e as unknown as Record<string, unknown>
    const file = typeof x.file_path === 'string' ? x.file_path : typeof x.notebook_path === 'string' ? x.notebook_path : null
    if (kind && file && !('deny' in ran && ran.deny !== undefined)) {
      await update($, touched, t => (t[file] === 'edit' ? t : { ...t, [file]: kind }))
      // open the folders leading to it, so it shows up
      const base = await read($, root)
      if (file.startsWith(`${base}/`)) {
        const parts = file.slice(base.length + 1).split('/').slice(0, -1)
        const dirs = parts.map((_, i) => `${base}/${parts.slice(0, i + 1).join('/')}`)
        await update($, open, o => Array.from(new Set([...o, ...dirs])))
      }
    }
    if (kind === 'edit' || e.tool === 'Bash') await update($, rev, r => r + 1)
    return ran
  }).catch(($, e, next) => next(e)) // an observer: never block the call

  on('ui.render', { component: 'Pane', requestId: PANE }, async ($, e) => {
    const { Box, Text, Button } = $.ui.resolve(e)
    const base = (await read($, root)) || (await $.session.cwd())
    await read($, rev) // redraw after edits and shell commands
    const marks = await read($, touched)
    const opened = new Set(await read($, open))
    const limit = Math.max(5, (e.viewport?.rows ?? 30) - 6)
    const out: Row[] = []
    await rows($, base, 0, opened, out, limit)

    const mark = (p: string, isDir: boolean) => markFor(marks, p, isDir)
    const edited = Object.values(marks).filter(v => v === 'edit').length

    return (
      <Box flexDirection="column">
        <Text bold wrap="truncate-start">{base}</Text>
        <Text dimColor>✎ edited {edited} · • read {Object.keys(marks).length - edited}</Text>
        {out.map(r =>
          r.isDir ? (
            <Button
              key={`d:${r.path}`}
              label={`${'  '.repeat(r.depth)}${opened.has(r.path) ? '▾' : '▸'} ${r.name}/ ${mark(r.path, true)}`}
              onPress={() =>
                update($, open, o => (o.includes(r.path) ? o.filter(p => p !== r.path && !p.startsWith(`${r.path}/`)) : [...o, r.path]))
              }
            />
          ) : (
            <Text
              key={`f:${r.path}`}
              wrap="truncate-end"
              color={marks[r.path] === 'edit' ? 'yellow' : marks[r.path] === 'read' ? 'cyan' : undefined}
              dimColor={!marks[r.path]}
            >
              {'  '.repeat(r.depth)}  {mark(r.path, false)} {r.name}
            </Text>
          ),
        )}
        {out.length >= limit && <Text dimColor>… more (collapse a folder or enlarge the pane)</Text>}
        <Button key="collapse" label="Collapse all" onPress={() => update($, open, () => [])} />
      </Box>
    )
  })
}
