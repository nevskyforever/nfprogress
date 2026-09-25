import { invoke } from '@tauri-apps/api/core'
import { encodeBase64Url } from '@/api/base64url'
import type { ObjectCryptoEnvelope } from '@/crypto'
import type { NoteResolutionSealingRepository, UnsealedNoteResolutionIntent } from '@/cloud/noteSyncResolutionSealing'

export class SQLiteNoteSyncResolutionRepository implements NoteResolutionSealingRepository {
  list(accountId: string, limit: number): Promise<UnsealedNoteResolutionIntent[]> {
    return invoke('list_unsealed_note_resolution_intents', { accountId, limit })
  }
  commit(input: { eventId: string, accountId: string, canonicalUserId: string, deviceId: string, projectId: string, entityId: string, canonicalPayload: string, envelope: ObjectCryptoEnvelope }): Promise<'sealed' | 'already_sealed'> {
    return invoke('commit_sealed_note_resolution_event', { command: {
      event_id: input.eventId, account_id: input.accountId, canonical_user_id: input.canonicalUserId,
      device_id: input.deviceId, project_id: input.projectId, entity_id: input.entityId,
      expected_canonical_payload: input.canonicalPayload,
      envelope: { crypto_version: input.envelope.crypto_version, aad_version: input.envelope.aad_version,
        nonce: encodeBase64Url(input.envelope.nonce), ciphertext: encodeBase64Url(input.envelope.ciphertext) },
    } })
  }
}
