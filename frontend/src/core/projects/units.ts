import type { ProgressUnit } from './types'

export const UNIT_FACTORS: Readonly<Record<ProgressUnit, number>> = {
  symbols: 1,
  A4: 1_800,
  author_list: 40_000,
  ficbook_pages: 4_500,
}

function compareFloatToRational(value: number, numerator: bigint, denominator: bigint): number {
  const bits = new DataView(new ArrayBuffer(8))
  bits.setFloat64(0, Math.abs(value), false)
  const raw = bits.getBigUint64(0, false)
  const exponent = Number((raw >> 52n) & 0x7ffn)
  const mantissa = raw & 0x000f_ffff_ffff_ffffn
  if (exponent === 0 && mantissa === 0n) return -1
  const significand = exponent === 0 ? mantissa : (1n << 52n) | mantissa
  const binaryExponent = exponent === 0 ? -1074 : exponent - 1023 - 52
  const floatNumerator = binaryExponent >= 0
    ? significand << BigInt(binaryExponent)
    : significand
  const floatDenominator = binaryExponent >= 0
    ? 1n
    : 1n << BigInt(-binaryExponent)
  const left = floatNumerator * denominator
  const right = numerator * floatDenominator
  return left < right ? -1 : left > right ? 1 : 0
}

/** Python round(value, digits) uses ties-to-even; Math.round does not. */
export function roundHalfEven(value: number, digits = 0): number {
  if (!Number.isFinite(value)) return value
  const factor = 10 ** digits
  const sign = value < 0 ? -1 : 1
  const scaled = Math.abs(value) * factor
  const lower = Math.floor(scaled)
  const fraction = scaled - lower
  let rounded: number
  if (fraction < 0.5 - Number.EPSILON * Math.max(1, scaled) * 4) {
    rounded = lower
  } else if (fraction > 0.5 + Number.EPSILON * Math.max(1, scaled) * 4) {
    rounded = lower + 1
  } else {
    const comparison = compareFloatToRational(
      Math.abs(value),
      BigInt(2 * lower + 1),
      BigInt(2 * factor),
    )
    rounded = comparison < 0 || (comparison === 0 && lower % 2 === 0)
      ? lower : lower + 1
  }
  return sign * rounded / factor
}

/** Equivalent to engine.unit_converter; invalid units are impossible by type. */
export function convertUnits(value: number, from: ProgressUnit, to: ProgressUnit = 'symbols'): number {
  if (!Object.hasOwn(UNIT_FACTORS, from) || !Object.hasOwn(UNIT_FACTORS, to)) {
    throw new RangeError('Unknown progress unit.')
  }
  if (!Number.isFinite(value)) return value
  const converted = value * UNIT_FACTORS[from] / UNIT_FACTORS[to]
  if (to === 'symbols') return converted
  if (to === 'author_list') return roundHalfEven(converted, 1)
  return Math.ceil(converted)
}
