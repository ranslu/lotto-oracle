import { atom, read, update } from 'claude-code'
import type { EngineInterface, Register, Timer } from 'claude-code'

import type { Scene } from '../types'
import { summarize } from './summary'

const PANE = 'replay-theater'
const scenes = atom({ plugin: 'replay-theater', key: 'scenes' } as const, [])
const pos = atom({ plugin: 'replay-theater', key: 'pos' } as const, 0)
const playing = atom({ plugin: 'replay-theater', key: 'playing' } as const, false)
const turnNo = atom({ plugin: 'replay-theater', key: 'turn' } as const, 0)

let reel: Timer | null = null

function clamp(n: number, len: number) {
  return Math.max(0, Math.min(len - 1, n))
}

async function go($: EngineInterface, to: (cur: number, len: number) => number) {
  const len = (await read($, scenes)).length
  if (!len) return
  await update($, pos, cur => clamp(to(cur, len), len))
}

async function stop($: EngineInterface) {
  reel?.cancel()
  reel = null
  await update($, playing, () => false)
}

async function play($: EngineInterface) {
  await stop($)
  await update($, playing, () => true)
  reel = $.clock.every(1500, () => {
    void (async () => {
      const len = (await read($, scenes)).length
      const at = await read($, pos)
      if (at >= len - 1) return stop($)
      await update($, pos, p => clamp(p + 1, len))
    })()
  })
}

function outputOf(ran: unknown): string {
  const r = (ran ?? {}) as Record<string, unknown>
  if (typeof r.deny === 'string') return `denied: ${r.deny}`
  if (typeof r.text === 'string') return r.text
  try {
    return JSON.stringify(r.result ?? '')
  } catch {
    return ''
  }
}

export const register: Register = on => {
  on('session.start', async ($, e, next) => {
    await $.command.register({ name: 'replay', description: 'Open Replay Theater (/replay last, /replay <n>)' })
    return next(e)
  })

  on('command.run', { command: 'replay' }, async ($, e) => {
    const arg = e.args.trim()
    const len = (await read($, scenes)).length
    if (arg === 'last') await update($, pos, () => Math.max(0, len - 1))
    else if (/^\d+$/.test(arg)) await update($, pos, () => clamp(Number(arg) - 1, Math.max(1, len)))
    else await update($, pos, () => 0)
    await $.ui.open({ id: PANE, title: 'Replay Theater' })
    return { text: len ? `Replay Theater: ${len} scenes.` : 'Replay Theater: nothing recorded yet.' }
  })

  on('turn.start', async ($, e, next) => {
    await update($, turnNo, n => n + 1)
    return next(e)
  })

  on('tool.call', async ($, e, next) => {
    const at = await $.clock.now()
    const ran = await next(e)
    const out = outputOf(ran).replace(/\r/g, '')
    const scene: Scene = {
      id: e.tool_use_id,
      tool: e.tool,
      what: summarize(e.tool, e),
      out: out.length > 1200 ? `${out.slice(0, 1200)}…` : out,
      isError: ('deny' in ran && ran.deny !== undefined) || ran.isError === true,
      at,
      ms: (await $.clock.now()) - at,
      turn: await read($, turnNo),
    }
    await update($, scenes, s => [...s, scene].slice(-300))
    return ran
  }).catch(($, e, next) => next(e)) // an observer: never block the call

  on('ui.render', { component: 'Pane', requestId: PANE }, async ($, e) => {
    const { Box, Text, Button } = $.ui.resolve(e)
    const list = await read($, scenes)
    if (!list.length) return <Text dimColor>No scenes yet — every tool call this session becomes one.</Text>

    const i = clamp(await read($, pos), list.length)
    const s = list[i]!
    const isPlaying = await read($, playing)
    const first = list[0]!.at
    const t = Math.round((s.at - first) / 1000)
    const lines = s.out.split('\n')
    const room = Math.max(3, (e.viewport?.rows ?? 30) - 12)
    const width = Math.max(10, (e.props.bodyColumns ?? 60) - 2)
    const barW = Math.min(40, width)
    const head = Math.round((i / Math.max(1, list.length - 1)) * (barW - 1))

    return (
      <Box flexDirection="column">
        <Text bold>
          🎬 Scene {i + 1}/{list.length} · turn {s.turn} · +{t}s
        </Text>
        <Text dimColor>{'─'.repeat(head)}●{'─'.repeat(barW - 1 - head)}</Text>
        <Text> </Text>
        <Text color={s.isError ? 'red' : 'cyan'} bold>
          {s.isError ? '✗' : '✓'} {s.tool} <Text dimColor>({s.ms} ms)</Text>
        </Text>
        <Text wrap="wrap">{s.what}</Text>
        <Text> </Text>
        {lines.slice(0, room).map((l, n) => (
          <Text key={`o${n}`} dimColor wrap="truncate-end">
            {l || ' '}
          </Text>
        ))}
        {lines.length > room && <Text dimColor>… {lines.length - room} more lines</Text>}
        <Text> </Text>
        <Box>
          <Button key="first" label="⏮" onPress={() => go($, () => 0)} />
          <Button key="prev" label="◀ Prev" onPress={() => go($, c => c - 1)} />
          <Button key="play" label={isPlaying ? '⏸ Pause' : '▶ Play'} onPress={() => (isPlaying ? stop($) : play($))} />
          <Button key="next" label="Next ▶" onPress={() => go($, c => c + 1)} />
          <Button key="last" label="⏭" onPress={() => go($, (_, len) => len - 1)} />
        </Box>
      </Box>
    )
  })
}
