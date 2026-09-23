import { describe, expect, it } from 'vitest'
import fixture from './__fixtures__/noteSyncPlaintextV1.json'
import { canonicalNoteSyncJson, decodeNoteSyncPlaintext, encodeNoteSyncPlaintext, noteSyncEligibility, validateNoteSyncPlaintext, type NoteSyncPlaintext } from './noteSyncCodec'

describe('C15 golden plaintext fixture', () => {
  it('matches TypeScript canonical bytes', () => {
    const plaintext = fixture.plaintext as NoteSyncPlaintext
    validateNoteSyncPlaintext(plaintext)
    expect(canonicalNoteSyncJson(plaintext)).toBe(fixture.canonical_json)
    expect(new TextDecoder().decode(encodeNoteSyncPlaintext(plaintext))).toBe(fixture.canonical_json)
    expect(decodeNoteSyncPlaintext(new TextEncoder().encode(fixture.canonical_json))).toEqual(plaintext)
    expect(noteSyncEligibility(plaintext)).toEqual({ eligible: true })
  })
  it('matches shared update canonical bytes', () => {
    const update = fixture.update.plaintext as NoteSyncPlaintext
    validateNoteSyncPlaintext(update)
    expect(update.mutation).toBe('update')
    expect(update.header.revision).toBe(2)
    expect(update.header.parent_event_id).toBe(fixture.plaintext.header.event_id)
    expect(canonicalNoteSyncJson(update)).toBe(fixture.update.canonical_json)
    expect(new TextDecoder().decode(encodeNoteSyncPlaintext(update))).toBe(fixture.update.canonical_json)
    expect(decodeNoteSyncPlaintext(new TextEncoder().encode(fixture.update.canonical_json))).toEqual(update)
  })
})
