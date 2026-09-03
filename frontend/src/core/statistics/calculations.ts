import { convertUnits } from '@/core/projects/calculations'
import type { PureStatistics, StatisticsInput } from './types'

const MS_PER_DAY = 86_400_000

function parseIsoDate(value: string): Date | null {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(value)) return null
  const [year, month, day] = value.split('-').map(Number)
  const result = new Date(year!, month! - 1, day!)
  return result.getFullYear() === year && result.getMonth() === month! - 1
    && result.getDate() === day ? result : null
}

function datePart(value: string): string | null {
  const match = /^(\d{4}-\d{2}-\d{2})/.exec(value)
  return match && parseIsoDate(match[1]!) ? match[1]! : null
}

/** Python's round uses ties-to-even; Math.round does not. */
function roundHalfEven(value: number, digits = 0): number {
  if (!Number.isFinite(value)) return value
  const factor = 10 ** digits
  const scaled = value * factor
  const lower = Math.floor(scaled)
  const fraction = scaled - lower
  const rounded = fraction < 0.5 || (fraction === 0.5 && lower % 2 === 0)
    ? lower : lower + 1
  return rounded / factor
}

function daysInclusive(start: string | null, end: string): number {
  const startDate = start ? parseIsoDate(start) : null
  const endDate = parseIsoDate(end)
  if (!startDate || !endDate) return 0
  return Math.floor((endDate.getTime() - startDate.getTime()) / MS_PER_DAY) + 1
}

export function calculatePureStatistics(input: StatisticsInput): PureStatistics {
  const symbolsByDay = new Map<string, number>()
  for (const entry of input.progressEntries) {
    const date = datePart(entry.createdAt)
    if (!date || !Number.isFinite(entry.addedSymbols)) continue
    symbolsByDay.set(date, (symbolsByDay.get(date) ?? 0) + entry.addedSymbols)
  }

  const days = [...symbolsByDay.keys()].sort()
  const entriesCount = input.progressEntries.length
  const activeDays = days.length
  const total = input.total
  const bestDayDate = days.reduce<string | null>((best, day) => (
    best === null || symbolsByDay.get(day)! > symbolsByDay.get(best)! ? day : best
  ), null)
  const symbolsByWeekday = new Map<number, number>()
  for (const day of days) {
    const weekday = parseIsoDate(day)!.getDay() === 0 ? 6 : parseIsoDate(day)!.getDay() - 1
    symbolsByWeekday.set(weekday, (symbolsByWeekday.get(weekday) ?? 0) + symbolsByDay.get(day)!)
  }
  let bestWeekday: number | null = null
  for (const [weekday, value] of symbolsByWeekday) {
    if (bestWeekday === null || value > symbolsByWeekday.get(bestWeekday)!) bestWeekday = weekday
  }
  const daysSinceStart = daysInclusive(datePart(input.createdAt ?? ''), input.planningDate)
  const timeline = days.map((date) => ({
    date,
    symbols: symbolsByDay.get(date)!,
    value: convertUnits(symbolsByDay.get(date)!, 'symbols', input.unit),
  }))

  return {
    entity_id: input.entityId,
    unit: input.unit,
    metrics: {
      entries_count: entriesCount,
      total,
      average_symbols_per_active_day: activeDays
        ? roundHalfEven(convertUnits(total, input.unit, 'symbols') / activeDays) : 0,
      average_symbols_per_entry: entriesCount
        ? roundHalfEven(input.progressEntries.reduce((sum, entry) => sum + entry.addedSymbols, 0) / entriesCount) : 0,
      average_entries_per_active_day: activeDays ? roundHalfEven(entriesCount / activeDays, 1) : 0,
      best_day: bestDayDate === null ? null : {
        date: bestDayDate,
        symbols: symbolsByDay.get(bestDayDate)!,
        value: convertUnits(symbolsByDay.get(bestDayDate)!, 'symbols', input.unit),
      },
      best_weekday: bestWeekday === null ? null : {
        weekday: bestWeekday,
        symbols: symbolsByWeekday.get(bestWeekday)!,
      },
      days_since_start: daysSinceStart,
      active_days: activeDays,
      active_days_percent: daysSinceStart > 0 ? roundHalfEven(activeDays / daysSinceStart * 100, 1) : 0,
    },
    timeline,
  }
}

export { roundHalfEven }
