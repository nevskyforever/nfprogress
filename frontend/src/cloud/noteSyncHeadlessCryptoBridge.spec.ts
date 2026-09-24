// @vitest-environment node
import { readFileSync, writeFileSync } from 'node:fs'
import { describe, expect, it } from 'vitest'
import { asAccountMasterKey, generateAccountMasterKey } from '@/crypto'
import { decodeBase64Url, encodeBase64Url } from '@/api/base64url'
import { encryptedSyncObjectFromWire, encryptedSyncPushBodyBytes } from '@/api/encryptedSync'
import { encodeNoteSyncPlaintext, type NoteSyncRecord } from './noteSyncCodec'
import { openNoteSyncEvent, sealNoteSyncEvent } from './encryptedSyncProtocol'
import type { SyncEventEnvelope } from './syncProtocol'

interface SealRequest {
  action: 'seal'
  canonical_user_id: string
  device_id: string
  event: SyncEventEnvelope
  note: NoteSyncRecord
  amk?: number[]
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

type BridgeRequest = SealRequest | OpenRequest

async function execute(request: BridgeRequest): Promise<Record<string, unknown>> {
  if (request.action === 'seal') {
    const amk = request.amk === undefined
      ? await generateAccountMasterKey()
      : asAccountMasterKey(Uint8Array.from(request.amk))
    const sealed = await sealNoteSyncEvent(amk, request.canonical_user_id, request.event, null, request.note)
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
