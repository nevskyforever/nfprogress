import { describe, expect, it, vi } from 'vitest'

import { ApiError } from '@/api/client'
import { NormalUserAuthRuntime, StaleAuthContextError } from '@/auth/userAuth'
import { NoteSyncTransportRouter } from './noteSyncTransportRouter'

const USER_A = '123e4567-e89b-42d3-a456-426614174099'
const USER_B = '123e4567-e89b-42d3-a456-426614174098'
const V1 = { stages: ['v1'], sealed: [], uploaded: 3, pulled: [], applied: [],
  blocked: ['v1-block'], errors: [], hasRemainingWork: true }
const V2 = { stages: ['v2'], sealed: [], ordinaryUploaded: 2, resolutionUploaded: 1,
  pulled: [], mixedApply: { stages: ['mixed'], v1Pages: [], resolutionPages: [], blocked: [], errors: [], hasRemainingWork: true },
  blocked: [], errors: [{ stage: 'ack_v2', code: 'retry' }], hasRemainingWork: true }

async function harness() {
  let userId = USER_A
  let mode: 1 | 2 = 1
  let epoch = 0
  const auth = new NormalUserAuthRuntime({
    login: vi.fn().mockResolvedValue({ access_token: 'token', refresh_token: 'refresh', access_expires_in: 60 }),
    refresh: vi.fn(), logout: vi.fn().mockResolvedValue(undefined),
    me: vi.fn(async () => ({ id: userId, username: 'user', email: 'u@example.test',
      email_verified: true, role: 'user', status: 'active', created_at: 'now' })),
  })
  await auth.login('user', 'password')
  const v1 = { runOnce: vi.fn().mockResolvedValue(V1) }
  const v2 = { runOnce: vi.fn().mockResolvedValue(V2) }
  const v1Upload = { uploadOnce: vi.fn().mockResolvedValue(undefined) }
  const v2Upload = { uploadOnce: vi.fn().mockResolvedValue(undefined) }
  const api = { capabilities: vi.fn(async () => ({ supported_transport_version: 2 as const,
    writer_transport_version: mode, cutover_epoch: epoch })) }
  const router = new NoteSyncTransportRouter(auth, v1, v2, v1Upload, v2Upload, api)
  return { auth, v1, v2, v1Upload, v2Upload, api, router,
    setMode: (value: 1 | 2, generation: number) => { mode = value; epoch = generation },
    setUser: (value: string) => { userId = value } }
}

describe('production Notes transport router', () => {
  it('selects only v1 in mode one and retains its diagnostics and epoch', async () => {
    const h = await harness()
    const result = await h.router.runOnce('account-a', 'device', { applyLimit: 2 })
    expect(result).toEqual({ transport_version: 1, cutover_epoch: 0, cycle: V1,
      hasRemainingWork: true, blocked: V1.blocked, errors: V1.errors })
    expect(h.v1.runOnce).toHaveBeenCalledWith('account-a', 'device', { applyLimit: 2 })
    expect(h.v2.runOnce).not.toHaveBeenCalled()
  })

  it('selects only v2 in mode two and retains ordinary, resolution, and mixed diagnostics', async () => {
    const h = await harness(); h.setMode(2, 7)
    const result = await h.router.runOnce('account-a', 'device')
    expect(result).toEqual({ transport_version: 2, cutover_epoch: 7, cycle: V2,
      hasRemainingWork: true, blocked: V2.blocked, errors: V2.errors })
    expect(h.v2.runOnce).toHaveBeenCalledOnce()
    expect(h.v1.runOnce).not.toHaveBeenCalled()
  })

  it('fails closed before either cycle on malformed or unsupported capabilities', async () => {
    const h = await harness()
    for (const response of [
      { supported_transport_version: 3, writer_transport_version: 1, cutover_epoch: 0 },
      { supported_transport_version: 2, writer_transport_version: 3, cutover_epoch: 0 },
      { supported_transport_version: 2, writer_transport_version: 1, cutover_epoch: -1 },
      { supported_transport_version: 2, writer_transport_version: 1 },
    ]) {
      h.api.capabilities.mockResolvedValueOnce(response as never)
      await expect(h.router.runOnce('account-a', 'device')).rejects.toThrow()
    }
    expect(h.v1.runOnce).not.toHaveBeenCalled()
    expect(h.v2.runOnce).not.toHaveBeenCalled()
  })

  it('does not run a cycle when the capabilities request fails or auth changes while it is in flight', async () => {
    const h = await harness()
    h.api.capabilities.mockRejectedValueOnce(new TypeError('network unavailable'))
    await expect(h.router.runOnce('account-a', 'device')).rejects.toThrow('network unavailable')
    h.api.capabilities.mockImplementationOnce(async () => {
      await h.auth.logout()
      return { supported_transport_version: 2, writer_transport_version: 1, cutover_epoch: 0 }
    })
    await expect(h.router.runOnce('account-a', 'device')).rejects.toBeInstanceOf(StaleAuthContextError)
    expect(h.v1.runOnce).not.toHaveBeenCalled()
    expect(h.v2.runOnce).not.toHaveBeenCalled()
  })

  it('never falls back to the other transport after a selected cycle fails', async () => {
    const h = await harness()
    h.v1.runOnce.mockRejectedValueOnce(new ApiError(409, 'sync_transport_mode_incompatible', 'changed'))
    await expect(h.router.runOnce('account-a', 'device')).rejects.toMatchObject({ code: 'sync_transport_mode_incompatible' })
    expect(h.v2.runOnce).not.toHaveBeenCalled()
    h.setMode(2, 1)
    h.v2.runOnce.mockRejectedValueOnce(new ApiError(409, 'sync_transport_mode_incompatible', 'changed'))
    await expect(h.router.runOnce('account-a', 'device')).rejects.toMatchObject({ code: 'sync_transport_mode_incompatible' })
    expect(h.v1.runOnce).toHaveBeenCalledTimes(1)
  })

  it('re-reads capabilities for every new cycle, auth lifecycle, and account', async () => {
    const h = await harness()
    await h.router.runOnce('account-a', 'device')
    h.setMode(2, 1)
    await h.router.runOnce('account-a', 'device')
    await h.router.runOnce('account-b', 'device')
    await h.auth.logout()
    h.setUser(USER_B)
    await h.auth.login('user-b', 'password')
    h.setMode(1, 0)
    await h.router.runOnce('account-b', 'device')
    expect(h.api.capabilities).toHaveBeenCalledTimes(4)
    expect(h.v1.runOnce).toHaveBeenCalledTimes(2)
    expect(h.v2.runOnce).toHaveBeenCalledTimes(2)
  })

  it('routes each bootstrap upload independently and never falls back within the request', async () => {
    const h = await harness()
    await h.router.uploadOnce('account-a')
    expect(h.v1Upload.uploadOnce).toHaveBeenCalledOnce()
    expect(h.v2Upload.uploadOnce).not.toHaveBeenCalled()
    h.setMode(2, 1)
    await h.router.uploadOnce('account-a')
    expect(h.v2Upload.uploadOnce).toHaveBeenCalledOnce()
    h.v2Upload.uploadOnce.mockRejectedValueOnce(new ApiError(409, 'sync_transport_mode_incompatible', 'changed'))
    await expect(h.router.uploadOnce('account-a')).rejects.toMatchObject({ code: 'sync_transport_mode_incompatible' })
    expect(h.v1Upload.uploadOnce).toHaveBeenCalledTimes(1)
    expect(h.api.capabilities).toHaveBeenCalledTimes(3)
  })
})
