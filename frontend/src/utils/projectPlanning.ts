/** @deprecated Import project calculations from the framework-independent core. */
import {
  automaticDailyGoal as coreDailyGoal,
  automaticDeadline as coreDeadline,
  automaticDeadlineAfterGoalChange as coreDeadlineAfterGoalChange,
  automaticEditedDeadline as coreEditedDeadline,
  convertUnits,
  todayIsoDate as coreTodayIsoDate,
  writingDayIsoDate as coreWritingDayIsoDate,
  planningDate as corePlanningDate,
} from '@/core/projects/calculations'
import type { ProgressUnit } from '@/core/projects/types'

export const convertProjectUnit = convertUnits
export function planningDate(value: string | undefined, fallback = new Date()): Date {
  return corePlanningDate(value, fallback)
}
export function automaticDailyGoal(goal: number, total: number, deadline: string, unit: ProgressUnit, today = new Date(), addedToday = 0): number | null {
  return coreDailyGoal(goal, total, deadline, unit, today, addedToday)
}
export function automaticDeadline(goal: number, total: number, dailyGoal: number, today = new Date()): string | null {
  return coreDeadline(goal, total, dailyGoal, today)
}
export function automaticEditedDeadline(options: Omit<Parameters<typeof coreEditedDeadline>[0], 'today'> & { today?: Date }): string | null {
  return coreEditedDeadline({ ...options, today: options.today ?? new Date() })
}
export function automaticDeadlineAfterGoalChange(options: Omit<Parameters<typeof coreDeadlineAfterGoalChange>[0], 'today'> & { today?: Date }): string | null {
  return coreDeadlineAfterGoalChange({ ...options, today: options.today ?? new Date() })
}
export function todayIsoDate(today = new Date()): string { return coreTodayIsoDate(today) }
export function writingDayIsoDate(startTime: unknown, now = new Date()): string { return coreWritingDayIsoDate(startTime, now) }
