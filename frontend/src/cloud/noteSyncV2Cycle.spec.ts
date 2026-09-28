import { describe, expect, it, vi } from 'vitest'
import { NormalUserAuthRuntime } from '@/auth/userAuth'
import { NoteSyncOrchestrator } from './noteSyncOrchestrator'
import { NoteSyncV2Cycle } from './noteSyncV2Cycle'

const USER = '123e4567-e89b-42d3-a456-426614174099'
const DEVICE = '123e4567-e89b-42d3-a456-426614174001'
const PAGE = { committed_cursor: 0, new_events: 0, replayed_events: 0, has_more: false }

async function setup(account = 'local') {
  const auth = new NormalUserAuthRuntime({
    login: vi.fn().mockResolvedValue({ access_token: 'token', refresh_token: 'refresh', access_expires_in: 60 }),
    refresh: vi.fn(), logout: vi.fn(),
    me: vi.fn().mockResolvedValue({ id: USER, username: 'u', email: 'u@example.test', email_verified: true,
      role: 'user', status: 'active', created_at: '2026-01-01T00:00:00Z' }),
  })
  await auth.login('u', 'p')
  const context = auth.requireContext()
  let current = true
  let writerMode = 2
  const calls: string[] = []
  const lease = { localAccountId: account, canonicalUserId: USER, authEpoch: context.authEpoch,
    keyContextId: 'key', keyEpoch: 1, isCurrent: () => current }
  const keys = { leaseForAccount: vi.fn(() => lease) }
  const bindings = { ensureForCurrentUser: vi.fn(async () => ({ context })) }
  const identity = { read: vi.fn(async () => ({ local_account_id: account, device_id: DEVICE })) }
  const capabilities = { capabilities: vi.fn(async () => ({ supported_transport_version: 2,
    writer_transport_version: writerMode, cutover_epoch: 0 })) }
  const device = { registerOnce: vi.fn(async () => { calls.push('register') }) }
  const intents = { list: vi.fn(async () => { calls.push('seal'); return [] as Array<{ event_id: string, mutation_generation: number, seal_state: string }> }), recordSealFailure: vi.fn(), commitSealedEvent: vi.fn() }
  const ordinary = { uploadOnce: vi.fn(async () => { calls.push('ordinary'); return { uploaded: 1, deviceId: DEVICE } }) }
  const resolution = { uploadOnce: vi.fn(async () => { calls.push('resolution'); return { uploaded: 2, deviceId: DEVICE } }) }
  const inbox = { pullOnce: vi.fn(async () => { calls.push('pull'); return PAGE }) }
  const v1Applier = { applyPage: vi.fn(async () => { calls.push('apply_v1'); return { listed: 0, lastServerSequence: 0, errorCount: 0, results: [] as Array<{ status: string }> } }) }
  const resolutionApplier = {
    applyReceivedPage: vi.fn(async () => { calls.push('apply_resolution'); return { listed: 0, lastServerSequence: 0, errorCount: 0, results: [] as Array<{ status: string }> } }),
    retryOrphansFrom: vi.fn(async () => { calls.push('orphans'); return { listed: 0, lastServerSequence: 0,
      errorCount: 0, reachedEnd: true, results: [] as Array<{ status: string }> } }),
  }
  const mixed = new NoteSyncOrchestrator(auth, keys as never, intents as never, {} as never, {} as never,
    v1Applier as never, device as never, resolutionApplier as never)
  const ack = { ackOnce: vi.fn(async () => { calls.push('ack'); return { status: 'no_progress', cursor: 0 } as const }) }
  const cycle = new NoteSyncV2Cycle(auth, bindings as never, identity as never, keys as never,
    device as never, intents as never, ordinary as never, resolution as never, inbox as never,
    mixed, ack as never, capabilities as never)
  return { auth, cycle, mixed, calls, lease, keys, bindings, identity, capabilities, device, intents, ordinary,
    resolution, inbox, v1Applier, resolutionApplier, ack,
    invalidate: () => { current = false }, mode: (value: number) => { writerMode = value } }
}

describe('dormant mode-2 Note sync cycle', () => {
  it('runs the complete ordered cycle, including mixed streams and orphan retry', async () => {
    const h = await setup()
    h.inbox.pullOnce.mockImplementationOnce(async () => { h.calls.push('pull'); return { ...PAGE, committed_cursor: 2, has_more: true } })
    const result = await h.cycle.runOnce('local', DEVICE)
    expect(result.stages).toEqual(['preflight', 'register_device', 'seal', 'upload_ordinary', 'upload_resolution',
      'pull', 'pull', 'mixed_apply', 'ack_v2'])
    expect(h.calls).toEqual(['register', 'seal', 'ordinary', 'resolution', 'pull', 'pull',
      'apply_v1', 'apply_resolution', 'orphans', 'ack'])
    expect(result).toMatchObject({ ordinaryUploaded: 1, resolutionUploaded: 2, errors: [], blocked: [],
      hasRemainingWork: false, ack: { status: 'no_progress' } })
    expect(result.mixedApply?.orphanRetry?.reachedEnd).toBe(true)
  })

  it('keeps pull, seal and mixed work bounded and exposes blocked statuses', async () => {
    const h = await setup()
    h.intents.list.mockImplementationOnce(async () => { h.calls.push('seal'); return Array.from({ length: 2 }, (_, i) => ({
      event_id: `e${i}`, mutation_generation: 1, seal_state: 'blocked',
    })) })
    h.inbox.pullOnce.mockResolvedValue({ ...PAGE, committed_cursor: 3, has_more: true })
    h.v1Applier.applyPage.mockImplementationOnce(async () => ({ listed: 1, lastServerSequence: 4,
      errorCount: 0, results: [{ status: 'conflict' }] }))
    h.resolutionApplier.retryOrphansFrom.mockImplementationOnce(async () => ({ listed: 1, lastServerSequence: 5,
      errorCount: 0, reachedEnd: false, results: [{ status: 'orphan' }] }))
    const result = await h.cycle.runOnce('local', DEVICE,
      { sealLimit: 2, maxPullPages: 2, applyLimit: 1, maxApplyPasses: 1 })
    expect(result.pulled).toHaveLength(2)
    expect(result.sealed[0]?.results.map(item => item.status)).toEqual(['blocked_skipped', 'blocked_skipped'])
    expect(result.blocked).toEqual(['blocked_skipped', 'conflict', 'orphan'])
    expect(result.mixedApply?.hasRemainingWork).toBe(true)
    expect(result.hasRemainingWork).toBe(true)
  })

  it('requires current key, account, device and mode before mutation', async () => {
    const missing = await setup()
    missing.keys.leaseForAccount.mockReturnValueOnce(null as never)
    await expect(missing.cycle.runOnce('local', DEVICE)).rejects.toThrow('')
    const stale = await setup(); stale.invalidate()
    await expect(stale.cycle.runOnce('local', DEVICE)).rejects.toThrow('')
    const wrong = await setup(); wrong.identity.read.mockResolvedValueOnce({ local_account_id: 'other', device_id: DEVICE })
    expect((await wrong.cycle.runOnce('local', DEVICE)).errors[0]?.stage).toBe('preflight')
    expect(wrong.device.registerOnce).not.toHaveBeenCalled()
    const mode = await setup(); mode.mode(1)
    expect((await mode.cycle.runOnce('local', DEVICE)).errors[0]).toEqual({ stage: 'preflight', code: 'mode_incompatible' })
    expect(mode.device.registerOnce).not.toHaveBeenCalled()
  })

  it('stops after registration failure, preserving pending work', async () => {
    const h = await setup()
    h.device.registerOnce.mockRejectedValueOnce(new Error('offline'))
    expect(await h.cycle.runOnce('local', DEVICE)).toMatchObject({
      stages: ['preflight', 'register_device'], errors: [{ stage: 'register_device', code: 'Error' }], hasRemainingWork: true,
    })
    expect(h.intents.list).not.toHaveBeenCalled()
  })

  it('tries both outbound ledgers on ordinary error and stops before pull', async () => {
    const h = await setup()
    h.ordinary.uploadOnce.mockRejectedValueOnce(new Error('offline'))
    const result = await h.cycle.runOnce('local', DEVICE)
    expect(result.errors).toEqual([{ stage: 'upload_ordinary', code: 'Error' }])
    expect(result.resolutionUploaded).toBe(2)
    expect(h.inbox.pullOnce).not.toHaveBeenCalled()
    const other = await setup()
    other.resolution.uploadOnce.mockRejectedValueOnce(new Error('offline'))
    expect((await other.cycle.runOnce('local', DEVICE)).ordinaryUploaded).toBe(1)
    expect(other.inbox.pullOnce).not.toHaveBeenCalled()
  })

  it('never falls back when mode changes at upload, pull or ACK', async () => {
    const ordinary = await setup()
    ordinary.intents.list.mockImplementationOnce(async () => { ordinary.mode(1); return [] })
    expect((await ordinary.cycle.runOnce('local', DEVICE)).errors[0]?.stage).toBe('upload_ordinary')
    expect(ordinary.ordinary.uploadOnce).not.toHaveBeenCalled()
    expect(ordinary.resolution.uploadOnce).not.toHaveBeenCalled()
    const resolution = await setup()
    resolution.ordinary.uploadOnce.mockImplementationOnce(async () => {
      resolution.mode(1); return { uploaded: 1, deviceId: DEVICE }
    })
    expect((await resolution.cycle.runOnce('local', DEVICE)).errors[0]?.stage).toBe('upload_resolution')
    expect(resolution.resolution.uploadOnce).not.toHaveBeenCalled()
    const upload = await setup()
    upload.device.registerOnce.mockImplementationOnce(async () => { upload.mode(1) })
    expect((await upload.cycle.runOnce('local', DEVICE)).errors[0]?.stage).toBe('seal')
    expect(upload.ordinary.uploadOnce).not.toHaveBeenCalled()
    const pull = await setup()
    pull.resolution.uploadOnce.mockImplementationOnce(async () => { pull.calls.push('resolution'); pull.mode(1); return { uploaded: 1, deviceId: DEVICE } })
    expect((await pull.cycle.runOnce('local', DEVICE)).errors[0]?.stage).toBe('pull')
    expect(pull.ack.ackOnce).not.toHaveBeenCalled()
    const ack = await setup()
    ack.resolutionApplier.retryOrphansFrom.mockImplementationOnce(async () => { ack.mode(1); return {
      listed: 0, lastServerSequence: 0, errorCount: 0, reachedEnd: true, results: [],
    } })
    expect((await ack.cycle.runOnce('local', DEVICE)).errors[0]?.stage).toBe('ack_v2')
    expect(ack.ack.ackOnce).not.toHaveBeenCalled()
  })

  it('does not ACK after pull or top-level mixed failure, and reports ACK errors', async () => {
    const pull = await setup(); pull.inbox.pullOnce.mockRejectedValueOnce(new Error('commit failed'))
    expect((await pull.cycle.runOnce('local', DEVICE)).errors[0]?.stage).toBe('pull')
    expect(pull.ack.ackOnce).not.toHaveBeenCalled()
    const mixed = await setup(); vi.spyOn(mixed.mixed, 'runMixedInboxOnce').mockRejectedValueOnce(new Error('apply failed'))
    expect((await mixed.cycle.runOnce('local', DEVICE)).errors[0]?.stage).toBe('mixed_apply')
    expect(mixed.ack.ackOnce).not.toHaveBeenCalled()
    const ack = await setup(); ack.ack.ackOnce.mockRejectedValueOnce(new Error('ack failed'))
    expect((await ack.cycle.runOnce('local', DEVICE)).errors[0]?.stage).toBe('ack_v2')
    expect(ack.calls).toContain('orphans')
  })

  it('propagates mixed apply errors and blocked states without overriding native ACK', async () => {
    const h = await setup()
    h.v1Applier.applyPage.mockRejectedValueOnce(new Error('v1 page failed'))
    h.resolutionApplier.applyReceivedPage.mockImplementationOnce(async () => ({ listed: 1,
      lastServerSequence: 3, errorCount: 0, results: [{ status: 'self_echo_pending' }] }))
    const result = await h.cycle.runOnce('local', DEVICE)
    expect(result.mixedApply?.errors).toEqual([{ stage: 'apply_v1', code: 'Error' }])
    expect(result.blocked).toEqual(['self_echo_pending'])
    expect(result.hasRemainingWork).toBe(true)
    expect(h.resolutionApplier.retryOrphansFrom).toHaveBeenCalledTimes(1)
    expect(h.ack.ackOnce).toHaveBeenCalledTimes(1)
  })

  it('stops on stale lifecycle between registration and seal', async () => {
    const h = await setup()
    h.device.registerOnce.mockImplementationOnce(async () => { h.invalidate() })
    expect((await h.cycle.runOnce('local', DEVICE)).errors[0]?.stage).toBe('seal')
    expect(h.intents.list).not.toHaveBeenCalled()
  })

  it('joins one lifecycle flight and separates different devices', async () => {
    const h = await setup()
    let release!: () => void
    h.device.registerOnce.mockImplementationOnce(() => new Promise<void>(resolve => { release = resolve }))
    const first = h.cycle.runOnce('local', DEVICE)
    await vi.waitFor(() => expect(h.device.registerOnce).toHaveBeenCalledTimes(1))
    const second = h.cycle.runOnce('local', DEVICE)
    const otherDevice = await h.cycle.runOnce('local', '123e4567-e89b-42d3-a456-426614174002')
    expect(otherDevice.errors[0]?.stage).toBe('preflight')
    expect(h.identity.read).toHaveBeenCalledTimes(2)
    release()
    await Promise.all([first, second])
    expect(h.device.registerOnce).toHaveBeenCalledTimes(1)
  })
})
