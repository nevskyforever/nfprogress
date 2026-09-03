import type { ProgressUnit } from './types'

export const UNIT_FACTORS: Readonly<Record<ProgressUnit, number>> = {
  symbols: 1,
  A4: 1_800,
  author_list: 40_000,
  ficbook_pages: 4_500,
}

/** Equivalent to engine.unit_converter; invalid units are impossible by type. */
export function convertUnits(value: number, from: ProgressUnit, to: ProgressUnit = 'symbols'): number {
  if (!Number.isFinite(value)) return value
  const converted = value * UNIT_FACTORS[from] / UNIT_FACTORS[to]
  if (to === 'symbols') return converted
  if (to === 'author_list') return Math.round(converted * 10) / 10
  return Math.ceil(converted)
}
