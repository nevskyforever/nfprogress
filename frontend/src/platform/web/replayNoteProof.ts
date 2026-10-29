import type { AccountMasterKey } from '@/crypto'
import type { BrowserSyncScope } from './syncDurability'
import type { LocalSourceSnapshot } from './localAuthority'
import { openHistoryCandidate } from './noteHistory'
import { noteProofDigest, verifyStoredNoteProof } from './legacyNoteApply'
import { BrowserReplayError, replaySame } from './replayRecords'
import type { ReplaySnapshot } from './replayInventory'
import type { BrowserNoteCandidate } from './noteHistoryRecords'
import type { NativeLocalProject } from './localAuthorityRecords'
import { authenticateReplaySourceSeed } from './replaySourceSeed'

/** Reauthenticate real Legacy outcomes and the owner's encrypted source after restart. */
export async function reauthenticateReplayNotes(scope: BrowserSyncScope, snapshot: ReplaySnapshot, amk: AccountMasterKey,
  current: () => boolean, readSource: (projectId: string) => Promise<{ source: LocalSourceSnapshot; project: NativeLocalProject }>): Promise<ReadonlySet<number>> {
  const sequences = new Set<number>()
  const rows = snapshot.rows.filter(row => row.state === 'note_proven')
  for (const seed of snapshot.manifest?.source_seeds ?? []) {
    if (!current()) throw new BrowserReplayError('session_closed')
    const opened = await readSource(seed.project_id)
    const evidence = await authenticateReplaySourceSeed(scope, snapshot, seed.project_id, amk, current)
    if (!replaySame(seed, evidence.reference) || !replaySame(opened.project, evidence.project)
      || !replaySame(opened.source.project, snapshot.sources?.find(row => row.project_id === seed.project_id))
      || !replaySame(opened.source.notes, snapshot.notes?.filter(row => row.project_id === seed.project_id))) throw new BrowserReplayError('note_source_reauthentication_failed')
  }
  for (const row of rows) {
    if (!current()) throw new BrowserReplayError('session_closed')
    const proof = row.note_proof
    const seed = snapshot.manifest?.source_seeds?.find(value => value.project_id === proof.header.project_id)
    const initial = row.server_sequence <= (seed?.initial_max_server_sequence ?? 0)
    if (!seed || proof.outcome !== 'applied' || (initial ? proof.mutation !== 'create' || proof.header.revision !== 1
      : proof.mutation !== 'update' || proof.header.revision < 2)) throw new BrowserReplayError('note_proof_reauthentication_failed')
    await verifyStoredNoteProof(scope, amk, row)
    const candidate = snapshot.noteHistory?.find((record): record is BrowserNoteCandidate => record.record_kind === 'candidate' && record.event_id === row.event_id)
    if (!candidate || candidate.record_version !== 1 || candidate.origin !== 'peer'
      || await noteProofDigest(candidate.projection) !== proof.local_note_digest) throw new BrowserReplayError('note_proof_reauthentication_failed')
    await openHistoryCandidate(scope, candidate, amk)
    sequences.add(row.server_sequence)
  }
  if (!current()) throw new BrowserReplayError('session_closed')
  return sequences
}
