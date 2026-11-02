import { expect, test } from 'claude-code/testing'

import { check, latestDue, nextDraw } from './ready'

// Fri 2026-10-09 15:00 UTC
const NOW = Date.UTC(2026, 9, 9, 15)

test('latest due draw per schedule', async () => {
  expect(latestDue([2, 5], NOW)).toBe('2026-10-06') // Tue
  expect(latestDue([3, 6], NOW)).toBe('2026-10-07') // Wed
  expect(latestDue([1, 4], NOW)).toBe('2026-10-08') // Thu
})

test('a draw is not due until 04:00 UTC next day', async () => {
  const thuNight = Date.UTC(2026, 9, 9, 3) // Fri 03:00 UTC, Thu draw not yet due
  expect(latestDue([1, 4], thuNight)).toBe('2026-10-05')
})

test('flags only games behind', async () => {
  const d = (date: string) => ({ draws: [[date, [1], 1]] as [string, ...unknown[]][] })
  const r = check(
    { lotto_max: d('2026-10-06'), western_max: d('2026-10-02'), lotto_649: d('2026-10-07'), western_649: d('2026-10-07'), daily_grand: d('2026-10-08') },
    NOW,
  )
  expect(r.behind.map(l => l.game)).toEqual(['Western Max'])
  expect(nextDraw(NOW)).toBe('Lotto Max + Western Max Fri')
})
