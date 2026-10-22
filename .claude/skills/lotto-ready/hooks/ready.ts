import type { Lag, Readiness } from '../types'

// Draw weekdays (0 = Sunday). Draws run ~22:30 ET, so results count as due
// from 04:00 UTC the following day.
export const SCHEDULE: Record<string, { label: string; days: number[] }> = {
  lotto_max: { label: 'Lotto Max', days: [2, 5] },
  western_max: { label: 'Western Max', days: [2, 5] },
  lotto_649: { label: 'Lotto 6/49', days: [3, 6] },
  western_649: { label: 'Western 6/49', days: [3, 6] },
  daily_grand: { label: 'Daily Grand', days: [1, 4] },
}

const DAY = 86_400_000
const DUE_AFTER = 28 * 3_600_000 // draw date midnight UTC + 28h = 04:00 UTC next day
const WEEKDAY = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']

const iso = (ms: number) => new Date(ms).toISOString().slice(0, 10)
const midnight = (ms: number) => Math.floor(ms / DAY) * DAY

export function latestDue(days: number[], now: number): string {
  for (let d = midnight(now); ; d -= DAY) {
    if (days.includes(new Date(d).getUTCDay()) && d + DUE_AFTER <= now) return iso(d)
  }
}

export function nextDraw(now: number): string {
  for (let d = midnight(now); ; d += DAY) {
    if (d + DUE_AFTER <= now) continue
    const day = new Date(d).getUTCDay()
    const games = Object.values(SCHEDULE).filter(g => g.days.includes(day)).map(g => g.label)
    if (games.length) return `${games.join(' + ')} ${WEEKDAY[day]}`
  }
}

type Data = Record<string, { draws?: [string, ...unknown[]][] } | undefined>

export function check(data: Data, now: number): Readiness {
  const behind: Lag[] = []
  for (const [key, { label, days }] of Object.entries(SCHEDULE)) {
    const have = (data[key]?.draws ?? []).reduce((max, [date]) => (date > max ? date : max), '')
    const want = latestDue(days, now)
    if (have < want) behind.push({ game: label, have: have || 'none', want })
  }
  return { checkedAt: new Date(now).toISOString(), behind, next: nextDraw(now) }
}
