import { describe, expect, it, vi } from 'vitest'
import { NormalUserAuthRuntime, StaleAuthContextError } from '@/auth/userAuth'
import { NoteSyncOrchestrator } from './noteSyncOrchestrator'

const USER = '123e4567-e89b-42d3-a456-426614174099'
const DEVICE = '123e4567-e89b-42d3-a456-426614174001'

function auth() {
  return new NormalUserAuthRuntime({
    login: vi.fn().mockResolvedValue({ access_token: 'token', refresh_token: 'refresh', access_expires_in: 60 }), refresh: vi.fn(), logout: vi.fn(),
    me: vi.fn().mockResolvedValue({ id: USER, username: 'u', email: 'u@example.test', email_verified: true, role: 'user', status: 'active', created_at: '2026-01-01T00:00:00Z' }),
  })
}

function harness(authEpoch: number) {
  let current = true
  const lease = { localAccountId: 'local', canonicalUserId: USER, authEpoch, keyContextId: 'key', keyEpoch: 1, isCurrent: vi.fn(() => current) }
  const keys = { leaseForAccount: vi.fn(() => lease) }
  const intents = { list: vi.fn().mockResolvedValue([]), recordSealFailure: vi.fn(), commitSealedEvent: vi.fn() }
  const uploader = { uploadOnce: vi.fn().mockResolvedValue({ uploaded: 0, deviceId: null }) }
  const inbox = { pullOnce: vi.fn().mockResolvedValue({ committed_cursor: 0, new_events: 0, replayed_events: 0, has_more: false }) }
  const applier = { applyOnce: vi.fn().mockResolvedValue({ listed: 0, results: [] }) }
  const deviceAck = { registerOnce: vi.fn().mockResolvedValue({ deviceId: DEVICE, serverAckCursor: 0 }), ackOnce: vi.fn().mockResolvedValue({ status: 'no_progress', cursor: 0 }) }
  return { keys, intents, uploader, inbox, applier, deviceAck, invalidate: () => { current = false } }
}

async function orchestrator() {
  const runtime = auth(); await runtime.login('u', 'p')
  const h = harness(runtime.requireContext().authEpoch)
  const value = new NoteSyncOrchestrator(runtime, h.keys as never, h.intents as never, h.uploader as never, h.inbox as never, h.applier as never, h.deviceAck as never)
  return { runtime, h, value }
}

describe('bounded Notes sync orchestration', () => {
  it('runs the protected components in order for an empty cycle', async () => {
    const { h, value } = await orchestrator()
    const result = await value.runOnce('local', DEVICE)
    expect(result.stages).toEqual(['register_device', 'seal', 'upload', 'pull', 'apply', 'ack'])
    expect(result).toMatchObject({ uploaded: 0, blocked: [], errors: [], hasRemainingWork: false, ack: { status: 'no_progress' } })
    expect(h.intents.list).toHaveBeenCalledTimes(1); expect(h.uploader.uploadOnce).toHaveBeenCalledTimes(1)
    expect(h.inbox.pullOnce).toHaveBeenCalledTimes(1); expect(h.applier.applyOnce).toHaveBeenCalledTimes(1)
    await value.runOnce('local', DEVICE)
    expect(h.deviceAck.registerOnce).toHaveBeenCalledTimes(2)
  })

  it('joins concurrent calls only for the same current account/key context', async () => {
    const { h, value } = await orchestrator()
    let release!: () => void
    h.deviceAck.registerOnce.mockImplementationOnce(() => new Promise<void>(resolve => { release = resolve }))
    const first = value.runOnce('local', DEVICE)
    await vi.waitFor(() => expect(h.deviceAck.registerOnce).toHaveBeenCalledTimes(1))
    const second = value.runOnce('local', DEVICE)
    release()
    await expect(Promise.all([first, second])).resolves.toHaveLength(2)
    expect(h.deviceAck.registerOnce).toHaveBeenCalledTimes(1)
  })

  it('stops bounded pull and apply loops on no progress or their configured budgets', async () => {
    const { h, value } = await orchestrator()
    h.inbox.pullOnce.mockResolvedValue({ committed_cursor: 3, new_events: 1, replayed_events: 0, has_more: true })
    h.applier.applyOnce.mockResolvedValue({ listed: 8, results: [{ status: 'applied' }] })
    const result = await value.runOnce('local', DEVICE, { maxPullPages: 4, maxApplyPasses: 2, applyLimit: 8 })
    expect(h.inbox.pullOnce).toHaveBeenCalledTimes(2)
    expect(h.applier.applyOnce).toHaveBeenCalledTimes(2)
    expect(result.hasRemainingWork).toBe(true)
  })

  it('preserves independent inbound work after upload failure and records structured errors', async () => {
    const { h, value } = await orchestrator()
    h.uploader.uploadOnce.mockRejectedValueOnce(new Error('lost upload response'))
    const result = await value.runOnce('local', DEVICE)
    expect(result.errors).toContainEqual({ stage: 'upload', code: 'Error' })
    expect(h.inbox.pullOnce).toHaveBeenCalledTimes(1)
    expect(h.applier.applyOnce).toHaveBeenCalledTimes(1)
    expect(h.deviceAck.ackOnce).toHaveBeenCalledTimes(1)
  })

  it('keeps ACK delegated and does not claim unresolved inbox states as progress', async () => {
    const { h, value } = await orchestrator()
    h.applier.applyOnce.mockResolvedValue({ listed: 1, results: [{ event_id: 'e', server_sequence: 2, status: 'conflict' }] })
    h.deviceAck.ackOnce.mockResolvedValue({ status: 'no_progress', cursor: 1 })
    const result = await value.runOnce('local', DEVICE)
    expect(result.blocked).toEqual(['conflict'])
    expect(h.deviceAck.ackOnce).toHaveBeenCalledWith('local', DEVICE)
    expect(result.ack).toEqual({ status: 'no_progress', cursor: 1 })
  })

  it('does not start dependent stages after registration failure or stale key context', async () => {
    const { h, value } = await orchestrator()
    h.deviceAck.registerOnce.mockRejectedValueOnce(new Error('registration timeout'))
    await expect(value.runOnce('local', DEVICE)).resolves.toMatchObject({ errors: [{ stage: 'register_device', code: 'Error' }] })
    expect(h.uploader.uploadOnce).not.toHaveBeenCalled()

    const second = await orchestrator()
    second.h.deviceAck.registerOnce.mockImplementationOnce(async () => { second.h.invalidate() })
    await expect(second.value.runOnce('local', DEVICE)).rejects.toBeInstanceOf(StaleAuthContextError)
    expect(second.h.uploader.uploadOnce).not.toHaveBeenCalled()
  })
})
