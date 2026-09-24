import { beforeEach, describe, expect, it, vi } from 'vitest'

import { cloudProjectsApi, type CloudProjectBootstrapDescriptor } from '@/api/cloudProjects'
import { NormalUserAuthRuntime, StaleAuthContextError } from '@/auth/userAuth'
import type {
  CloudProjectBootstrapRecord,
  CloudProjectBootstrapRepository,
} from '@/infrastructure/sqlite/cloudProjectBootstrapRepository'
import { CloudProjectBootstrapBlockedError, CloudProjectBootstrapCoordinator } from './projectBootstrap'

const USER = '123e4567-e89b-42d3-a456-426614174099'
const PROJECT = '123e4567-e89b-42d3-a456-426614174010'
const DEVICE = '123e4567-e89b-42d3-a456-426614174001'
const TOKEN = '123e4567-e89b-42d3-a456-426614174020'
const IDENTITY = { localAccountId: 'local-account', deviceId: DEVICE }
const EMPTY_CYCLE = { stages: [], sealed: [], uploaded: 0, pulled: [], applied: [], blocked: [], errors: [], hasRemainingWork: false }

function auth(): NormalUserAuthRuntime {
  return new NormalUserAuthRuntime({
    login: vi.fn().mockResolvedValue({ access_token: 'token', refresh_token: 'refresh', access_expires_in: 60 }),
    refresh: vi.fn(), logout: vi.fn().mockResolvedValue(undefined),
    me: vi.fn().mockResolvedValue({ id: USER, username: 'user', email: 'u@example.test', email_verified: true, role: 'user', status: 'active', created_at: 'now' }),
  })
}

function descriptor(state: 'legacy' | 'initializing' | 'active' = 'active'): CloudProjectBootstrapDescriptor {
  return {
    project_id: PROJECT, bootstrap_id: state === 'legacy' ? null : TOKEN,
    origin_device_id: state === 'legacy' ? null : DEVICE, state,
    initial_event_count: state === 'active' ? 2 : null,
    initial_max_server_sequence: state === 'active' ? 2 : null,
  }
}

function record(phase: CloudProjectBootstrapRecord['phase'] = 'prepared'): CloudProjectBootstrapRecord {
  return {
    project_id: PROJECT, account_id: IDENTITY.localAccountId, device_id: DEVICE,
    bootstrap_id: TOKEN, mode: 'upload_existing', phase,
    remote_state: phase === 'prepared' ? null : phase === 'ready' ? 'active' : 'initializing',
    initial_event_count: phase === 'prepared' || phase === 'registered' ? 0 : 2,
    initial_local_ordinal_hi: phase === 'prepared' || phase === 'registered' ? 0 : 2,
    remote_high_water: phase === 'prepared' ? null : 0,
    initial_max_server_sequence: phase === 'ready' ? 2 : null, blocked_reason: null,
  }
}

function repository(initial: CloudProjectBootstrapRecord[] = []) {
  let records = [...initial]
  const repo: CloudProjectBootstrapRepository = {
    preflight: vi.fn().mockResolvedValue([]),
    prepare: vi.fn(async () => {
      const value = records[0] ?? record()
      records = [value]
      return value
    }),
    confirmRegistration: vi.fn(async (_scope, remoteState, remoteHighWater) => {
      const current = records[0] ?? record()
      const next = { ...current, phase: current.phase === 'prepared' ? 'registered' as const : current.phase, remote_state: remoteState, remote_high_water: remoteHighWater }
      records = [next]
      return next
    }),
    capture: vi.fn(async () => {
      const next = record('captured'); records = [next]; return next
    }),
    cohort: vi.fn().mockResolvedValue({ event_count: 2, accepted_count: 2, max_server_sequence: 2, complete: true }),
    markCompleting: vi.fn(async () => {
      const next = { ...record('completing'), remote_state: 'initializing' as const }; records = [next]; return next
    }),
    markReady: vi.fn(async () => {
      const next = { ...record('ready'), remote_state: 'active' as const }; records = [next]; return next
    }),
    list: vi.fn(async () => records),
    importRemote: vi.fn(),
    setPaused: vi.fn(async (_scope, paused) => {
      const current = records[0] ?? record('ready')
      const next = { ...current, phase: paused ? 'paused' as const : 'ready' as const }
      records = [next]
      return next
    }),
  }
  return { repo, records: () => records }
}

function workers() {
  return {
    registerDevice: vi.fn().mockResolvedValue(undefined),
    sealOnce: vi.fn().mockResolvedValue(undefined), uploadOnce: vi.fn().mockResolvedValue(undefined),
    runOnce: vi.fn().mockResolvedValue(EMPTY_CYCLE),
  }
}

describe('safe cloud project bootstrap coordinator', () => {
  beforeEach(() => vi.restoreAllMocks())

  it('blocks account-wide pull and ACK until every remote project has a matching active local lineage', async () => {
    const session = auth(); await session.login('user', 'password')
    vi.spyOn(cloudProjectsApi, 'listBootstraps').mockResolvedValue({ projects: [descriptor('active')], current_cursor: 2 })
    const { repo } = repository([])
    const work = workers()
    const coordinator = new CloudProjectBootstrapCoordinator(session, repo, work)

    const reconciled = await coordinator.reconcile(IDENTITY)
    expect(reconciled).toMatchObject({ readyForCycle: false, readyForNormalCycle: false })
    expect(reconciled.reasons).toContain(`missing_local_binding:${PROJECT}`)
    await expect(coordinator.runReadyCycle(IDENTITY)).rejects.toBeInstanceOf(CloudProjectBootstrapBlockedError)
    expect(work.runOnce).not.toHaveBeenCalled()
  })

  it('orders registration, atomic capture, durable cohort proof, completion, reconciliation, then the normal cycle', async () => {
    const session = auth(); await session.login('user', 'password')
    let serverState: 'initializing' | 'active' = 'initializing'
    vi.spyOn(cloudProjectsApi, 'registerBootstrap').mockImplementation(async () => ({ project: descriptor(serverState), current_cursor: 0 }))
    vi.spyOn(cloudProjectsApi, 'completeBootstrap').mockImplementation(async () => {
      serverState = 'active'; return { project: descriptor('active'), current_cursor: 2 }
    })
    vi.spyOn(cloudProjectsApi, 'listBootstraps').mockImplementation(async () => ({ projects: [descriptor(serverState)], current_cursor: serverState === 'active' ? 2 : 0 }))
    const { repo } = repository()
    const work = workers()
    const coordinator = new CloudProjectBootstrapCoordinator(session, repo, work)

    const stages: string[] = []
    const result = await coordinator.bootstrapLocalProject(IDENTITY, PROJECT, stage => stages.push(stage))

    expect(repo.preflight).toHaveBeenCalledBefore(repo.prepare as ReturnType<typeof vi.fn>)
    expect(work.registerDevice).toHaveBeenCalledBefore(cloudProjectsApi.registerBootstrap as ReturnType<typeof vi.fn>)
    expect(repo.capture).toHaveBeenCalledBefore(repo.markCompleting as ReturnType<typeof vi.fn>)
    expect(repo.markCompleting).toHaveBeenCalledBefore(cloudProjectsApi.completeBootstrap as ReturnType<typeof vi.fn>)
    expect(work.runOnce).toHaveBeenCalledAfter(cloudProjectsApi.completeBootstrap as ReturnType<typeof vi.fn>)
    expect(repo.markReady).toHaveBeenCalledAfter(work.runOnce)
    expect(result).toMatchObject({ project: { phase: 'ready' }, hasRemainingWork: false })
    expect(stages).toEqual([
      'registering', 'preparing_initial_notes', 'completing_registration',
      'pulling_remote_notes', 'initial_sync_completed',
    ])
  })

  it('does not register when native preflight finds one unsupported Note', async () => {
    const session = auth(); await session.login('user', 'password')
    const register = vi.spyOn(cloudProjectsApi, 'registerBootstrap')
    const { repo } = repository()
    vi.mocked(repo.preflight).mockResolvedValue([{ note_id: 'note', code: 'unsupported_content_format' }])
    const work = workers()
    const coordinator = new CloudProjectBootstrapCoordinator(session, repo, work)

    await expect(coordinator.bootstrapLocalProject(IDENTITY, PROJECT)).rejects.toMatchObject({ code: 'unsupported_content_format' })
    expect(register).not.toHaveBeenCalled()
    expect(work.runOnce).not.toHaveBeenCalled()
  })

  it('rejects stale auth after registration without capture, completion, pull, or ACK', async () => {
    const session = auth(); await session.login('user', 'password')
    vi.spyOn(cloudProjectsApi, 'registerBootstrap').mockImplementation(async () => {
      await session.logout()
      return { project: descriptor('initializing'), current_cursor: 0 }
    })
    const { repo } = repository()
    const work = workers()
    const coordinator = new CloudProjectBootstrapCoordinator(session, repo, work)

    await expect(coordinator.bootstrapLocalProject(IDENTITY, PROJECT)).rejects.toBeInstanceOf(StaleAuthContextError)
    expect(repo.capture).not.toHaveBeenCalled()
    expect(work.runOnce).not.toHaveBeenCalled()
  })

  it('replays the same durable token after a lost registration response', async () => {
    const session = auth(); await session.login('user', 'password')
    const register = vi.spyOn(cloudProjectsApi, 'registerBootstrap')
      .mockRejectedValueOnce(new TypeError('network response lost'))
      .mockResolvedValueOnce({ project: descriptor('initializing'), current_cursor: 0 })
    vi.spyOn(cloudProjectsApi, 'completeBootstrap').mockResolvedValue({ project: descriptor('active'), current_cursor: 2 })
    vi.spyOn(cloudProjectsApi, 'listBootstraps').mockResolvedValue({ projects: [descriptor('active')], current_cursor: 2 })
    const { repo } = repository()
    const coordinator = new CloudProjectBootstrapCoordinator(session, repo, workers())

    await expect(coordinator.bootstrapLocalProject(IDENTITY, PROJECT)).rejects.toThrow('network response lost')
    await expect(coordinator.bootstrapLocalProject(IDENTITY, PROJECT)).resolves.toMatchObject({ project: { bootstrap_id: TOKEN } })
    expect(register).toHaveBeenCalledTimes(2)
    expect(register.mock.calls[0]![2]).toEqual(register.mock.calls[1]![2])
    expect(repo.prepare).toHaveBeenCalledTimes(2)
  })

  it('keeps partial upload durable and resumes with the same bootstrap lineage', async () => {
    const session = auth(); await session.login('user', 'password')
    let serverState: 'initializing' | 'active' = 'initializing'
    vi.spyOn(cloudProjectsApi, 'registerBootstrap').mockImplementation(async () => ({ project: descriptor(serverState), current_cursor: 0 }))
    vi.spyOn(cloudProjectsApi, 'completeBootstrap').mockImplementation(async () => {
      serverState = 'active'
      return { project: descriptor('active'), current_cursor: 2 }
    })
    vi.spyOn(cloudProjectsApi, 'listBootstraps').mockImplementation(async () => ({
      projects: [descriptor(serverState)], current_cursor: serverState === 'active' ? 2 : 0,
    }))
    const { repo } = repository()
    let cohortComplete = false
    vi.mocked(repo.cohort).mockImplementation(async () => cohortComplete
      ? { event_count: 2, accepted_count: 2, max_server_sequence: 2, complete: true }
      : { event_count: 2, accepted_count: 1, max_server_sequence: 1, complete: false })
    const work = workers()
    const coordinator = new CloudProjectBootstrapCoordinator(session, repo, work)

    const first = await coordinator.bootstrapLocalProject(IDENTITY, PROJECT)
    expect(first.project.bootstrap_id).toBe(TOKEN)
    expect(first.hasRemainingWork).toBe(true)
    expect(work.uploadOnce).toHaveBeenCalledTimes(8)
    expect(cloudProjectsApi.completeBootstrap).not.toHaveBeenCalled()

    cohortComplete = true
    const second = await coordinator.bootstrapLocalProject(IDENTITY, PROJECT)
    expect(second.project.bootstrap_id).toBe(TOKEN)
    expect(repo.prepare).toHaveBeenCalledTimes(2)
    expect(repo.capture).toHaveBeenCalledTimes(2)
    expect(cloudProjectsApi.completeBootstrap).toHaveBeenCalledTimes(1)
  })

  it('exposes read-only native preflight and durable pause/resume without starting a cycle', async () => {
    const session = auth(); await session.login('user', 'password')
    vi.spyOn(cloudProjectsApi, 'listBootstraps').mockResolvedValue({ projects: [descriptor('active')], current_cursor: 2 })
    const { repo } = repository([record('ready')])
    const work = workers()
    const coordinator = new CloudProjectBootstrapCoordinator(session, repo, work)

    await expect(coordinator.preflightLocalProject(PROJECT)).resolves.toEqual([])
    const paused = await coordinator.setPaused(IDENTITY, PROJECT, true)
    expect(repo.setPaused).toHaveBeenCalledWith(expect.objectContaining({ project_id: PROJECT, bootstrap_id: TOKEN }), true)
    expect(paused.readyForNormalCycle).toBe(false)
    expect(paused.reasons).toContain(`paused:${PROJECT}`)
    await coordinator.setPaused(IDENTITY, PROJECT, false)
    expect(work.runOnce).not.toHaveBeenCalled()
  })
})
