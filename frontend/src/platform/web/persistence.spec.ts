import { afterEach, describe, expect, it, vi } from 'vitest'
import { BrowserPersistenceError, openBrowserPersistence, persistenceError } from './persistence'

afterEach(() => vi.unstubAllGlobals())
describe('browser persistence failure boundary', () => {
  it('keeps only typed codes and never retains arbitrary storage messages', () => {
    const mappings = { QuotaExceededError: 'quota_exceeded', VersionError: 'unsupported_version', SecurityError: 'unavailable', NotAllowedError: 'unavailable', NotSupportedError: 'unavailable', AbortError: 'storage_failed' }
    for (const [name, code] of Object.entries(mappings)) {
      const error = persistenceError(new DOMException('SECRET_CONTENT_TOKEN', name))
      expect(error).toBeInstanceOf(BrowserPersistenceError)
      expect(error.code).toBe(code)
      expect(JSON.stringify(error) + error.message).not.toContain('SECRET_CONTENT_TOKEN')
    }
    expect(persistenceError(new Error('SECRET')).code).toBe('storage_failed')
    const existing = new BrowserPersistenceError('writer_busy')
    expect(persistenceError(existing)).toBe(existing)
  })
  it('rejects noncanonical user scope before opening storage', async () => {
    await expect(openBrowserPersistence('User')).rejects.toMatchObject({ code: 'account_mismatch' })
    await expect(openBrowserPersistence('ABCDEFAB-1111-1111-1111-111111111111')).rejects.toMatchObject({ code: 'account_mismatch' })
  })
  it('rejects unavailable or insecure storage without a fallback', async () => {
    vi.stubGlobal('isSecureContext', false)
    await expect(openBrowserPersistence('11111111-1111-1111-1111-111111111111')).rejects.toMatchObject({ code: 'unavailable' })
    vi.stubGlobal('isSecureContext', true)
    vi.stubGlobal('indexedDB', undefined)
    await expect(openBrowserPersistence('11111111-1111-1111-1111-111111111111')).rejects.toMatchObject({ code: 'unavailable' })
  })
})
