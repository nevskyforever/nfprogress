import type { ProgressUnit } from '@/core/projects/types'
import { convertUnits } from '@/core/projects/calculations'

/** Match ProjectService._round_for_unit for a non-negative submitted total. */
export function normalizeProgressTotal(value: number, unit: ProgressUnit): number {
  if (!Number.isFinite(value) || value < 0) {
    throw new RangeError('Progress total must be a finite non-negative number.')
  }
  // Legacy project values in author lists retain fractional precision. All
  // page-like units are rounded up before the authoritative service validates.
  return unit === 'author_list' ? value : Math.ceil(value)
}

export function progressDeltaSymbols(
  previousTotal: number,
  nextTotal: number,
  unit: ProgressUnit,
): number {
  return convertUnits(nextTotal, unit, 'symbols')
    - convertUnits(previousTotal, unit, 'symbols')
}

export function progressContributionPercent(
  deltaSymbols: number,
  goalSymbols: number | null,
): number {
  if (goalSymbols === null || !Number.isFinite(goalSymbols) || goalSymbols <= 0) return 0
  return deltaSymbols / goalSymbols * 100
}
