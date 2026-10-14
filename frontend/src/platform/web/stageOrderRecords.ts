import type { BrowserStageProof } from './stageRecords';
import { validateStageProof } from './stageRecords';
import { BrowserPersistenceError } from './persistence';
import { immutableWireIdentity, type BrowserSyncScope } from './syncDurability';
export interface StageOrderDependency {
  stage_id: string;
  event_ids: string[];
}
export interface BrowserStageOrderProof extends Omit<BrowserStageProof, 'owner_kind' | 'stage_id'> {
  owner_kind: 'stage_order';
  entity_id: 'stage_order';
  stage_dependencies: StageOrderDependency[];
}
export interface BrowserStageOrderHead {
  record_version: 1;
  owner_kind: 'stage_order';
  owner_id: string;
  account_id: string;
  device_id: string;
  project_id: string;
  bootstrap_id: string;
  tip_event_ids: string[];
  history: BrowserStageOrderProof[];
}
function bad(): never {
  throw new BrowserPersistenceError('corrupt_record');
}
const same = (a: unknown, b: unknown) => immutableWireIdentity(a) === immutableWireIdentity(b);
export function validateStageOrderProof(value: unknown, scope: BrowserSyncScope): BrowserStageOrderProof {
  const p = value as BrowserStageOrderProof;
  if (!p || p.owner_kind !== 'stage_order' || p.entity_id !== 'stage_order' || !Array.isArray(p.stage_dependencies) || p.stage_dependencies.length > 4096)
    bad();
  const { owner_kind: _kind, entity_id: _id, stage_dependencies: dependencies, ...rest } = p;
  // Reuse strict nonsecret structural fields; the owning frozen codec validates the actual payload.
  validateStageProof({ ...rest, owner_kind: 'stage', stage_id: 'stage_order', reference: { ...rest.reference, entity_type: 'stage' } }, scope);
  if (p.reference.entity_type !== 'stage_order' || p.reference.entity_id !== 'stage_order')
    bad();
  for (const [i, d] of dependencies.entries())
    if (!d || Object.keys(d).sort().join(',') !== 'event_ids,stage_id' || typeof d.stage_id !== 'string' || !d.stage_id || new TextEncoder().encode(d.stage_id).length > 512 || /[\uD800-\uDFFF]/u.test(d.stage_id) || i > 0 && dependencies[i - 1]!.stage_id >= d.stage_id || !Array.isArray(d.event_ids) || d.event_ids.length < 1 || d.event_ids.length > 64 || d.event_ids.some((v, j) => typeof v !== 'string' || !/^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/.test(v) || j > 0 && d.event_ids[j - 1]! >= v))
      bad();
  return structuredClone(p);
}
export function validateStageOrderHead(value: unknown, scope: BrowserSyncScope): BrowserStageOrderHead {
  const h = value as BrowserStageOrderHead;
  if (!h || Object.keys(h).sort().join(',') !== 'account_id,bootstrap_id,device_id,history,owner_id,owner_kind,project_id,record_version,tip_event_ids' || h.record_version !== 1 || h.owner_kind !== 'stage_order' || h.account_id !== scope.accountId || h.device_id !== scope.deviceId || h.owner_id !== h.project_id || !Array.isArray(h.history) || h.history.length < 1 || h.history.length > 200 || !Array.isArray(h.tip_event_ids) || h.tip_event_ids.length !== 1)
    bad();
  const history = h.history.map(p => validateStageOrderProof(p, scope)), causal = [...history].sort((a, b) => a.revision - b.revision);
  if (history.some((p, i) => p.project_id !== h.project_id || p.bootstrap_id !== h.bootstrap_id || i > 0 && history[i - 1]!.event_id >= p.event_id) || causal.some((p, i) => p.revision !== i + 1 || p.generation !== i + 1 || i === 0 && p.operation !== 'create' || i > 0 && (!same(p.parent_event_ids, [causal[i - 1]!.event_id]) || p.server_sequence <= causal[i - 1]!.server_sequence)) || h.tip_event_ids[0] !== causal.at(-1)!.event_id)
    bad();
  return { ...structuredClone(h), history };
}
/** Native receiver reference_coverage: cached non-reference expansion count per Stage. */
export function proveStageReferenceCoverage(current: string[], refs: string[], history: ReadonlyArray<{
  event_id: string;
  operation: string;
  parent_event_ids: string[];
}>): boolean {
  const byEvent = new Map(history.map(h => [h.event_id, h])), cache = new Map<string, string[]>(), covered = new Set<string>();
  if (byEvent.size !== history.length || !current.length || !refs.length || new Set(refs).size !== refs.length)
    return false;
  for (const ref of refs)
    if (!byEvent.has(ref) || byEvent.get(ref)!.operation === 'delete')
      return false;
  for (const tip of current) {
    const stack = [tip], visited = new Set<string>();
    let matched = false;
    while (stack.length) {
      const id = stack.pop()!;
      if (visited.has(id))
        continue;
      visited.add(id);
      if (refs.includes(id)) {
        covered.add(id);
        matched = true;
        continue;
      }
      if (!cache.has(id)) {
        if (cache.size >= 256)
          throw new BrowserPersistenceError('stage_dependency_proof_limit');
        const p = byEvent.get(id);
        if (!p)
          return false;
        cache.set(id, p.parent_event_ids);
      }
      stack.push(...cache.get(id)!);
    }
    if (!matched)
      return false;
  }
  return covered.size === refs.length;
}
