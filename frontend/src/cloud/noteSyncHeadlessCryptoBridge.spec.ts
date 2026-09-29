// @vitest-environment node
import { readFileSync, writeFileSync } from 'node:fs'
import { describe, expect, it } from 'vitest'
import { asAccountMasterKey, decryptObjectBytes, encryptObjectBytes, generateAccountMasterKey } from '@/crypto'
import { decodeBase64Url, encodeBase64Url } from '@/api/base64url'
import { encryptedSyncObjectFromWire, encryptedSyncPushBodyBytes } from '@/api/encryptedSync'
import { encodeNoteSyncPlaintext, type NoteSyncRecord } from './noteSyncCodec'
import { normalizeC15SyncEvent, openNoteSyncEvent, sealNoteSyncEvent } from './encryptedSyncProtocol'
import type { SyncEventEnvelope } from './syncProtocol'
import { decodeNoteSyncResolutionV2, encodeNoteSyncResolutionV2, type NoteSyncResolutionV2 } from './noteSyncResolutionV2Codec'
import { resolutionEnvelopeWire } from './noteSyncResolutionSealing'
import { sealPendingNoteSyncIntents, type UnsealedNoteSyncIntent } from './noteSyncIntent'
import type { RuntimeKeyContext } from '@/auth/keyContext'

interface SealRequest {
  action: 'seal'
  canonical_user_id: string
  device_id: string
  event: SyncEventEnvelope
  note: NoteSyncRecord
  amk?: number[]
  parent_event_id?: string | null
}

interface OpenRequest {
  action: 'open'
  canonical_user_id: string
  amk: number[]
  item: {
    event: SyncEventEnvelope & { device_id: string; server_sequence: number }
    object: { crypto_version: number; aad_version: number; nonce: string; ciphertext: string }
  }
}

interface ResolutionEncodeRequest { action: 'resolution_encode'; payload: NoteSyncResolutionV2 }
interface ResolutionSealRequest {
  action: 'resolution_seal'; canonical_user_id: string; amk: number[]; canonical_payload: string
  event: SyncEventEnvelope; device_id: string
}
interface ResolutionOpenRequest { action: 'resolution_open'; canonical_user_id: string; amk: number[]; item: OpenRequest['item'] }
interface SealIntentRequest { action: 'seal_intent'; canonical_user_id: string; amk: number[]; intent: UnsealedNoteSyncIntent }

type BridgeRequest = SealRequest | OpenRequest | ResolutionEncodeRequest | ResolutionSealRequest | ResolutionOpenRequest | SealIntentRequest

async function execute(request: BridgeRequest): Promise<Record<string, unknown>> {
  if (request.action === 'seal_intent') {
    let object: ReturnType<typeof resolutionEnvelopeWire> | undefined
    const keyContext = {
      leaseForAccount: (accountId: string) => ({
        localAccountId: accountId, canonicalUserId: request.canonical_user_id,
        isCurrent: () => true,
        use: async <T>(operation: (key: ReturnType<typeof asAccountMasterKey>) => Promise<T>) =>
          operation(asAccountMasterKey(Uint8Array.from(request.amk))),
      }),
    } as RuntimeKeyContext
    const result = await sealPendingNoteSyncIntents({
      list: async () => [request.intent],
      recordSealFailure: async () => { throw new Error('Production Note intent sealing failed.') },
      commitSealedEvent: async input => { object = resolutionEnvelopeWire(input.envelope); return 'sealed' },
    }, keyContext)
    expect(result.results[0]?.status).toBe('sealed')
    expect(object).toBeDefined()
    return { object, event: normalizeC15SyncEvent({
      event_id: request.intent.event_id, project_id: request.intent.project_id,
      entity_id: request.intent.entity_id, entity_type: 'note', operation: request.intent.operation,
      revision: request.intent.revision, updated_at: request.intent.updated_at,
      deleted_at: request.intent.deleted_at,
    }) }
  }
  if (request.action === 'resolution_encode') {
    const bytes = encodeNoteSyncResolutionV2(request.payload)
    return { canonical_payload: encodeBase64Url(bytes), decoded: decodeNoteSyncResolutionV2(bytes) }
  }
  if (request.action === 'resolution_seal') {
    const bytes = decodeBase64Url(request.canonical_payload)
    const payload = decodeNoteSyncResolutionV2(bytes)
    expect(payload.header.event_id).toBe(request.event.event_id)
    expect(payload.header.revision).toBe(request.event.revision)
    const object = await encryptObjectBytes(asAccountMasterKey(Uint8Array.from(request.amk)), {
      userId: request.canonical_user_id, projectId: payload.header.project_id,
      entityId: payload.header.entity_id, entityType: 'note',
    }, bytes)
    return { object: resolutionEnvelopeWire(object) }
  }
  if (request.action === 'resolution_open') {
    const envelope = encryptedSyncObjectFromWire(request.item.object)
    const plaintext = await decryptObjectBytes(asAccountMasterKey(Uint8Array.from(request.amk)), {
      userId: request.canonical_user_id, projectId: request.item.event.project_id,
      entityId: request.item.event.entity_id, entityType: 'note',
    }, envelope)
    return { crypto_version: envelope.crypto_version, aad_version: envelope.aad_version,
      nonce: Array.from(envelope.nonce), ciphertext: Array.from(envelope.ciphertext),
      plaintext: Array.from(plaintext), decoded: decodeNoteSyncResolutionV2(plaintext) }
  }
  if (request.action === 'seal') {
    const amk = request.amk === undefined
      ? await generateAccountMasterKey()
      : asAccountMasterKey(Uint8Array.from(request.amk))
    const sealed = await sealNoteSyncEvent(
      amk, request.canonical_user_id, request.event, request.parent_event_id ?? null, request.note,
    )
    const push = {
      protocol_version: 1 as const,
      encrypted_sync_version: 1 as const,
      device_id: request.device_id,
      items: [sealed],
    }
    expect(encryptedSyncPushBodyBytes(push)).toBeGreaterThan(0)
    return {
      amk: Array.from(amk),
      push: {
        protocol_version: 1,
        encrypted_sync_version: 1,
        device_id: request.device_id,
        items: [{
          event: sealed.event,
          object: {
            crypto_version: sealed.object.crypto_version,
            aad_version: sealed.object.aad_version,
            nonce: encodeBase64Url(sealed.object.nonce),
            ciphertext: encodeBase64Url(sealed.object.ciphertext),
          },
        }],
      },
    }
  }

  const envelope = encryptedSyncObjectFromWire(request.item.object)
  const plaintext = await openNoteSyncEvent(
    asAccountMasterKey(Uint8Array.from(request.amk)),
    request.canonical_user_id,
    request.item.event,
    envelope,
  )
  return {
    crypto_version: envelope.crypto_version,
    aad_version: envelope.aad_version,
    nonce: Array.from(envelope.nonce),
    ciphertext: Array.from(envelope.ciphertext),
    plaintext: Array.from(encodeNoteSyncPlaintext(plaintext)),
    decoded: plaintext,
  }
}

function defaultRequest(): SealRequest {
  const timestamp = '2026-09-23T00:00:00.000000Z'
  return {
    action: 'seal',
    canonical_user_id: '123e4567-e89b-42d3-a456-426614174099',
    device_id: '123e4567-e89b-42d3-a456-426614174001',
    event: {
      event_id: '123e4567-e89b-42d3-a456-426614174010',
      project_id: 'project-1',
      entity_id: 'note-1',
      entity_type: 'note',
      operation: 'upsert',
      revision: 1,
      updated_at: timestamp,
      deleted_at: null,
    },
    note: {
      id: 'note-1', project_id: 'project-1', stage_id: null, source_type: 'project',
      source_map_id: null, source_node_id: null, content_format: 'html', title: 'headless title',
      content: '<p>headless private body</p>', checklist: [], color: 'default', pinned: false,
      archived: false, sort_order: 0, tags: [], created_at: timestamp, updated_at: timestamp, metadata: {},
    },
  }
}

describe('C15 test-only headless crypto bridge', () => {
  it('seals an ordinary causal update with the supplied parent', async () => {
    const request = defaultRequest()
    request.event.event_id = '123e4567-e89b-42d3-a456-426614174011'
    request.event.revision = 2
    request.parent_event_id = '123e4567-e89b-42d3-a456-426614174010'
    const sealed = await execute(request)
    const opened = await execute({
      action: 'open', canonical_user_id: request.canonical_user_id,
      amk: sealed.amk as number[], item: {
        event: { ...request.event, device_id: request.device_id, server_sequence: 1 },
        object: (sealed.push as { items: Array<{ object: OpenRequest['item']['object'] }> }).items[0]!.object,
      },
    })
    const decoded = opened.decoded as { mutation: string; header: { parent_event_id: string } }
    expect(decoded.mutation).toBe('update')
    expect(decoded.header.parent_event_id).toBe(request.parent_event_id)
  })

  it('uses production sealing/opening code and emits only an explicit temporary response', async () => {
    const requestPath = process.env.NFPROGRESS_C15_CRYPTO_BRIDGE_REQUEST
    const responsePath = process.env.NFPROGRESS_C15_CRYPTO_BRIDGE_RESPONSE
    if (requestPath === undefined && responsePath === undefined) {
      const sealed = await execute(defaultRequest())
      const push = sealed.push as { items: Array<{ object: { ciphertext: string } }> }
      expect(decodeBase64Url(push.items[0]!.object.ciphertext).byteLength).toBeGreaterThan(16)
      return
    }
    if (requestPath === undefined || responsePath === undefined) throw new Error('Incomplete crypto bridge environment.')
    const request = JSON.parse(readFileSync(requestPath, 'utf8')) as BridgeRequest
    const response = await execute(request)
    writeFileSync(responsePath, JSON.stringify(response), { encoding: 'utf8', mode: 0o600 })
    expect(response).toBeDefined()
  })
})
