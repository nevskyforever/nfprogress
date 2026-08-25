import type { UnitCode } from '@/types/api'

function localDate(value: string): Date | null {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(value)) return null
  const [year, month, day] = value.split('-').map(Number)
  const result = new Date(year!, month! - 1, day!)
  return Number.isNaN(result.getTime()) ? null : result
}

function toIsoDate(value: Date): string {
  const year = value.getFullYear()
  const month = String(value.getMonth() + 1).padStart(2, '0')
  const day = String(value.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

function rounded(value: number, unit: UnitCode): number {
  if (unit === 'author_list') return Math.round(value * 10) / 10
  return Math.ceil(value)
}

export function automaticDailyGoal(
  goal: number,
  total: number,
  deadline: string,
  unit: UnitCode,
  today = new Date(),
): number | null {
  const due = localDate(deadline)
  if (!due || !Number.isFinite(goal) || !Number.isFinite(total)) return null
  const remaining = Math.max(0, goal - total)
  if (remaining === 0) return 0
  const start = new Date(today.getFullYear(), today.getMonth(), today.getDate())
  const days = Math.floor((due.getTime() - start.getTime()) / 86_400_000) + 1
  return rounded(remaining / Math.max(1, days), unit)
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
  const due = new Date(today.getFullYear(), today.getMonth(), today.getDate() + days - 1)
  return toIsoDate(due)
}
