import { describe, expect, it, vi } from 'vitest'
import { encryptedCoversApi } from './encryptedCovers'

describe('encrypted cover API', () => {
  it('uploads raw ciphertext and parses binary download metadata', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch')
    fetchMock.mockResolvedValueOnce(new Response(JSON.stringify({ blob_id: 'blob', project_id: 'project', kind: 'project_cover', size_bytes: 16, duplicate: false }), { status: 200, headers: { 'Content-Type': 'application/json' } }))
    await encryptedCoversApi.upload('token', 'project', 'blob', { crypto_version: 1, aad_version: 1, nonce: new Uint8Array(24), ciphertext: new Uint8Array(16) })
    const firstCall = fetchMock.mock.calls[0]
    expect(firstCall?.[1]?.body).toBeInstanceOf(ArrayBuffer)
    fetchMock.mockResolvedValueOnce(new Response(new Uint8Array(16), { status: 200, headers: { 'X-WORTA-Crypto-Version': '1', 'X-WORTA-AAD-Version': '1', 'X-WORTA-Nonce': 'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA' } }))
    await expect(encryptedCoversApi.download('token', 'project', 'blob')).resolves.toMatchObject({ ciphertext: new Uint8Array(16) })
    fetchMock.mockRestore()
  })

  it('rejects noncanonical nonce headers through the shared Base64URL boundary', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(new Response(new Uint8Array(16), {
      status: 200,
      headers: { 'X-WORTA-Crypto-Version': '1', 'X-WORTA-AAD-Version': '1', 'X-WORTA-Nonce': 'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=' },
    }))
    await expect(encryptedCoversApi.download('token', 'project', 'blob')).rejects.toThrow(TypeError)
    fetchMock.mockRestore()
  })
})
