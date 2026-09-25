// @vitest-environment node
import { describe, expect, it, vi } from 'vitest'
import fixture from './__fixtures__/noteSyncPlaintextV2Resolution.json'
import { decryptObjectBytes, encryptObjectBytes, generateAccountMasterKey } from '@/crypto'
import { decodeNoteSyncResolutionV2 } from './noteSyncResolutionV2Codec'
import { encodeBase64Url } from '@/api/base64url'
import { sealPendingNoteResolutions } from './noteSyncResolutionSealing'
import type { RuntimeKeyContext } from '@/auth/keyContext'

describe('resolution v2 durable sealing primitive', () => {
  it('round-trips the frozen canonical fixture under the original Note AAD context', async () => {
    const item = fixture.examples[0]!
    const bytes = new TextEncoder().encode(item.canonical_json)
    const resolution = decodeNoteSyncResolutionV2(bytes)
    const amk = await generateAccountMasterKey()
    const context = { userId: '123e4567-e89b-42d3-a456-426614174001', projectId: resolution.header.project_id, entityId: resolution.header.entity_id, entityType: 'note' }
    const envelope = await encryptObjectBytes(amk, context, bytes)
    expect(envelope.crypto_version).toBe(1)
    expect(envelope.aad_version).toBe(1)
    expect(envelope.nonce).toHaveLength(24)
    expect(await decryptObjectBytes(amk, context, envelope)).toEqual(bytes)
  })

  it('does not encrypt or commit with an already stale account/key lease', async () => {
    const item = fixture.examples[0]!
    const commit = vi.fn()
    const use = vi.fn()
    const keys = { leaseForAccount: () => ({ localAccountId: 'account', canonicalUserId: '123e4567-e89b-42d3-a456-426614174001', isCurrent: () => false, use }) } as unknown as RuntimeKeyContext
    await sealPendingNoteResolutions({ list: async () => [{ event_id: item.plaintext.header.event_id, account_id: 'account', device_id: '123e4567-e89b-42d3-a456-426614174002', project_id: item.plaintext.header.project_id, entity_id: item.plaintext.header.entity_id, canonical_payload: encodeBase64Url(new TextEncoder().encode(item.canonical_json)) }], commit }, keys, 'account')
    expect(use).not.toHaveBeenCalled()
    expect(commit).not.toHaveBeenCalled()
  })

  it('does not commit when the lease becomes stale after encryption', async () => {
    const item = fixture.examples[0]!
    const amk = await generateAccountMasterKey()
    const commit = vi.fn()
    let checks = 0
    const lease = { localAccountId: 'account', canonicalUserId: '123e4567-e89b-42d3-a456-426614174001', isCurrent: () => ++checks === 1, use: async <T>(callback: (key: typeof amk) => Promise<T>) => callback(amk) }
    const keys = { leaseForAccount: () => lease } as unknown as RuntimeKeyContext
    await sealPendingNoteResolutions({ list: async () => [{ event_id: item.plaintext.header.event_id, account_id: 'account', device_id: '123e4567-e89b-42d3-a456-426614174002', project_id: item.plaintext.header.project_id, entity_id: item.plaintext.header.entity_id, canonical_payload: encodeBase64Url(new TextEncoder().encode(item.canonical_json)) }], commit }, keys, 'account')
    expect(commit).not.toHaveBeenCalled()
  })
})
