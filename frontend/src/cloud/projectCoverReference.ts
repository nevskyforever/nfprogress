import { deriveObjectKey, type AccountMasterKey, type ObjectCryptoEnvelope } from '@/crypto'
import { encodeBase64Url } from '@/api/base64url'
import { decryptProjectCover, MAX_PROJECT_COVER_PLAINTEXT_BYTES, type ProjectCoverIdentity } from './projectCoverCrypto'

/** Only this reference is portable; JPEG and transfer/cache state remain local. */
export interface ProjectCoverReference {
  version: 1; blob_id: string; crypto_version: 1; aad_version: 1
  mime_type: 'image/jpeg'; plaintext_size: number; key_fingerprint: string; envelope_sha256: string
}
const keys = ['aad_version','blob_id','crypto_version','envelope_sha256','key_fingerprint','mime_type','plaintext_size','version']
const uuid = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/
const digest = /^[0-9a-f]{64}$/
export class InvalidCoverReferenceError extends TypeError {
  constructor(readonly reference: unknown) { super('cover_blob_invalid') }
}
export function validateCoverReference(value: unknown): asserts value is ProjectCoverReference {
  if (typeof value !== 'object' || value === null || Array.isArray(value)) throw new InvalidCoverReferenceError(value)
  const r = value as Record<string, unknown>
  if (Object.keys(r).sort().join(',') !== keys.join(',') || r.version !== 1 || r.crypto_version !== 1 || r.aad_version !== 1
    || typeof r.blob_id !== 'string' || !uuid.test(r.blob_id) || r.mime_type !== 'image/jpeg'
    || !Number.isSafeInteger(r.plaintext_size) || (r.plaintext_size as number) < 4 || (r.plaintext_size as number) > MAX_PROJECT_COVER_PLAINTEXT_BYTES
    || typeof r.key_fingerprint !== 'string' || !digest.test(r.key_fingerprint)
    || typeof r.envelope_sha256 !== 'string' || !digest.test(r.envelope_sha256)) throw new InvalidCoverReferenceError(value)
}
export async function sha256(bytes: Uint8Array): Promise<string> {
  return Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256', new Uint8Array(bytes).buffer)), b => b.toString(16).padStart(2,'0')).join('')
}
export function canonicalCoverEnvelope(e: ObjectCryptoEnvelope): Uint8Array {
  if (e.crypto_version !== 1 || e.aad_version !== 1 || e.nonce.length !== 24 || e.ciphertext.length < 16
    || e.ciphertext.length > MAX_PROJECT_COVER_PLAINTEXT_BYTES + 16) throw new TypeError('cover_blob_invalid')
  return new TextEncoder().encode(JSON.stringify({ aad_version: e.aad_version, ciphertext: encodeBase64Url(e.ciphertext), crypto_version: e.crypto_version, nonce: encodeBase64Url(e.nonce) }))
}
async function fingerprint(amk: AccountMasterKey, identity: ProjectCoverIdentity): Promise<string> {
  const key = await deriveObjectKey(amk, { ...identity, entityId: identity.blobId, entityType: 'project_cover' })
  try { return await sha256(key) } finally { key.fill(0) }
}
export function validatePreparedJpeg(bytes: Uint8Array): void {
  const invalid = (): never => { throw new TypeError('cover_source_invalid') }
  if (bytes.length < 4 || bytes.length > MAX_PROJECT_COVER_PLAINTEXT_BYTES
    || bytes[0] !== 255 || bytes[1] !== 216) invalid()
  let at = 2, scan = false, frame = false, scanSeen = false
  while (at < bytes.length) {
    if (scan && bytes[at] !== 255) { at++; continue }
    if (bytes[at++] !== 255) invalid()
    while (bytes[at] === 255) at++
    const marker = bytes[at++] ?? invalid()
    if (scan && (marker === 0 || (marker >= 0xd0 && marker <= 0xd7))) continue
    if (marker === 0xd9) {
      if (!frame || !scanSeen || at !== bytes.length) invalid()
      return
    }
    if (marker === 0xd8 || marker === 0 || (marker >= 0xd0 && marker <= 0xd7)) invalid()
    if (marker === 1) continue // JPEG TEM is a standalone marker.
    scan = false
    if (at + 2 > bytes.length) invalid()
    const length = bytes[at]! * 256 + bytes[at + 1]!
    if (length < 2 || at + length > bytes.length) invalid()
    if (marker >= 0xc0 && marker <= 0xcf && ![0xc4, 0xc8, 0xcc].includes(marker)) {
      if (length < 8 || !(bytes[at + 3]! * 256 + bytes[at + 4]!)
        || !(bytes[at + 5]! * 256 + bytes[at + 6]!)) invalid()
      frame = true
    }
    if (marker === 0xda) {
      if (!frame || length < 6) invalid()
      scan = true; scanSeen = true
    }
    at += length
  }
  invalid()
}
export async function createCoverReference(amk: AccountMasterKey, identity: ProjectCoverIdentity, bytes: Uint8Array, envelope: ObjectCryptoEnvelope): Promise<ProjectCoverReference> {
  validatePreparedJpeg(bytes)
  const ref: ProjectCoverReference = { version: 1, blob_id: identity.blobId, crypto_version: 1, aad_version: 1, mime_type: 'image/jpeg', plaintext_size: bytes.length,
    key_fingerprint: await fingerprint(amk, identity), envelope_sha256: await sha256(canonicalCoverEnvelope(envelope)) }
  validateCoverReference(ref)
  return ref
}
export async function authenticateCoverReference(amk: AccountMasterKey, identity: ProjectCoverIdentity, ref: ProjectCoverReference, envelope: ObjectCryptoEnvelope): Promise<Uint8Array> {
  validateCoverReference(ref)
  if (identity.blobId !== ref.blob_id || await sha256(canonicalCoverEnvelope(envelope)) !== ref.envelope_sha256
    || await fingerprint(amk, identity) !== ref.key_fingerprint) throw new TypeError('cover_blob_invalid')
  const bytes = await decryptProjectCover(amk, identity, envelope)
  try { validatePreparedJpeg(bytes); if (bytes.length !== ref.plaintext_size) throw new TypeError('cover_blob_invalid'); return bytes }
  catch (error) { bytes.fill(0); throw error }
}
