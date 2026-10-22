import { atom, read, update } from 'claude-code'
import type { EngineInterface, Register, Timer } from 'claude-code'

import type { Step, Turn } from '../types'
import { summarize } from './summary'

const PANE = 'savvy-progress'
const turn = atom({ plugin: 'savvy-progress', key: 'turn' } as const, null)
const history = atom({ plugin: 'savvy-progress', key: 'history' } as const, [])
const now = atom({ plugin: 'savvy-progress', key: 'now' } as const, 0)

const secs = (ms: number) => (ms < 60_000 ? `${Math.round(ms / 1000)}s` : `${Math.floor(ms / 60_000)}m${Math.round((ms % 60_000) / 1000)}s`)

function line(t: Turn, at: number): string {
  const running = t.steps.find(s => s.state === 'run')
  const errs = t.steps.filter(s => s.state === 'err').length
  const parts = [`${secs((t.endedAt ?? at) - t.startedAt)}`, `${t.steps.length} tools`]
  if (errs) parts.push(`${errs} failed`)
  if (running) parts.push(running.tool)
  return parts.join(' · ')
}

function setStep($: EngineInterface, id: string, patch: Partial<Step>) {
  return update($, turn, t => (t ? { ...t, steps: t.steps.map(s => (s.id === id ? { ...s, ...patch } : s)) } : t))
}

export const register: Register = on => {
  let tick: Timer | null = null

  on('session.start', async ($, e, next) => {
    await $.command.register({ name: 'progress', description: 'Open the Savvy Progress pane' })
    return next(e)
  })

  on('command.run', { command: 'progress' }, async $ => {
    await $.ui.open({ id: PANE, title: 'Savvy Progress' })
    return { text: 'Savvy Progress opened.' }
  })

  on('turn.start', async ($, e, next) => {
    const at = await $.clock.now()
    await update($, turn, () => ({ prompt: e.text.replace(/\s+/g, ' ').slice(0, 80), startedAt: at, endedAt: null, steps: [] }))
    await update($, now, () => at)
    tick?.cancel()
    tick = $.clock.every(1000, () => {
      void $.clock.now().then(t => update($, now, () => t))
    })
    $.ui.status('⏳ working…')
    return next(e)
  })

  on('tool.call', async ($, e, next) => {
    const at = await $.clock.now()
    const step: Step = { id: e.tool_use_id, tool: e.tool, what: summarize(e.tool, e), state: 'run', ms: 0 }
    const t = await update($, turn, cur => (cur ? { ...cur, steps: [...cur.steps, step].slice(-200) } : cur))
    if (t) $.ui.status(`⏳ ${line(t, at)}`)
    const ran = await next(e)
    const failed = 'deny' in ran && ran.deny !== undefined ? true : ran.isError === true
    await setStep($, step.id, { state: failed ? 'err' : 'ok', ms: (await $.clock.now()) - at })
    return ran
  }).catch(($, e, next) => next(e)) // an observer: never block the call

  on('turn.complete', async ($, e, next) => {
    tick?.cancel()
    tick = null
    const at = await $.clock.now()
    const done = await update($, turn, t => (t ? { ...t, endedAt: at } : t))
    if (done) {
      await update($, history, h => [done, ...h].slice(0, 8))
      $.ui.status(`✓ ${line(done, at)}`)
    }
    return next(e)
  })

  on('ui.render', { component: 'Pane', requestId: PANE }, async ($, e) => {
    const { Box, Text } = $.ui.resolve(e)
    const t = await read($, turn)
    const at = (await read($, now)) || (await $.clock.now())
    const past = await read($, history)
    const room = Math.max(3, (e.viewport?.rows ?? 24) - 10)
    const width = Math.max(20, (e.props.bodyColumns ?? 60) - 4)

    if (!t) return <Text dimColor>Waiting for the first turn…</Text>

    const done = t.steps.filter(s => s.state !== 'run').length
    const pct = t.endedAt ? 1 : t.steps.length ? done / t.steps.length : 0
    const barW = Math.min(30, width - 10)
    const fill = Math.round(pct * barW)

    return (
      <Box flexDirection="column">
        <Text bold>{t.endedAt ? '✓ Done' : '⏳ Working'} · {line(t, at)}</Text>
        <Text dimColor wrap="truncate-end">“{t.prompt}”</Text>
        <Text color={t.endedAt ? 'green' : 'yellow'}>
          {'█'.repeat(fill)}{'░'.repeat(barW - fill)} {done}/{t.steps.length}
        </Text>
        <Text> </Text>
        {t.steps.slice(-room).map(s => (
          <Text key={s.id} wrap="truncate-end" color={s.state === 'err' ? 'red' : undefined} dimColor={s.state === 'ok'}>
            {s.state === 'run' ? '▶' : s.state === 'ok' ? '✓' : '✗'} {s.tool.padEnd(8)} {s.what}
            {s.state !== 'run' ? `  ${secs(s.ms)}` : ''}
          </Text>
        ))}
        {past.length > 1 && <Text> </Text>}
        {past.length > 1 && <Text bold>Recent turns</Text>}
        {past.slice(1, 5).map((p, i) => (
          <Text key={`h${i}`} dimColor wrap="truncate-end">
            {line(p, p.endedAt ?? at)} — {p.prompt}
          </Text>
        ))}
      </Box>
    )
  })
}
