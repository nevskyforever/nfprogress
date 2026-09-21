import { describe, expect, it } from 'vitest'
import { decodeBase64Url, encodeBase64Url } from './base64url'

describe('canonical Base64URL boundary', () => {
  it('roundtrips canonical unpadded values', () => {
    const bytes = Uint8Array.of(0xfb, 0xff, 0, 1)
    expect(encodeBase64Url(bytes)).toBe('-_8AAQ')
    expect(decodeBase64Url('-_8AAQ')).toEqual(bytes)
    expect(encodeBase64Url(new Uint8Array())).toBe('')
    expect(decodeBase64Url('')).toEqual(new Uint8Array())
  })

  it.each(['Zg==', 'Zg=', 'Zg+', 'Zg/', 'Zg\n', 'Z', 'Zh'])('rejects noncanonical value %j', value => {
    expect(() => decodeBase64Url(value)).toThrow(TypeError)
  })

  it('enforces decoded lengths', () => {
    expect(() => decodeBase64Url('AA', { expectedLength: 2 })).toThrow(TypeError)
    expect(() => decodeBase64Url('AA', { minimumLength: 2 })).toThrow(TypeError)
    expect(() => decodeBase64Url('AAA', { maximumLength: 1 })).toThrow(TypeError)
  })
})
