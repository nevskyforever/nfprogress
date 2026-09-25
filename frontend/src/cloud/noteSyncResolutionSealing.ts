import { decodeBase64Url, encodeBase64Url } from '@/api/base64url'
import type { RuntimeKeyContext } from '@/auth/keyContext'
import { encryptObjectBytes, type ObjectCryptoEnvelope } from '@/crypto'
import { decodeNoteSyncResolutionV2 } from './noteSyncResolutionV2Codec'

export interface UnsealedNoteResolutionIntent {
  event_id: string
  account_id: string
  device_id: string
  project_id: string
  entity_id: string
  canonical_payload: string
}

export interface NoteResolutionSealingRepository {
  list(accountId: string, limit: number): Promise<UnsealedNoteResolutionIntent[]>
  commit(input: { eventId: string, accountId: string, canonicalUserId: string, deviceId: string, projectId: string, entityId: string, canonicalPayload: string, envelope: ObjectCryptoEnvelope }): Promise<'sealed' | 'already_sealed'>
}

/** Encrypts only durable canonical bytes. It never reconstructs a resolution
 * and is deliberately not connected to the sync runtime or uploader. */
export async function sealPendingNoteResolutions(repository: NoteResolutionSealingRepository, keys: RuntimeKeyContext, accountId: string, limit = 8): Promise<void> {
  const intents = await repository.list(accountId, limit)
  for (const intent of intents) {
    const lease = keys.leaseForAccount(intent.account_id)
    if (lease === null || lease.localAccountId !== intent.account_id || !lease.isCurrent()) continue
    await lease.use(async amk => {
      const bytes = decodeBase64Url(intent.canonical_payload, { minimumLength: 1, maximumLength: 8_388_608 })
      const payload = decodeNoteSyncResolutionV2(bytes)
      if (payload.header.event_id !== intent.event_id || payload.header.project_id !== intent.project_id || payload.header.entity_id !== intent.entity_id) {
        throw new TypeError('Durable resolution identity mismatch.')
      }
      const envelope = await encryptObjectBytes(amk, {
        userId: lease.canonicalUserId, projectId: intent.project_id, entityId: intent.entity_id, entityType: 'note',
      }, bytes)
      if (!lease.isCurrent()) return
      await repository.commit({ eventId: intent.event_id, accountId: intent.account_id, canonicalUserId: lease.canonicalUserId,
        deviceId: intent.device_id, projectId: intent.project_id, entityId: intent.entity_id,
        canonicalPayload: intent.canonical_payload, envelope })
    })
  }
}

export function resolutionEnvelopeWire(envelope: ObjectCryptoEnvelope) {
  return { crypto_version: envelope.crypto_version, aad_version: envelope.aad_version, nonce: encodeBase64Url(envelope.nonce), ciphertext: encodeBase64Url(envelope.ciphertext) }
}
