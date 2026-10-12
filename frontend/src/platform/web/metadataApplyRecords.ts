import { timestamp } from '@/cloud/projectMetadataCodec'
import type { V3Descriptor } from '@/api/encryptedSyncV3'
import { BrowserPersistenceError } from './persistence'
import type { BrowserSyncScope } from './syncDurability'

/** Authority metadata only. The immutable encrypted inbox remains the payload ledger. */
export interface BrowserMetadataProof {
  record_version: 1; protocol_version: 2 | 3; metadata_codec_version: 1 | 2; owner_kind: 'project_metadata'; account_id: string; project_id: string
  bootstrap_id: string; event_id: string; source_device_id: string; server_sequence: number
  operation: 'create' | 'update' | 'delete' | 'genesis_resolution' | 'resolution'
  revision: number; generation: number; parent_event_ids: string[]; wire_digest: string; reference: V3Descriptor
}
export interface BrowserMetadataHead {
  record_version: 1; account_id: string; device_id: string; owner_kind: 'project_metadata'
  owner_id: string; bootstrap_id: string; tip_event_ids: string[]; history: BrowserMetadataProof[]
}
const uuid = (v: unknown): v is string => typeof v === 'string' && /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/.test(v)
const positive = (v: unknown): v is number => Number.isSafeInteger(v) && (v as number) > 0
const exact = (v: unknown, keys: string[]): v is Record<string, unknown> => !!v && typeof v === 'object' && !Array.isArray(v) && Object.keys(v).sort().join(',') === keys.sort().join(',')
function fail(): never { throw new BrowserPersistenceError('corrupt_record') }
const sortedIds = (v: unknown, max: number): v is string[] => Array.isArray(v) && v.length <= max && v.every((id, i) => uuid(id) && (!i || v[i - 1] < id))
export function validateBrowserMetadataProof(value: unknown, scope: BrowserSyncScope): BrowserMetadataProof {
  if (!exact(value, ['record_version','protocol_version','metadata_codec_version','owner_kind','account_id','project_id','bootstrap_id','event_id','source_device_id','server_sequence','operation','revision','generation','parent_event_ids','wire_digest','reference'])) fail()
  const p = value as unknown as BrowserMetadataProof, d = p.reference
  if (p.record_version !== 1 || ![2,3].includes(p.protocol_version) || ![1,2].includes(p.metadata_codec_version) || p.owner_kind !== 'project_metadata' || p.account_id !== scope.accountId
    || typeof p.project_id !== 'string' || !p.project_id.length || p.project_id.length > 512
    || !(typeof p.bootstrap_id === 'string' && /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/.test(p.bootstrap_id)) || !uuid(p.event_id) || !uuid(p.source_device_id) || !positive(p.server_sequence)
    || typeof p.wire_digest !== 'string' || !/^[0-9a-f]{64}$/.test(p.wire_digest)
    || !positive(p.revision) || !positive(p.generation) || !sortedIds(p.parent_event_ids, 64) || p.parent_event_ids.includes(p.event_id)
    || !['create','update','delete','genesis_resolution','resolution'].includes(p.operation)
    || !exact(d, ['event_id','device_id','server_sequence','project_id','entity_id','entity_type','operation','revision','updated_at','deleted_at'])
    || d.event_id !== p.event_id || d.device_id !== p.source_device_id || d.server_sequence !== p.server_sequence
    || d.project_id !== p.project_id || d.entity_id !== p.project_id || d.entity_type !== 'project_metadata'
    || d.revision !== p.revision || d.operation !== (p.operation === 'delete' ? 'delete' : 'upsert')
    || !timestamp(d.updated_at)
    || (p.operation === 'delete' ? d.deleted_at !== d.updated_at : d.deleted_at !== null)) fail()
  if (p.operation === 'create' && (p.revision !== 1 || p.generation !== 1 || p.parent_event_ids.length)) fail()
  if (['update','delete'].includes(p.operation) && p.parent_event_ids.length !== 1) fail()
  if (['resolution','genesis_resolution'].includes(p.operation) && (p.parent_event_ids.length < 2 || p.revision < 2)) fail()
  return structuredClone(p)
}
export function validateBrowserMetadataHead(value: unknown, scope: BrowserSyncScope): BrowserMetadataHead {
  if (!exact(value, ['record_version','account_id','device_id','owner_kind','owner_id','bootstrap_id','tip_event_ids','history'])) fail()
  const h = value as unknown as BrowserMetadataHead
  if (h.record_version !== 1 || h.account_id !== scope.accountId || h.device_id !== scope.deviceId || h.owner_kind !== 'project_metadata'
    || !(typeof h.bootstrap_id === 'string' && /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/.test(h.bootstrap_id)) || typeof h.owner_id !== 'string' || !h.owner_id.length || h.owner_id.length > 512
    || !sortedIds(h.tip_event_ids, 64) || !h.tip_event_ids.length || !Array.isArray(h.history) || !h.history.length || h.history.length > 200) fail()
  const history = h.history.map(p => validateBrowserMetadataProof(p, scope)), ids = history.map(p => p.event_id)
  if (ids.some((id, i) => i > 0 && ids[i - 1]! >= id) || history.some(p => p.project_id !== h.owner_id || p.bootstrap_id !== h.bootstrap_id)) fail()
  const tips = new Set(ids)
  for (const p of history) {
    const parents = p.parent_event_ids.map(id => history.find(prior => prior.event_id === id) ?? fail())
    if (parents.length && (p.revision !== Math.max(...parents.map(p => p.revision)) + 1 || p.generation <= Math.max(...parents.map(p => p.generation)))) fail()
    if (p.operation === 'genesis_resolution' && parents.some(p => p.operation !== 'create' || p.revision !== 1 || p.parent_event_ids.length)) fail()
    parents.forEach(p => tips.delete(p.event_id))
  }
  if (JSON.stringify([...tips].sort()) !== JSON.stringify(h.tip_event_ids)) fail()
  return { ...structuredClone(h), history }
}
