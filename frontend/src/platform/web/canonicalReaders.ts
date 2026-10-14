import { decryptObjectBytes, type AccountMasterKey, type ObjectCryptoEnvelope } from '@/crypto'
import { decryptAccountObject, type AccountObjectEnvelope } from '@/crypto/accountObjectCrypto'
import { unframeProjectMetadata } from '@/cloud/projectMetadataCodec'
import { unframeStructuralEvent } from '@/cloud/stageCodec'
import { unframeCatalogEvent } from '@/cloud/accountCatalogCodec'
import { unframeContentNote } from '@/cloud/contentNoteCodec'
import { unframeMapEvent } from '@/cloud/mapCodec'
import { unframeDocumentEvent } from '@/cloud/documentCodec'
import { unframeProgressEvent } from '@/cloud/progressCodec'
import { unframeGameEvent } from '@/cloud/gameCodec'

const entries = [
  [1, 'project_metadata', [1,2], unframeProjectMetadata],
  [2, 'stage', [1,2], unframeStructuralEvent],
  [3, 'stage_order', [1,2], unframeStructuralEvent],
  [4, 'folder', [1], unframeCatalogEvent],
  [5, 'folder_order', [1], unframeCatalogEvent],
  [6, 'folder_membership', [1], unframeCatalogEvent],
  [7, 'project_order', [1], unframeCatalogEvent],
  [8, 'note', [1], unframeContentNote],
  [9, 'map', [1], unframeMapEvent],
  [10, 'document', [1], unframeDocumentEvent],
  [11, 'progress', [1], unframeProgressEvent],
  [12, 'project_game', [1], (f: Uint8Array) => unframeGameEvent(f, 'project')],
  [13, 'account_game', [1], (f: Uint8Array) => unframeGameEvent(f, 'account')],
] as const
export const BROWSER_CANONICAL_READERS = Object.freeze(entries.map(([id, family, versions]) => Object.freeze({ id, family, versions: Object.freeze([...versions]) })))
export interface BrowserCanonicalContext { accountId: string; projectId: string | null; entityId: string; entityType: string; eventId: string }
const fail = (): never => { throw new TypeError('browser_canonical_reader_rejected') }
/** Read-only canonical surface. The frame is never inspected or decompressed before AEAD succeeds. */
export async function openBrowserCanonicalObject(amk: AccountMasterKey, input: BrowserCanonicalContext, envelope: ObjectCryptoEnvelope | AccountObjectEnvelope): Promise<unknown> {
  const context = { ...input }, account = ['folder','folder_order','folder_membership','project_order','account_game'].includes(context.entityType)
  if (account !== (context.projectId === null) || envelope.ciphertext.length > 8 * 1024 * 1024 + 16) fail()
  const sealed = { ...envelope, nonce: envelope.nonce.slice(), ciphertext: envelope.ciphertext.slice() }
  let frame: Uint8Array | undefined
  try {
    frame = account
      ? await decryptAccountObject(amk, { userId: context.accountId, scope: 'account', entityId: context.entityId, entityType: context.entityType }, sealed as AccountObjectEnvelope)
      : await decryptObjectBytes(amk, { userId: context.accountId, projectId: context.projectId!, entityId: context.entityId, entityType: context.entityType }, sealed as ObjectCryptoEnvelope)
    if (frame.length < 20) fail()
    const entry = entries.find(([id]) => id === frame![9])
    if (!entry) return fail()
    if (entry[1] !== context.entityType || !(entry[2] as readonly number[]).includes(frame[10]!)) fail()
    const result = await entry[3](frame)
    // Owning decoder validates the schema. Bind authenticated data to the external event reference too.
    const note = entry[0] === 8 ? result as ReturnType<typeof unframeContentNote> : null
    const h = (note ? note.event.header : (result as { header: Record<string, unknown> }).header) as unknown as Record<string, unknown>
    if ((note ? note.account_id : h.account_id) !== context.accountId || h.entity_id !== context.entityId || h.event_id !== context.eventId
      || !account && h.project_id !== context.projectId || account && h.scope !== 'account') fail()
    return result
  } finally { frame?.fill(0); sealed.nonce.fill(0); sealed.ciphertext.fill(0) }
}
