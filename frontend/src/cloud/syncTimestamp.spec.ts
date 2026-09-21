import { describe, expect, it } from 'vitest'
import { canonicalizeSyncTimestamp, parseSyncTimestamp, syncTimestampsEqual } from './syncTimestamp'

describe('C15 exact timestamps', () => {
  it('normalizes offsets and fractional precision to UTC microseconds', () => {
    expect(canonicalizeSyncTimestamp('2026-09-21T03:30:00+03:30')).toBe('2026-09-21T00:00:00.000000Z')
    expect(canonicalizeSyncTimestamp('2026-09-20T19:00:00-05:00')).toBe('2026-09-21T00:00:00.000000Z')
    expect(canonicalizeSyncTimestamp('2026-09-21T00:00:00.1Z')).toBe('2026-09-21T00:00:00.100000Z')
    expect(canonicalizeSyncTimestamp('1969-12-31T23:59:59.999999Z')).toBe('1969-12-31T23:59:59.999999Z')
    expect(syncTimestampsEqual('2026-09-21T00:00:00Z', '2026-09-21T03:00:00.000000+03:00')).toBe(true)
    expect(parseSyncTimestamp('1970-01-01T00:00:00.000001Z').epochMicroseconds).toBe(1n)
  })

  it.each([
    '2026-02-29T00:00:00Z', '2024-13-01T00:00:00Z', '2024-04-31T00:00:00Z',
    '2024-01-01T24:00:00Z', '2024-01-01T00:60:00Z', '2024-01-01T00:00:60Z',
    '2024-01-01T00:00:00.1234567Z', '2024-01-01T00:00:00z', '2024-01-01T00:00:00',
    '2024-01-01T00:00:00-00:00', '2024-01-01T00:00:00+24:00', '0000-01-01T00:00:00Z',
  ])('rejects invalid timestamp %s', value => {
    expect(() => parseSyncTimestamp(value)).toThrow(TypeError)
  })

  it('validates Gregorian leap years', () => {
    expect(canonicalizeSyncTimestamp('2000-02-29T00:00:00Z')).toBe('2000-02-29T00:00:00.000000Z')
    expect(() => parseSyncTimestamp('1900-02-29T00:00:00Z')).toThrow(TypeError)
  })
})
