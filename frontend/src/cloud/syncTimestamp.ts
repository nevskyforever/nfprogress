const TIMESTAMP = /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})(?:\.(\d{1,6}))?(Z|[+-]\d{2}:\d{2})$/
const MICROS_PER_SECOND = 1_000_000n
const SECONDS_PER_DAY = 86_400n

export interface SyncTimestamp {
  readonly epochMicroseconds: bigint
}

function invalidTimestamp(): never {
  throw new TypeError('Invalid sync timestamp.')
}

function isLeapYear(year: number): boolean {
  return year % 4 === 0 && (year % 100 !== 0 || year % 400 === 0)
}

function daysInMonth(year: number, month: number): number {
  if (month === 2) return isLeapYear(year) ? 29 : 28
  return [4, 6, 9, 11].includes(month) ? 30 : 31
}

// Proleptic Gregorian civil date to days relative to 1970-01-01.
function daysFromCivil(year: number, month: number, day: number): bigint {
  let adjustedYear = BigInt(year)
  if (month <= 2) adjustedYear -= 1n
  const era = adjustedYear >= 0n ? adjustedYear / 400n : (adjustedYear - 399n) / 400n
  const yearOfEra = adjustedYear - era * 400n
  const shiftedMonth = BigInt(month + (month > 2 ? -3 : 9))
  const dayOfYear = (153n * shiftedMonth + 2n) / 5n + BigInt(day - 1)
  const dayOfEra = yearOfEra * 365n + yearOfEra / 4n - yearOfEra / 100n + dayOfYear
  return era * 146097n + dayOfEra - 719468n
}

function civilFromDays(daysSinceEpoch: bigint): [number, number, number] {
  const shifted = daysSinceEpoch + 719468n
  const era = shifted >= 0n ? shifted / 146097n : (shifted - 146096n) / 146097n
  const dayOfEra = shifted - era * 146097n
  const yearOfEra = (dayOfEra - dayOfEra / 1460n + dayOfEra / 36524n - dayOfEra / 146096n) / 365n
  let year = yearOfEra + era * 400n
  const dayOfYear = dayOfEra - (365n * yearOfEra + yearOfEra / 4n - yearOfEra / 100n)
  const monthPrime = (5n * dayOfYear + 2n) / 153n
  const day = dayOfYear - (153n * monthPrime + 2n) / 5n + 1n
  const month = monthPrime + (monthPrime < 10n ? 3n : -9n)
  if (month <= 2n) year += 1n
  return [Number(year), Number(month), Number(day)]
}

function floorDiv(value: bigint, divisor: bigint): bigint {
  const quotient = value / divisor
  return value < 0n && value % divisor !== 0n ? quotient - 1n : quotient
}

export function parseSyncTimestamp(value: string): SyncTimestamp {
  if (typeof value !== 'string') invalidTimestamp()
  const match = TIMESTAMP.exec(value)
  if (match === null) invalidTimestamp()
  const year = Number(match[1])
  const month = Number(match[2])
  const day = Number(match[3])
  const hour = Number(match[4])
  const minute = Number(match[5])
  const second = Number(match[6])
  const fraction = match[7] ?? ''
  const zone = match[8]!
  if (year < 1 || month < 1 || month > 12 || day < 1 || day > daysInMonth(year, month)
    || hour > 23 || minute > 59 || second > 59 || zone === '-00:00') invalidTimestamp()

  let offsetSeconds = 0
  if (zone !== 'Z') {
    const offsetHour = Number(zone.slice(1, 3))
    const offsetMinute = Number(zone.slice(4, 6))
    if (offsetHour > 23 || offsetMinute > 59) invalidTimestamp()
    offsetSeconds = (offsetHour * 60 + offsetMinute) * 60 * (zone[0] === '+' ? 1 : -1)
  }
  const localSeconds = daysFromCivil(year, month, day) * SECONDS_PER_DAY
    + BigInt(hour * 3600 + minute * 60 + second)
  const microseconds = BigInt(fraction.padEnd(6, '0'))
  return { epochMicroseconds: (localSeconds - BigInt(offsetSeconds)) * MICROS_PER_SECOND + microseconds }
}

export function formatSyncTimestamp(timestamp: SyncTimestamp): string {
  if (typeof timestamp !== 'object' || timestamp === null || typeof timestamp.epochMicroseconds !== 'bigint') invalidTimestamp()
  const wholeSeconds = floorDiv(timestamp.epochMicroseconds, MICROS_PER_SECOND)
  const microseconds = timestamp.epochMicroseconds - wholeSeconds * MICROS_PER_SECOND
  const days = floorDiv(wholeSeconds, SECONDS_PER_DAY)
  const secondsOfDay = wholeSeconds - days * SECONDS_PER_DAY
  const [year, month, day] = civilFromDays(days)
  if (year < 1 || year > 9999) invalidTimestamp()
  const hour = secondsOfDay / 3600n
  const minute = (secondsOfDay % 3600n) / 60n
  const second = secondsOfDay % 60n
  const pad = (part: number | bigint, width = 2) => String(part).padStart(width, '0')
  return `${pad(year, 4)}-${pad(month)}-${pad(day)}T${pad(hour)}:${pad(minute)}:${pad(second)}.${pad(microseconds, 6)}Z`
}

export function canonicalizeSyncTimestamp(value: string): string {
  return formatSyncTimestamp(parseSyncTimestamp(value))
}

export function syncTimestampsEqual(left: string, right: string): boolean {
  return parseSyncTimestamp(left).epochMicroseconds === parseSyncTimestamp(right).epochMicroseconds
}
