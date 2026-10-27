import { encodeProjectMetadataEvent, validateProjectMetadataEvent, type ProjectMetadata, type ProjectMetadataEvent } from './projectMetadataCodec'

/** Shared read-only Metadata history reduction. It grants no apply/ACK authority. */
export interface MetadataImportSnapshot { bootstrapId: string; metadata: ProjectMetadata | null; head: string | null; tips: string[]; cursor?: number }
export function metadataImportSnapshot(events: ProjectMetadataEvent[], bootstrapId: string, projectId: string): MetadataImportSnapshot | null {
  if (!events.length) return null
  const history = new Map<string, ProjectMetadataEvent>()
  const tips = new Set<string>()
  for (const event of events) {
    validateProjectMetadataEvent(event)
    const h = event.header
    if (h.bootstrap_id !== bootstrapId || h.project_id !== projectId) throw new TypeError('metadata_import_lineage')
    const prior = history.get(h.event_id)
    if (prior) {
      if (new TextDecoder().decode(encodeProjectMetadataEvent(prior)) !== new TextDecoder().decode(encodeProjectMetadataEvent(event))) throw new TypeError('metadata_import_replay')
      continue
    }
    const parents = h.parent_event_ids.map(id => history.get(id))
    if (parents.some(parent => !parent) || parents.some(parent => parent!.header.account_id !== h.account_id)) throw new TypeError('metadata_import_dependency')
    if (parents.length && (h.revision !== Math.max(...parents.map(parent => parent!.header.revision)) + 1 || h.generation <= Math.max(...parents.map(parent => parent!.header.generation)))) throw new TypeError('metadata_import_revision')
    if (['resolution', 'genesis_resolution'].includes(h.operation)) {
      // A subset resolution is historical conflict evidence; uncovered tips remain.
      if (h.operation === 'genesis_resolution' && parents.some(parent => parent!.header.operation !== 'create')) throw new TypeError('metadata_import_resolution')
    }
    for (const parent of h.parent_event_ids) tips.delete(parent)
    tips.add(h.event_id); history.set(h.event_id, event)
  }
  const ids = [...tips].sort()
  const head = ids.length === 1 ? ids[0]! : null
  const metadata = head ? history.get(head)!.metadata : null
  if (head && !metadata) throw new TypeError('metadata_import_deleted')
  return { bootstrapId, metadata, head, tips: ids }
}
