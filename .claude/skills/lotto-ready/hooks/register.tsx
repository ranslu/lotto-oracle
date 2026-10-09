import { atom, read, update } from 'claude-code'
import type { EngineInterface, Register } from 'claude-code'

import type { Readiness } from '../types'
import { check } from './ready'

const DATA = 'lottery_data.json'
const EVERY = 30 * 60_000

const readiness = atom({ plugin: 'lotto-ready', key: 'readiness' } as const, null)
const isRefreshing = atom({ plugin: 'lotto-ready', key: 'isRefreshing' } as const, false)

async function runCheck($: EngineInterface, isQuiet = false): Promise<Readiness> {
  let result: Readiness
  try {
    result = check(JSON.parse(await $.fs.read(DATA)), await $.clock.now())
  } catch (err) {
    result = { checkedAt: '', behind: [], next: '', error: `can't read ${DATA}` }
  }
  const was = await read($, readiness)
  await update($, readiness, () => result)

  if (result.error) {
    $.ui.status(`🎰 lotto-ready: ${result.error}`)
  } else if (result.behind.length) {
    $.ui.status(`🎰 ⚠ ${result.behind.length} game(s) behind · /lotto-refresh`)
    const isNew = !was || was.behind.length !== result.behind.length
    if (isNew && !isQuiet) {
      $.ui.toast(`Lotto data behind: ${result.behind.map(l => l.game).join(', ')}`)
    }
  } else {
    $.ui.status(`🎰 Lotto ready ✓ · next: ${result.next}`)
  }
  return result
}

async function refresh($: EngineInterface): Promise<string> {
  if (await read($, isRefreshing)) return 'Refresh already running.'
  await update($, isRefreshing, () => true)
  $.ui.status('🎰 refreshing lottery data…')
  try {
    const ran = await $.process.run(['python3', 'fetch_lottery.py'], { timeoutMs: 180_000 })
    const after = await runCheck($, true)
    if (ran.exitCode !== 0) return `fetch_lottery.py failed (exit ${ran.exitCode}): ${ran.stderr.slice(-300)}`
    return after.behind.length
      ? `Fetched, still behind: ${after.behind.map(l => `${l.game} (have ${l.have}, want ${l.want})`).join('; ')}`
      : `Fetched. All games current ✓ Next: ${after.next}`
  } finally {
    await update($, isRefreshing, () => false)
  }
}

function describe(r: Readiness): string {
  if (r.error) return r.error
  if (!r.behind.length) return `All 5 games current ✓ Next draw: ${r.next}`
  return `Behind:\n${r.behind.map(l => `- ${l.game}: have ${l.have}, due ${l.want}`).join('\n')}\nRun /lotto-refresh.`
}

export const register: Register = on => {
  on('session.start', async ($, e, next) => {
    await $.command.register({ name: 'lotto-check', description: 'Check lottery data readiness now' })
    await $.command.register({ name: 'lotto-refresh', description: 'Run fetch_lottery.py and re-check' })
    void runCheck($)
    $.clock.every(EVERY, () => void runCheck($))
    return next(e)
  })

  on('command.run', { command: 'lotto-check' }, async $ => ({ text: describe(await runCheck($)) }))
  on('command.run', { command: 'lotto-refresh' }, async $ => ({ text: await refresh($) }))

  on('ui.render', { component: 'AbovePrompt' }, async ($, e, next) => {
    const r = await read($, readiness)
    if (e.props.hasSurvey || !r || !r.behind.length) return next(e)

    const { Box, Button, Text } = $.ui.resolve(e)
    const busy = await read($, isRefreshing)
    return (
      <Box>
        <Text color="yellow">
          🎰 New draws ready: {r.behind.map(l => l.game).join(', ')}{' '}
        </Text>
        <Button
          key="refresh"
          label={busy ? 'Refreshing…' : 'Refresh now'}
          onPress={() => void refresh($)}
        />
      </Box>
    )
  })
}
