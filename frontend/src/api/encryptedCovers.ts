import { apiBinaryRequest, apiRequest } from './client'
import type { ObjectCryptoEnvelope } from '@/crypto'

const MAX_CIPHERTEXT_BYTES = 2 * 1024 * 1024 + 16

function authorization(accessToken: string): Headers { const headers = new Headers(); headers.set('Authorization', `Bearer ${accessToken}`); return headers }
function b64url(value: Uint8Array): string { let raw = ''; for (const byte of value) raw += String.fromCharCode(byte); return btoa(raw).replaceAll('+', '-').replaceAll('/', '_').replaceAll('=', '') }
function decodeB64url(value: string | null): Uint8Array {
  if (!value || !/^[A-Za-z0-9_-]+$/.test(value) || value.length % 4 === 1) throw new TypeError('Invalid encrypted cover response.')
  const raw = atob(value.replaceAll('-', '+').replaceAll('_', '/') + '='.repeat((4 - value.length % 4) % 4))
  return Uint8Array.from(raw, (char) => char.charCodeAt(0))
}
function path(projectId: string, blobId: string): string { return `/api/v1/cloud/projects/${encodeURIComponent(projectId)}/covers/${encodeURIComponent(blobId)}` }

export interface EncryptedCoverUploadResponse { blob_id: string; project_id: string; kind: 'project_cover'; size_bytes: number; duplicate: boolean }
export interface DownloadedEncryptedCover extends ObjectCryptoEnvelope {}

export const encryptedCoversApi = {
  upload(accessToken: string, projectId: string, blobId: string, envelope: ObjectCryptoEnvelope): Promise<EncryptedCoverUploadResponse> {
    if (envelope.ciphertext.byteLength > MAX_CIPHERTEXT_BYTES) throw new RangeError('Encrypted cover exceeds size limit.')
    const headers = authorization(accessToken)
    headers.set('Content-Type', 'application/octet-stream'); headers.set('X-WORTA-Crypto-Version', String(envelope.crypto_version)); headers.set('X-WORTA-AAD-Version', String(envelope.aad_version)); headers.set('X-WORTA-Nonce', b64url(envelope.nonce))
    return apiRequest(path(projectId, blobId), { method: 'PUT', headers, rawBody: new Uint8Array(envelope.ciphertext).buffer })
  },
  async download(accessToken: string, projectId: string, blobId: string): Promise<DownloadedEncryptedCover> {
    const response = await apiBinaryRequest(path(projectId, blobId), { headers: authorization(accessToken) })
    const crypto_version = Number(response.headers.get('X-WORTA-Crypto-Version')); const aad_version = Number(response.headers.get('X-WORTA-AAD-Version')); const nonce = decodeB64url(response.headers.get('X-WORTA-Nonce'))
    if (crypto_version !== 1 || aad_version !== 1 || nonce.byteLength !== 24 || response.bytes.byteLength < 16 || response.bytes.byteLength > MAX_CIPHERTEXT_BYTES) throw new TypeError('Invalid encrypted cover response.')
    return { crypto_version, aad_version, nonce, ciphertext: response.bytes }
  },
}
