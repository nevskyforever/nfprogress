import type { UnitCode } from '@/types/api'

const UNIT_FACTORS: Record<UnitCode, number> = {
  symbols: 1,
  A4: 1_800,
  author_list: 40_000,
  ficbook_pages: 4_500,
}

function localDate(value: string): Date | null {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(value)) return null
  const [year, month, day] = value.split('-').map(Number)
  const result = new Date(year!, month! - 1, day!)
  return Number.isNaN(result.getTime()) ? null : result
}

export function planningDate(value: string | undefined, fallback = new Date()): Date {
  return value ? localDate(value) ?? fallback : fallback
}

function startOfDay(value = new Date()): Date {
  return new Date(value.getFullYear(), value.getMonth(), value.getDate())
}

function toIsoDate(value: Date): string {
  const year = value.getFullYear()
  const month = String(value.getMonth() + 1).padStart(2, '0')
  const day = String(value.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

function roundedPlanValue(value: number, unit: UnitCode): number {
  if (unit === 'author_list') return Math.round(value * 10) / 10
  return Math.ceil(value)
}

export function convertProjectUnit(value: number, from: UnitCode, to: UnitCode): number {
  if (!Number.isFinite(value) || from === to) return value
  const converted = value * UNIT_FACTORS[from] / UNIT_FACTORS[to]
  if (to === 'symbols') return converted
  if (to === 'author_list') return Math.round(converted * 10) / 10
  return Math.ceil(converted)
}

export function automaticDailyGoal(
  goal: number,
  total: number,
  deadline: string,
  unit: UnitCode,
  today = new Date(),
  addedToday = 0,
): number | null {
  const due = localDate(deadline)
  if (!due || !Number.isFinite(goal) || !Number.isFinite(total)) return null
  // Legacy edit planning uses the amount at the beginning of today so text
  // already written today is not counted a second time after a plan change.
  const baseTotal = Math.max(0, total - Math.max(0, addedToday))
  const remaining = Math.max(0, goal - baseTotal)
  if (remaining === 0) return 0
  const days = Math.floor((due.getTime() - startOfDay(today).getTime()) / 86_400_000) + 1
  return roundedPlanValue(remaining / Math.max(1, days), unit)
}

export function automaticDeadline(
  goal: number,
  total: number,
  dailyGoal: number,
  today = new Date(),
): string | null {
  if (
    !Number.isFinite(goal) || !Number.isFinite(total) || !Number.isFinite(dailyGoal)
    || dailyGoal <= 0 || goal <= total
  ) return null
  const days = Math.ceil((goal - total) / dailyGoal)
  const due = new Date(startOfDay(today))
  due.setDate(due.getDate() + days - 1)
  return toIsoDate(due)
}

export function automaticEditedDeadline(options: {
  goal: number
  total: number
  dailyGoal: number
  todayGoal: number | null
  previousDailyGoal: number | null
  recalculate: boolean
  today?: Date
}): string | null {
  const { goal, total, dailyGoal, todayGoal, previousDailyGoal, recalculate } = options
  if (recalculate || todayGoal === null || previousDailyGoal === null) {
    return automaticDeadline(goal, total, dailyGoal, options.today)
  }
  if (dailyGoal <= 0 || !Number.isFinite(goal)) return null
  const newTodayGoal = todayGoal - previousDailyGoal + dailyGoal
  const daysAfterToday = Math.ceil(Math.max(0, goal - newTodayGoal) / dailyGoal)
  const due = startOfDay(options.today)
  due.setDate(due.getDate() + daysAfterToday)
  return toIsoDate(due)
}

export function automaticDeadlineAfterGoalChange(options: {
  goal: number
  todayGoal: number | null
  total: number
  dailyGoal: number
  recalculate: boolean
  today?: Date
}): string | null {
  if (options.recalculate || options.todayGoal === null) {
    return automaticDeadline(options.goal, options.total, options.dailyGoal, options.today)
  }
  if (options.dailyGoal <= 0 || !Number.isFinite(options.goal)) return null
  const daysAfterToday = Math.ceil(
    Math.max(0, options.goal - options.todayGoal) / options.dailyGoal,
  )
  const due = startOfDay(options.today)
  due.setDate(due.getDate() + daysAfterToday)
  return toIsoDate(due)
}

export function todayIsoDate(today = new Date()): string {
  return toIsoDate(startOfDay(today))
}

export function writingDayIsoDate(startTime: unknown, now = new Date()): string {
  const match = typeof startTime === 'string'
    ? /^(\d{2}):(\d{2})/.exec(startTime)
    : null
  const hour = match ? Number(match[1]) : 0
  const minute = match ? Number(match[2]) : 0
  const writingDay = startOfDay(now)
  if (
    Number.isInteger(hour) && Number.isInteger(minute)
    && hour >= 0 && hour <= 23 && minute >= 0 && minute <= 59
    && now.getHours() * 60 + now.getMinutes() < hour * 60 + minute
  ) writingDay.setDate(writingDay.getDate() - 1)
  return toIsoDate(writingDay)
}
