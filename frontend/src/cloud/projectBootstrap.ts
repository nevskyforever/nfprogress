import { cloudProjectsApi, type CloudProjectBootstrapDescriptor } from '@/api/cloudProjects'
import { NormalUserAuthRuntime, StaleAuthContextError, type AuthContextSnapshot } from '@/auth/userAuth'
import type { CloudProjectBootstrapRecord, CloudProjectBootstrapRepository, CloudProjectBootstrapScope } from '@/infrastructure/sqlite/cloudProjectBootstrapRepository'
import type { NoteSyncOrchestratorResult } from './noteSyncOrchestrator'

export class CloudProjectBootstrapBlockedError extends Error {
  readonly name = 'CloudProjectBootstrapBlockedError'
  constructor(readonly code: string) { super(code) }
}

export interface CloudRegistryReconciliation {
  readonly readyForCycle: boolean
  readonly readyForNormalCycle: boolean
  readonly reasons: readonly string[]
  readonly remote: readonly CloudProjectBootstrapDescriptor[]
  readonly local: readonly CloudProjectBootstrapRecord[]
  readonly currentCursor: number
}

export interface CloudProjectBootstrapProgress {
  readonly project: CloudProjectBootstrapRecord
  readonly registry: CloudRegistryReconciliation
  readonly cycle?: NoteSyncOrchestratorResult
  readonly hasRemainingWork: boolean
}

export type CloudProjectBootstrapStage =
  | 'registering'
  | 'preparing_initial_notes'
  | 'uploading_initial_notes'
  | 'completing_registration'
  | 'pulling_remote_notes'
  | 'initial_sync_completed'
  | 'remaining_work'

export type CloudProjectBootstrapReporter = (stage: CloudProjectBootstrapStage) => void

interface BootstrapIdentity {
  readonly localAccountId: string
  readonly deviceId: string
}

interface BootstrapWorkers {
  registerDevice(localAccountId: string, deviceId: string): Promise<unknown>
  sealOnce(): Promise<unknown>
  uploadOnce(localAccountId: string): Promise<unknown>
  runOnce(localAccountId: string, deviceId: string): Promise<NoteSyncOrchestratorResult>
}

const MAX_BOOTSTRAP_UPLOAD_PASSES = 8

function scope(record: CloudProjectBootstrapRecord): CloudProjectBootstrapScope {
  return {
    project_id: record.project_id, account_id: record.account_id,
    device_id: record.device_id, bootstrap_id: record.bootstrap_id,
  }
}

export class CloudProjectBootstrapCoordinator {
  private flight: { readonly key: string, readonly promise: Promise<CloudProjectBootstrapProgress> } | null = null

  constructor(
    private readonly auth: NormalUserAuthRuntime,
    private readonly repository: CloudProjectBootstrapRepository,
    private readonly workers: BootstrapWorkers,
  ) {}

  preflightLocalProject(projectId: string): Promise<Array<{ note_id: string, code: string }>> {
    return this.repository.preflight(projectId)
  }

  async reconcile(identity: BootstrapIdentity): Promise<CloudRegistryReconciliation> {
    const context = this.auth.requireContext()
    const [remoteResult, local] = await Promise.all([
      this.auth.authorized(token => cloudProjectsApi.listBootstraps(token)),
      this.repository.list(identity.localAccountId),
    ])
    this.assertCurrent(context)
    if (remoteResult.context.userId !== context.userId) throw new StaleAuthContextError()
    const localByProject = new Map(local.map(item => [item.project_id, item]))
    const remoteByProject = new Map(remoteResult.value.projects.map(item => [item.project_id, item]))
    const reasons: string[] = []
    for (const project of remoteResult.value.projects) {
      const match = localByProject.get(project.project_id)
      if (project.state === 'legacy' || project.bootstrap_id === null || project.origin_device_id === null) {
        reasons.push(`legacy:${project.project_id}`)
      } else if (!match) {
        reasons.push(`missing_local_binding:${project.project_id}`)
      } else if (match.bootstrap_id !== project.bootstrap_id || match.account_id !== identity.localAccountId) {
        reasons.push(`lineage_conflict:${project.project_id}`)
      } else if (match.device_id !== identity.deviceId) {
        reasons.push(`local_device_conflict:${project.project_id}`)
      } else if (match.phase === 'paused' || match.phase === 'blocked') {
        reasons.push(`${match.phase}:${project.project_id}`)
      } else if (project.state !== 'active') {
        reasons.push(`initializing:${project.project_id}`)
      } else if (!['captured', 'completing', 'ready'].includes(match.phase)) {
        reasons.push(`binding_not_ready:${project.project_id}`)
      }
    }
    for (const project of local) {
      if (!remoteByProject.has(project.project_id)) reasons.push(`missing_remote_registration:${project.project_id}`)
    }
    const cycleReasons = reasons.filter(reason => !reason.startsWith('initializing:'))
    const allRemoteActive = remoteResult.value.projects.every(project => project.state === 'active')
    const readyForCycle = cycleReasons.length === 0 && allRemoteActive
    return {
      readyForCycle,
      readyForNormalCycle: readyForCycle && local.every(project => project.phase === 'ready'),
      reasons: [...new Set(reasons)], remote: remoteResult.value.projects, local,
      currentCursor: remoteResult.value.current_cursor,
    }
  }

  async bootstrapLocalProject(
    identity: BootstrapIdentity,
    projectId: string,
    report?: CloudProjectBootstrapReporter,
  ): Promise<CloudProjectBootstrapProgress> {
    return this.runSingleFlight(
      `upload:${identity.localAccountId}:${identity.deviceId}:${projectId}`,
      () => this.bootstrapLocalProjectOnce(identity, projectId, report),
    )
  }

  async importRemoteProject(
    identity: BootstrapIdentity,
    projectId: string,
    displayName: string,
    report?: CloudProjectBootstrapReporter,
  ): Promise<CloudProjectBootstrapProgress> {
    return this.runSingleFlight(
      `import:${identity.localAccountId}:${identity.deviceId}:${projectId}`,
      () => this.importRemoteProjectOnce(identity, projectId, displayName, report),
    )
  }

  async setPaused(identity: BootstrapIdentity, projectId: string, paused: boolean): Promise<CloudRegistryReconciliation> {
    const context = this.auth.requireContext()
    const records = await this.repository.list(identity.localAccountId)
    this.assertCurrent(context)
    const project = records.find(item => item.project_id === projectId)
    if (!project || project.device_id !== identity.deviceId) {
      throw new CloudProjectBootstrapBlockedError('local_project_lineage_not_found')
    }
    await this.repository.setPaused(scope(project), paused)
    this.assertCurrent(context)
    return this.reconcile(identity)
  }

  async runReadyCycle(identity: BootstrapIdentity): Promise<NoteSyncOrchestratorResult> {
    const registry = await this.reconcile(identity)
    if (!registry.readyForNormalCycle) throw new CloudProjectBootstrapBlockedError(registry.reasons[0] ?? 'cloud_projects_not_connected')
    return this.workers.runOnce(identity.localAccountId, identity.deviceId)
  }

  private async bootstrapLocalProjectOnce(
    identity: BootstrapIdentity,
    projectId: string,
    report?: CloudProjectBootstrapReporter,
  ): Promise<CloudProjectBootstrapProgress> {
    const context = this.auth.requireContext()
    const issues = await this.repository.preflight(projectId)
    this.assertCurrent(context)
    if (issues.length) throw new CloudProjectBootstrapBlockedError(issues[0]!.code)
    let project = await this.repository.prepare(projectId, identity.localAccountId, identity.deviceId, 'upload_existing')
    this.assertCurrent(context)
    report?.('registering')
    await this.workers.registerDevice(identity.localAccountId, identity.deviceId)
    this.assertCurrent(context)
    const registration = await this.auth.authorized(token => cloudProjectsApi.registerBootstrap(token, projectId, {
      bootstrap_id: project.bootstrap_id, device_id: identity.deviceId,
    }))
    this.assertCurrent(context)
    project = await this.repository.confirmRegistration(
      scope(project), registration.value.project.state === 'active' ? 'active' : 'initializing',
      registration.value.current_cursor,
    )
    if (registration.value.project.state === 'initializing') {
      report?.('preparing_initial_notes')
      project = await this.repository.capture(scope(project))
    }

    for (let pass = 0; pass < MAX_BOOTSTRAP_UPLOAD_PASSES; pass += 1) {
      const cohort = await this.repository.cohort(scope(project))
      if (cohort.complete) break
      this.assertCurrent(context)
      report?.('uploading_initial_notes')
      await this.workers.sealOnce()
      this.assertCurrent(context)
      await this.workers.uploadOnce(identity.localAccountId)
    }
    const cohort = await this.repository.cohort(scope(project))
    if (!cohort.complete) {
      report?.('remaining_work')
      return { project, registry: await this.reconcile(identity), hasRemainingWork: true }
    }
    project = await this.repository.markCompleting(scope(project))
    report?.('completing_registration')
    const completion = await this.auth.authorized(token => cloudProjectsApi.completeBootstrap(token, projectId, {
      bootstrap_id: project.bootstrap_id, device_id: identity.deviceId,
      initial_event_count: cohort.event_count,
      initial_max_server_sequence: cohort.max_server_sequence,
    }))
    this.assertCurrent(context)
    project = await this.repository.confirmRegistration(scope(project), 'active', completion.value.current_cursor)
    const registry = await this.reconcile(identity)
    if (!registry.readyForCycle) {
      report?.('remaining_work')
      return { project, registry, hasRemainingWork: true }
    }
    report?.('pulling_remote_notes')
    const cycle = await this.workers.runOnce(identity.localAccountId, identity.deviceId)
    try { project = await this.repository.markReady(scope(project)) } catch { /* bounded cycle may need an exact retry */ }
    const hasRemainingWork = project.phase !== 'ready' || cycle.hasRemainingWork
    report?.(hasRemainingWork ? 'remaining_work' : 'initial_sync_completed')
    return { project, registry: await this.reconcile(identity), cycle, hasRemainingWork }
  }

  private async importRemoteProjectOnce(
    identity: BootstrapIdentity,
    projectId: string,
    displayName: string,
    report?: CloudProjectBootstrapReporter,
  ): Promise<CloudProjectBootstrapProgress> {
    const context = this.auth.requireContext()
    const remote = await this.auth.authorized(token => cloudProjectsApi.listBootstraps(token))
    this.assertCurrent(context)
    const descriptor = remote.value.projects.find(project => project.project_id === projectId)
    if (!descriptor || descriptor.state !== 'active' || !descriptor.bootstrap_id) {
      throw new CloudProjectBootstrapBlockedError('remote_project_not_active')
    }
    let project = await this.repository.importRemote(
      projectId, displayName, identity.localAccountId, identity.deviceId,
      descriptor.bootstrap_id, remote.value.current_cursor,
    )
    const registry = await this.reconcile(identity)
    if (!registry.readyForCycle) {
      report?.('remaining_work')
      return { project, registry, hasRemainingWork: true }
    }
    report?.('pulling_remote_notes')
    const cycle = await this.workers.runOnce(identity.localAccountId, identity.deviceId)
    try { project = await this.repository.markReady(scope(project)) } catch { /* retry after more bounded work */ }
    const hasRemainingWork = project.phase !== 'ready' || cycle.hasRemainingWork
    report?.(hasRemainingWork ? 'remaining_work' : 'initial_sync_completed')
    return { project, registry: await this.reconcile(identity), cycle, hasRemainingWork }
  }

  private async runSingleFlight(
    key: string,
    operation: () => Promise<CloudProjectBootstrapProgress>,
  ): Promise<CloudProjectBootstrapProgress> {
    if (this.flight?.key === key) return this.flight.promise
    if (this.flight) throw new CloudProjectBootstrapBlockedError('bootstrap_operation_in_progress')
    const promise = operation()
    this.flight = { key, promise }
    try {
      return await promise
    } finally {
      if (this.flight?.promise === promise) this.flight = null
    }
  }

  private assertCurrent(context: AuthContextSnapshot): void {
    if (!this.auth.isCurrent(context)) throw new StaleAuthContextError()
  }
}
