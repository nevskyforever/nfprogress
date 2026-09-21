// @vitest-environment node
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it, vi } from 'vitest'

import {
  decryptObjectBytes,
  encryptObjectBytes,
  generateAccountMasterKey,
  generateRecoveryKey,
  unwrapAmkWithPassphrase,
  wrapAmkWithPassphrase,
  wrapAmkWithRecoveryKey,
} from './index'

const context = { userId: 'boundary-user', projectId: 'boundary-project', entityId: 'boundary-entity', entityType: 'document' }

describe('C12 secret-boundary regression guard', () => {
  it('does not invoke network, storage, or console APIs while performing crypto operations', async () => {
    const fetchSpy = vi.spyOn(globalThis, 'fetch')
    const logSpy = vi.spyOn(console, 'log'); const warnSpy = vi.spyOn(console, 'warn'); const errorSpy = vi.spyOn(console, 'error')
    const amk = await generateAccountMasterKey(); const recovery = await generateRecoveryKey(); const plaintext = new TextEncoder().encode('plaintext that must remain local')
    const envelope = await encryptObjectBytes(amk, context, plaintext); await decryptObjectBytes(amk, context, envelope)
    const password = await wrapAmkWithPassphrase(amk, 'master passphrase'); await unwrapAmkWithPassphrase('master passphrase', password)
    await wrapAmkWithRecoveryKey(amk, recovery)
    expect(fetchSpy).not.toHaveBeenCalled(); expect(logSpy).not.toHaveBeenCalled(); expect(warnSpy).not.toHaveBeenCalled(); expect(errorSpy).not.toHaveBeenCalled()
  })

  it('keeps source imports isolated and excludes browser transport/storage globals', () => {
    const cryptoDirectory = resolve(import.meta.dirname)
    const source = ['bytes.ts', 'constants.ts', 'encoding.ts', 'errors.ts', 'index.ts', 'kdf.ts', 'keys.ts', 'objectCrypto.ts', 'sodium.ts', 'types.ts', 'wrapping.ts']
      .map(file => readFileSync(resolve(cryptoDirectory, file), 'utf8').replace(/\/\*[\s\S]*?\*\/|\/\/.*$/gm, ''))
      .join('\n')
    expect(source).not.toMatch(/\b(fetch|XMLHttpRequest|WebSocket|localStorage|sessionStorage|indexedDB|document\.cookie|console\.)\b/)
    expect(source).not.toMatch(/\b(location|URLSearchParams)\b/)
  })

  it('never embeds supplied secrets or protected bytes in typed error messages', async () => {
    const amk = await generateAccountMasterKey(); const passphrase = 'passphrase-not-for-errors'; const recovery = await generateRecoveryKey()
    const record = await wrapAmkWithPassphrase(amk, passphrase); const envelope = await encryptObjectBytes(amk, context, new TextEncoder().encode('plaintext-not-for-errors'))
    const errors = await Promise.allSettled([
      unwrapAmkWithPassphrase('wrong-passphrase-not-for-errors', record),
      decryptObjectBytes(amk, context, { ...envelope, ciphertext: new Uint8Array(envelope.ciphertext.length) }),
      wrapAmkWithRecoveryKey(amk, recovery).then(wrapped => unwrapAmkWithPassphrase(passphrase, wrapped as never)),
    ])
    for (const result of errors) if (result.status === 'rejected') {
      const message = (result.reason as Error).message
      expect(message).not.toContain(passphrase); expect(message).not.toContain('wrong-passphrase-not-for-errors')
      expect(message).not.toContain('plaintext-not-for-errors'); expect(message).not.toContain(Array.from(amk).join(','))
    }
  })
})
