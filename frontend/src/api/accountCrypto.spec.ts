import { describe, expect, it, vi } from 'vitest'

import { accountCryptoApi } from './accountCrypto'

const request = {
  password: {
    crypto_version: 1,
    wrapping_version: 1,
    kdf: { kdf_version: 1, algorithm: 'argon2id13', salt: 'AAAAAAAAAAAAAAAAAAAAAA', opslimit: 2, memlimit: 67_108_864 },
    nonce: 'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA',
    ciphertext: 'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA',
  },
  recovery: {
    crypto_version: 1,
    wrapping_version: 1,
    nonce: 'AQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEB',
    ciphertext: 'AQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEB',
  },
} as const

describe('account crypto transport', () => {
  it('posts only wrapper records under the authenticated account endpoint', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(new Response(JSON.stringify({
      provisioned: true, password: request.password, recovery: request.recovery,
    }), { status: 201 }))
    await expect(accountCryptoApi.provision('access-token', request)).resolves.toMatchObject({ provisioned: true })
    const [url, options] = fetchMock.mock.calls[0]!
    expect(url).toBe('/api/v1/account/crypto')
    expect(options?.method).toBe('POST')
    expect(new Headers(options?.headers).get('Authorization')).toBe('Bearer access-token')
    const body = String(options?.body)
    expect(body).toContain('"password"')
    expect(body).toContain('"recovery"')
    expect(body).not.toContain('master_key')
    expect(body).not.toContain('recovery_key')
    fetchMock.mockRestore()
  })
})
