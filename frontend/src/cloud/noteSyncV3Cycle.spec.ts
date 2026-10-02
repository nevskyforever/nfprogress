import { afterEach, describe, expect, it, vi } from 'vitest'
import { encryptedSyncV2Api } from '@/api/encryptedSyncV2'
import { NormalUserAuthRuntime } from '@/auth/userAuth'
import { NoteSyncV3Cycle } from './noteSyncV3Cycle'

const USER = '123e4567-e89b-42d3-a456-426614174099'
const DEVICE = '123e4567-e89b-42d3-a456-426614174003'
const PAGE = { committed_cursor: 1, new_events: 1, replayed_events: 0, has_more: false }

async function setup(structuralEnabled = false, accountEnabled = false, contentEnabled = false) {
  const auth = new NormalUserAuthRuntime({
    login: vi.fn().mockResolvedValue({ access_token: 'token', refresh_token: 'refresh', access_expires_in: 60 }),
    refresh: vi.fn(), logout: vi.fn(), me: vi.fn().mockResolvedValue({ id: USER, username: 'u',
      email: 'u@example.test', email_verified: true, role: 'user', status: 'active', created_at: 'now' }),
  })
  await auth.login('u', 'p')
  const context = auth.requireContext()
  let writerMode = 3
  const calls: string[] = []
  const capabilities = vi.spyOn(encryptedSyncV2Api, 'capabilities').mockImplementation(async () => ({
    supported_transport_version: 2, writer_transport_version: writerMode, cutover_epoch: 1,
  }) as never)
  const bindings = { ensureForCurrentUser: vi.fn(async () => ({ context })) }
  const identity = { read: vi.fn(async () => ({ local_account_id: 'local', device_id: DEVICE })) }
  const keys = { leaseForAccount: vi.fn(() => ({ canonicalUserId: USER, authEpoch: context.authEpoch,
    isCurrent: () => true })) }
  const device = { registerOnce: vi.fn(async () => { calls.push('register') }) }
  const intents = { list: vi.fn(async () => { calls.push('seal_notes'); return [] }),
    recordSealFailure: vi.fn(), commitSealedEvent: vi.fn() }
  const note = { uploadOnce: vi.fn(async () => { calls.push('upload_notes'); return { uploaded: 1 } }) }
  const resolution = { uploadOnce: vi.fn(async () => { calls.push('upload_resolutions'); return { uploaded: 1 } }) }
  const noteApply = { runMixedInboxOnce: vi.fn(async () => { calls.push('apply_notes'); return {
    blocked: [], errors: [], hasRemainingWork: false,
  } }) }
  const metadata = {
    sealOnce: vi.fn(async () => { calls.push('seal_metadata'); return 1 }),
    uploadOnce: vi.fn(async () => { calls.push('upload_metadata'); return 1 }),
    pullOnce: vi.fn(async () => { calls.push('pull'); return PAGE }),
    applyOnce: vi.fn(async () => { calls.push('apply_metadata'); return { applied: 1, conflicts: 0,
      orphans: 0, blocked: [], listed: 1 } }),
    ackOnce: vi.fn(async () => { calls.push('ack'); return { status: 'advanced', cursor: 1 } }),
  }
  const structural = {
    sealOnce: vi.fn(async () => { calls.push('seal_structure'); return 0 }),
    uploadOnce: vi.fn(async () => { calls.push('upload_structure'); return 0 }),
    applyOnce: vi.fn(async () => { calls.push('apply_structure'); return { applied: 0, conflicts: 0, orphans: 0, blocked: [], listed: 0 } }),
  }
  const account = { readOnce: vi.fn(async () => { calls.push('apply_account'); return { blocked: ['account_entity_codec_not_activated'], listed: 1, hasRemainingWork: false } }) }
  const content = { readOnce: vi.fn(async () => { calls.push('apply_content'); return { blocked: ['orphan'], listed: 1, hasRemainingWork: true } }) }
  const cycle = new NoteSyncV3Cycle(auth, bindings as never, identity as never, keys as never,
    device as never, intents as never, note as never, resolution as never, noteApply as never, metadata as never, structuralEnabled ? structural as never : undefined, accountEnabled ? account as never : undefined, contentEnabled ? content as never : undefined)
  return { account, structural, cycle, calls, capabilities, intents, note, resolution, metadata,
    mode: (value: number) => { writerMode = value } }
}

afterEach(() => vi.restoreAllMocks())

describe('mode-3 Note and metadata cycle', () => {
  it('runs the framed Note reader after dependencies and before common ACK without a content writer', async () => {
    const h=await setup(true,true,true),r=await h.cycle.runOnce('local',DEVICE)
    expect(h.calls.indexOf('apply_structure')).toBeLessThan(h.calls.indexOf('apply_content'))
    expect(h.calls.indexOf('apply_metadata')).toBeLessThan(h.calls.indexOf('apply_content'))
    expect(h.calls.indexOf('apply_content')).toBeLessThan(h.calls.indexOf('apply_account'))
    expect(h.calls.indexOf('apply_content')).toBeLessThan(h.calls.indexOf('ack'))
    expect(r.blocked).toContain('orphan');expect(r.hasRemainingWork).toBe(true)
    expect(r.stages.filter(s=>s.includes('content'))).toEqual(['apply_content_notes'])
  })
  it('runs one bounded mixed cycle and ACKs only after both appliers', async () => {
    const h = await setup()
    const result = await h.cycle.runOnce('local', DEVICE)
    expect(result.stages).toEqual(['preflight', 'register_device', 'seal_notes', 'seal_metadata',
      'upload_notes', 'upload_resolutions', 'upload_metadata', 'pull_v3', 'apply_notes', 'apply_metadata', 'ack_v3'])
    expect(h.calls).toEqual(['register', 'seal_notes', 'seal_metadata', 'upload_notes', 'upload_resolutions',
      'upload_metadata', 'pull', 'apply_notes', 'apply_metadata', 'ack'])
    expect(result).toMatchObject({ noteUploaded: 1, resolutionUploaded: 1, metadataUploaded: 1,
      errors: [], blocked: [], hasRemainingWork: false })
  })

  it('pulls self echo after a lost metadata upload response', async () => {
    const h = await setup()
    h.metadata.uploadOnce.mockRejectedValueOnce(new Error('lost_response'))
    const result = await h.cycle.runOnce('local', DEVICE)
    expect(result.errors).toEqual([{ stage: 'upload_metadata', code: 'Error' }])
    expect(h.metadata.pullOnce).toHaveBeenCalledOnce()
    expect(h.metadata.applyOnce).toHaveBeenCalledOnce()
    expect(h.metadata.ackOnce).toHaveBeenCalledOnce()
    expect(result.hasRemainingWork).toBe(true)
  })

  it('stops on mode loss and never publishes with a stale writer authority', async () => {
    const h = await setup()
    h.intents.list.mockImplementationOnce(async () => { h.mode(2); return [] })
    const result = await h.cycle.runOnce('local', DEVICE)
    expect(result.errors[0]?.stage).toBe('seal_metadata')
    expect(h.note.uploadOnce).not.toHaveBeenCalled()
    expect(h.resolution.uploadOnce).not.toHaveBeenCalled()
    expect(h.metadata.uploadOnce).not.toHaveBeenCalled()
  })
})

it('mode-3 production dispatch applies structural arrivals before contiguous ACK and pulls after a lost structural upload', async () => {
  const h = await setup(true)
  h.structural.uploadOnce.mockRejectedValueOnce(new Error('lost response'))
  const result = await h.cycle.runOnce('local', DEVICE)
  expect(h.calls.indexOf('apply_structure')).toBeGreaterThan(h.calls.indexOf('apply_metadata'))
  expect(h.calls.indexOf('ack')).toBeGreaterThan(h.calls.indexOf('apply_structure'))
  expect(h.metadata.pullOnce).toHaveBeenCalledOnce(); expect(h.structural.applyOnce).toHaveBeenCalledOnce()
  expect(result.errors).toEqual([{ stage: 'upload_structure', code: 'Error' }])
})

it('seals structural intents even when another bounded writer has remaining work', async () => {
  const h = await setup(true)
  h.metadata.sealOnce.mockResolvedValueOnce(8)
  const result = await h.cycle.runOnce('local', DEVICE)
  expect(result.hasRemainingWork).toBe(true)
  expect(h.structural.sealOnce).toHaveBeenCalledOnce()
})


it('runs the account reader before shared ACK and preserves its typed blocker',async()=>{
  const h=await setup(false,true)
  h.metadata.ackOnce.mockImplementationOnce(async()=>{ expect(h.calls.at(-1)).toBe('apply_account'); return {status:'no_progress',cursor:0} })
  const result=await h.cycle.runOnce('local',DEVICE)
  expect(result.blocked).toContain('account_entity_codec_not_activated')
  expect(result.hasRemainingWork).toBe(true)
  expect(result.ack).toEqual({status:'no_progress',cursor:0})
})
