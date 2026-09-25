import { defineStore } from 'pinia'
import { computed, ref } from 'vue'

import type { CurrentUserCryptoRecord } from '@/api/accountCrypto'
import { ApiError } from '@/api/client'
import { projectsApi } from '@/api/projects'
import { StaleAuthContextError } from '@/auth/userAuth'
import {
  AccountCryptoAlreadyProvisionedError,
  AccountCryptoProvisioningConflictError,
  PendingAccountCryptoProvisioning,
} from '@/cloud/accountCryptoProvisioning'
import {
  CloudProjectBootstrapBlockedError,
  type CloudProjectBootstrapProgress,
  type CloudProjectBootstrapReporter,
  type CloudProjectBootstrapStage,
  type CloudRegistryReconciliation,
} from '@/cloud/projectBootstrap'
import { NoteSyncRuntime, type NoteSyncRuntimeUnlockResult } from '@/cloud/noteSyncRuntime'
import type { NoteSyncOrchestratorResult } from '@/cloud/noteSyncOrchestrator'
import { canEnableCloudProjectSync } from '@/cloud/capabilities'
import type { CloudProjectBootstrapRecord } from '@/infrastructure/sqlite/cloudProjectBootstrapRepository'
import { currentPlatform } from '@/platform/runtime'

export type CloudSessionStatus =
  | 'unavailable'
  | 'logged_out'
  | 'provisioning'
  | 'key_locked'
  | 'ready'
  | 'syncing'
  | 'completed'
  | 'retryable_error'
  | 'blocked'
  | 'remaining_work'

export type CloudProjectUiStatus =
  | 'local_only'
  | 'unsupported'
  | 'import_available'
  | 'registering'
  | 'preparing_initial_notes'
  | 'uploading_initial_notes'
  | 'completing_registration'
  | 'pulling_remote_notes'
  | 'initial_sync_completed'
  | 'remaining_work'
  | 'paused'
  | 'blocked'

export interface CloudProjectView {
  readonly projectId: string
  readonly name: string | null
  readonly origin: 'local' | 'remote'
  readonly status: CloudProjectUiStatus
  readonly connectionAvailable: boolean
  readonly mode: 'upload_existing' | 'import_remote' | null
  readonly reason: string | null
}

interface LocalProjectSummary {
  readonly id: string
  readonly name: string
}

export interface CloudSessionRuntime {
  login(username: string, password: string): Promise<{ context: { username: string } }>
  cryptoRecord(): Promise<CurrentUserCryptoRecord>
  beginCryptoProvisioning(encryptionPassword: string): Promise<PendingAccountCryptoProvisioning>
  submitCryptoProvisioning(pending: PendingAccountCryptoProvisioning): Promise<CurrentUserCryptoRecord>
  reconcileCryptoProvisioning(pending: PendingAccountCryptoProvisioning): Promise<CurrentUserCryptoRecord | null>
  unlock(passphrase: string): Promise<NoteSyncRuntimeUnlockResult>
  reconcileProjects(): Promise<CloudRegistryReconciliation>
  preflightLocalProject(projectId: string): Promise<Array<{ note_id: string, code: string }>>
  bootstrapLocalProject(projectId: string, report?: CloudProjectBootstrapReporter): Promise<CloudProjectBootstrapProgress>
  importRemoteProject(projectId: string, displayName: string, report?: CloudProjectBootstrapReporter): Promise<CloudProjectBootstrapProgress>
  setProjectPaused(projectId: string, paused: boolean): Promise<CloudRegistryReconciliation>
  retry(): Promise<NoteSyncOrchestratorResult>
  lock(): Promise<void>
  logout(): Promise<void>
  dispose(): Promise<void>
}

let runtimeFactory: () => CloudSessionRuntime = () => new NoteSyncRuntime()
let projectLoader: () => Promise<LocalProjectSummary[]> = async () => (
  (await projectsApi.list({})).map(project => ({ id: project.id, name: project.name }))
)

/** Test-only injection; production continues to construct the single runtime directly. */
export function configureCloudSessionRuntimeFactoryForTests(factory: (() => CloudSessionRuntime) | null): void {
  runtimeFactory = factory ?? (() => new NoteSyncRuntime())
}

/** Test-only injection for the existing platform project reader. */
export function configureCloudSessionProjectLoaderForTests(loader: (() => Promise<LocalProjectSummary[]>) | null): void {
  projectLoader = loader ?? (async () => (await projectsApi.list({})).map(project => ({ id: project.id, name: project.name })))
}

function safeErrorMessage(error: unknown): string {
  if (error instanceof AccountCryptoProvisioningConflictError) {
    return 'Запись шифрования уже существует и отличается от подготовленной. Перезапись запрещена.'
  }
  if (error instanceof AccountCryptoAlreadyProvisionedError) {
    return 'Для этого аккаунта уже настроено шифрование. Разблокируйте существующий ключ.'
  }
  if (error instanceof CloudProjectBootstrapBlockedError) return safeBootstrapReason(error.code)
  if (error instanceof ApiError && error.status === 0) return 'Не удалось связаться с сервером. Можно безопасно повторить операцию.'
  if (error instanceof ApiError && error.status === 401) return 'Сеанс аккаунта истёк. Войдите снова.'
  if (error instanceof StaleAuthContextError) return 'Сеанс аккаунта изменился. Войдите снова.'
  return 'Операция облачной синхронизации не завершена. Повторите её после проверки подключения.'
}

function safeBootstrapReason(code: string): string {
  if (code === 'dependency_not_synced' || code === 'unsupported_content_format') {
    return 'Проект содержит заметки, которые C16 пока не поддерживает. Подключение целого проекта остановлено.'
  }
  if (code === 'missing_created_at' || code === 'invalid_created_at'
    || code === 'missing_updated_at' || code === 'invalid_updated_at' || code === 'invalid_note_payload') {
    return 'Некоторые заметки проекта имеют несовместимые данные. Подключение остановлено без отправки на сервер.'
  }
  if (code === 'remote_project_not_active') return 'Удалённый проект ещё не готов для безопасного импорта.'
  if (code === 'bootstrap_operation_in_progress') return 'Другая операция подключения уже выполняется. Дождитесь её завершения.'
  if (code === 'local_project_lineage_not_found') return 'Локальное подтверждение происхождения проекта не найдено.'
  return 'Проект заблокирован проверкой безопасности. Данные не изменены; повторите после устранения причины.'
}

function safeRegistryReason(reason: string): string {
  const kind = reason.split(':', 1)[0] ?? ''
  const messages: Record<string, string> = {
    legacy: 'В аккаунте есть облачный проект с устаревшим или неизвестным состоянием.',
    missing_local_binding: 'Удалённый проект ещё не импортирован на это устройство.',
    lineage_conflict: 'Происхождение локального и удалённого проекта не совпадает.',
    local_device_conflict: 'Локальная привязка проекта принадлежит другому устройству.',
    paused: 'Один из облачных проектов приостановлен.',
    blocked: 'Один из облачных проектов заблокирован.',
    initializing: 'Первоначальное подключение одного из проектов ещё не завершено.',
    binding_not_ready: 'Локальная привязка облачного проекта ещё не готова.',
    missing_remote_registration: 'Для локальной привязки не найдена подтверждённая серверная регистрация.',
  }
  return messages[kind] ?? 'Проверка реестра облачных проектов не завершена.'
}

function isAuthenticationFailure(error: unknown): boolean {
  return (error instanceof ApiError && error.status === 401) || error instanceof StaleAuthContextError
}

function statusForRecord(record: CloudProjectBootstrapRecord): CloudProjectUiStatus {
  if (record.phase === 'prepared') return 'registering'
  if (record.phase === 'registered') return 'preparing_initial_notes'
  if (record.phase === 'captured') return 'uploading_initial_notes'
  if (record.phase === 'completing') return 'completing_registration'
  if (record.phase === 'ready') return 'initial_sync_completed'
  if (record.phase === 'paused') return 'paused'
  return 'blocked'
}

export const useCloudSessionStore = defineStore('cloud-session', () => {
  // Runtime, key material, server bootstrap tokens and pending Recovery Key are
  // lexical-only. Pinia exposes only redacted account/project presentation data.
  let runtime: CloudSessionRuntime | null = null
  let pending: PendingAccountCryptoProvisioning | null = null
  let syncFlight: { readonly epoch: number, readonly promise: Promise<void> } | null = null
  let projectFlight: { readonly epoch: number, readonly promise: Promise<void> } | null = null
  let lifecycleEpoch = 0

  const supported = ref(false)
  const status = ref<CloudSessionStatus>('unavailable')
  const username = ref<string | null>(null)
  const hasProvisionedKey = ref(false)
  const errorMessage = ref<string | null>(null)
  const blockedEvents = ref<readonly string[]>([])
  const hasRemainingWork = ref(false)
  const lastCycleAt = ref<string | null>(null)
  const busy = ref(false)
  const projects = ref<CloudProjectView[]>([])
  const canRunCycle = ref(false)
  const projectBootstrapEnabled = canEnableCloudProjectSync()
  const authenticated = computed(() => username.value !== null)

  function resetVisibleSession(): void {
    username.value = null
    hasProvisionedKey.value = false
    errorMessage.value = null
    blockedEvents.value = []
    hasRemainingWork.value = false
    lastCycleAt.value = null
    projects.value = []
    canRunCycle.value = false
  }

  function clearPending(): void {
    pending?.dispose()
    pending = null
  }

  function requireRuntime(): CloudSessionRuntime {
    if (runtime === null) throw new Error('Desktop cloud session is unavailable.')
    return runtime
  }

  function current(epoch: number): boolean {
    return lifecycleEpoch === epoch
  }

  function setFailure(error: unknown, epoch = lifecycleEpoch): void {
    if (!current(epoch)) return
    errorMessage.value = safeErrorMessage(error)
    hasRemainingWork.value = false
    if (isAuthenticationFailure(error)) {
      lifecycleEpoch += 1
      clearPending()
      resetVisibleSession()
      busy.value = false
      status.value = 'logged_out'
      return
    }
    status.value = error instanceof AccountCryptoProvisioningConflictError
      || error instanceof CloudProjectBootstrapBlockedError ? 'blocked' : 'retryable_error'
  }

  function initialize(): void {
    if (currentPlatform() !== 'tauri') {
      supported.value = false
      status.value = 'unavailable'
      return
    }
    supported.value = true
    if (runtime === null) runtime = runtimeFactory()
    if (status.value === 'unavailable') status.value = 'logged_out'
  }

  async function login(accountUsername: string, accountPassword: string): Promise<void> {
    const activeRuntime = requireRuntime()
    const epoch = ++lifecycleEpoch
    busy.value = true
    errorMessage.value = null
    clearPending()
    projects.value = []
    try {
      const result = await activeRuntime.login(accountUsername, accountPassword)
      if (!current(epoch)) return
      username.value = result.context.username
      const record = await activeRuntime.cryptoRecord()
      if (!current(epoch)) return
      hasProvisionedKey.value = record.provisioned
      status.value = record.provisioned ? 'key_locked' : 'provisioning'
    } catch (error) {
      setFailure(error, epoch)
      throw error
    } finally {
      if (current(epoch)) busy.value = false
    }
  }

  async function prepareProvisioning(encryptionPassword: string): Promise<Uint8Array> {
    const activeRuntime = requireRuntime()
    if (status.value !== 'provisioning' || pending !== null) throw new Error('Encryption provisioning is not available.')
    const epoch = lifecycleEpoch
    busy.value = true
    errorMessage.value = null
    try {
      const prepared = await activeRuntime.beginCryptoProvisioning(encryptionPassword)
      if (!current(epoch)) {
        prepared.dispose()
        throw new StaleAuthContextError()
      }
      pending = prepared
      return prepared.recoveryKeyForDisplay()
    } catch (error) {
      setFailure(error, epoch)
      if (current(epoch) && !isAuthenticationFailure(error) && pending === null) status.value = 'provisioning'
      throw error
    } finally {
      if (current(epoch)) busy.value = false
    }
  }

  async function submitProvisioning(): Promise<void> {
    const activePending = pending
    if (activePending === null) throw new Error('Encryption provisioning is not available.')
    const epoch = lifecycleEpoch
    busy.value = true
    errorMessage.value = null
    try {
      activePending.confirmRecoveryKeySaved()
      await requireRuntime().submitCryptoProvisioning(activePending)
      if (!current(epoch)) return
      pending = null
      hasProvisionedKey.value = true
      status.value = 'key_locked'
    } catch (error) {
      setFailure(error, epoch)
      if (current(epoch) && !(error instanceof AccountCryptoProvisioningConflictError) && pending === activePending) status.value = 'provisioning'
      throw error
    } finally {
      if (current(epoch)) busy.value = false
    }
  }

  async function reconcileProvisioning(): Promise<boolean> {
    const activePending = pending
    if (activePending === null) return false
    const epoch = lifecycleEpoch
    busy.value = true
    errorMessage.value = null
    try {
      const record = await requireRuntime().reconcileCryptoProvisioning(activePending)
      if (!current(epoch) || record === null) return false
      pending = null
      hasProvisionedKey.value = true
      status.value = 'key_locked'
      return true
    } catch (error) {
      setFailure(error, epoch)
      throw error
    } finally {
      if (current(epoch)) busy.value = false
    }
  }

  function cancelProvisioning(): void {
    clearPending()
    errorMessage.value = null
    if (username.value !== null) status.value = hasProvisionedKey.value ? 'key_locked' : 'provisioning'
  }

  function applyCycle(result: NoteSyncOrchestratorResult, epoch: number): void {
    if (!current(epoch)) return
    blockedEvents.value = result.blocked.map(() => 'Есть зашифрованное событие, требующее отдельного безопасного решения.')
    hasRemainingWork.value = result.hasRemainingWork
    lastCycleAt.value = new Date().toISOString()
    if (result.blocked.length > 0) status.value = 'blocked'
    else if (result.errors.length > 0) status.value = 'retryable_error'
    else if (result.hasRemainingWork) status.value = 'remaining_work'
    else status.value = 'completed'
  }

  async function runCycle(operation: () => Promise<NoteSyncOrchestratorResult>): Promise<void> {
    const epoch = lifecycleEpoch
    if (syncFlight?.epoch === epoch) return syncFlight.promise
    status.value = 'syncing'
    errorMessage.value = null
    let promise!: Promise<void>
    promise = (async () => {
      try {
        const result = await operation()
        if (current(epoch)) await refreshProjects()
        applyCycle(result, epoch)
      } catch (error) {
        setFailure(error, epoch)
        throw error
      } finally {
        if (syncFlight?.promise === promise) syncFlight = null
      }
    })()
    syncFlight = { epoch, promise }
    return promise
  }

  async function unlock(encryptionPassword: string): Promise<void> {
    const epoch = lifecycleEpoch
    busy.value = true
    errorMessage.value = null
    try {
      const result = await requireRuntime().unlock(encryptionPassword)
      if (!current(epoch)) return
      await applyRegistry(result.registry, epoch)
      status.value = result.registry.readyForNormalCycle ? 'ready' : 'blocked'
    } catch (error) {
      setFailure(error, epoch)
      throw error
    } finally {
      if (current(epoch)) busy.value = false
    }
  }

  async function applyRegistry(registry: CloudRegistryReconciliation, epoch: number): Promise<void> {
    const localProjects = await projectLoader()
    if (!current(epoch)) return
    const localById = new Map(localProjects.map(project => [project.id, project]))
    const recordById = new Map(registry.local.map(record => [record.project_id, record]))
    const remoteById = new Map(registry.remote.map(project => [project.project_id, project]))
    const next: CloudProjectView[] = []

    for (const project of localProjects) {
      const record = recordById.get(project.id)
      const remote = remoteById.get(project.id)
      if (record) {
        next.push({
          projectId: project.id, name: project.name, origin: 'local',
          status: statusForRecord(record), connectionAvailable: false,
          mode: record.mode, reason: record.blocked_reason === null ? null : safeBootstrapReason(record.blocked_reason),
        })
        continue
      }
      if (remote) {
        next.push({
          projectId: project.id, name: project.name, origin: 'local', status: 'blocked',
          connectionAvailable: false, mode: null,
          reason: 'На устройстве уже есть проект с таким ID, но его общая история с облаком не подтверждена. Импорт и объединение запрещены.',
        })
        continue
      }
      let issues: Array<{ note_id: string, code: string }> = []
      try {
        issues = await requireRuntime().preflightLocalProject(project.id)
      } catch (error) {
        if (isAuthenticationFailure(error)) throw error
        issues = [{ note_id: '', code: 'invalid_note_payload' }]
      }
      if (!current(epoch)) return
      next.push({
        projectId: project.id, name: project.name, origin: 'local',
        status: issues.length ? 'unsupported' : 'local_only',
        connectionAvailable: issues.length === 0, mode: null,
        reason: issues.length ? safeBootstrapReason(issues[0]!.code) : null,
      })
    }

    for (const remote of registry.remote) {
      if (recordById.has(remote.project_id) || localById.has(remote.project_id)) continue
      const importAvailable = remote.state === 'active' && remote.bootstrap_id !== null
      next.push({
        projectId: remote.project_id, name: null, origin: 'remote',
        status: importAvailable ? 'import_available' : 'blocked',
        connectionAvailable: importAvailable, mode: 'import_remote',
        reason: importAvailable ? null : remote.state === 'legacy'
          ? 'Удалённый проект имеет устаревшее или неизвестное состояние. Безопасный импорт недоступен.'
          : 'Первоначальное подключение удалённого проекта выполняется на другом устройстве.',
      })
    }

    projects.value = next.sort((left, right) => (left.name ?? left.projectId).localeCompare(right.name ?? right.projectId))
    blockedEvents.value = [...new Set(registry.reasons.map(safeRegistryReason))]
    canRunCycle.value = registry.readyForNormalCycle
    hasRemainingWork.value = !registry.readyForNormalCycle
  }

  async function refreshProjects(): Promise<void> {
    const epoch = lifecycleEpoch
    try {
      const registry = await requireRuntime().reconcileProjects()
      if (!current(epoch)) return
      await applyRegistry(registry, epoch)
    } catch (error) {
      setFailure(error, epoch)
      throw error
    }
  }

  async function prepareProjectConnection(projectId: string): Promise<boolean> {
    if (!projectBootstrapEnabled) return false
    const epoch = lifecycleEpoch
    errorMessage.value = null
    const issues = await requireRuntime().preflightLocalProject(projectId)
    if (!current(epoch)) return false
    if (issues.length) {
      const reason = safeBootstrapReason(issues[0]!.code)
      projects.value = projects.value.map(project => project.projectId === projectId
        ? { ...project, status: 'unsupported', connectionAvailable: false, reason }
        : project)
      return false
    }
    return true
  }

  function setProjectStage(projectId: string, stage: CloudProjectBootstrapStage, epoch: number): void {
    if (!current(epoch)) return
    projects.value = projects.value.map(project => project.projectId === projectId
      ? { ...project, status: stage, connectionAvailable: false, reason: null }
      : project)
  }

  async function runProjectOperation(
    projectId: string,
    operation: (report: CloudProjectBootstrapReporter) => Promise<CloudProjectBootstrapProgress>,
  ): Promise<void> {
    const epoch = lifecycleEpoch
    if (projectFlight?.epoch === epoch) return projectFlight.promise
    busy.value = true
    errorMessage.value = null
    const report: CloudProjectBootstrapReporter = stage => setProjectStage(projectId, stage, epoch)
    let promise!: Promise<void>
    promise = (async () => {
      try {
        const result = await operation(report)
        if (!current(epoch)) return
        await applyRegistry(result.registry, epoch)
        if (result.cycle) applyCycle(result.cycle, epoch)
        if (result.hasRemainingWork) setProjectStage(projectId, 'remaining_work', epoch)
        else setProjectStage(projectId, 'initial_sync_completed', epoch)
      } catch (error) {
        setFailure(error, epoch)
        if (current(epoch)) {
          projects.value = projects.value.map(project => project.projectId === projectId
            ? { ...project, status: 'blocked', connectionAvailable: false, reason: safeErrorMessage(error) }
            : project)
        }
        throw error
      } finally {
        if (projectFlight?.promise === promise) projectFlight = null
        if (current(epoch)) busy.value = false
      }
    })()
    projectFlight = { epoch, promise }
    return promise
  }

  async function bootstrapProject(projectId: string): Promise<void> {
    if (!projectBootstrapEnabled) throw new CloudProjectBootstrapBlockedError('project_bootstrap_disabled')
    await runProjectOperation(projectId, report => requireRuntime().bootstrapLocalProject(projectId, report))
  }

  async function importProject(projectId: string, displayName: string): Promise<void> {
    if (!projectBootstrapEnabled) throw new CloudProjectBootstrapBlockedError('project_bootstrap_disabled')
    if (displayName.trim().length === 0) throw new Error('A local project name is required.')
    await runProjectOperation(projectId, report => requireRuntime().importRemoteProject(projectId, displayName.trim(), report))
  }

  async function resumeProject(projectId: string): Promise<void> {
    const project = projects.value.find(item => item.projectId === projectId)
    if (!project) throw new Error('Cloud project is unavailable.')
    if (project.status === 'paused') {
      const epoch = lifecycleEpoch
      const registry = await requireRuntime().setProjectPaused(projectId, false)
      if (current(epoch)) await applyRegistry(registry, epoch)
      return
    }
    if (project.mode === 'import_remote') {
      if (!project.name) throw new Error('Imported project name is unavailable.')
      return importProject(projectId, project.name)
    }
    return bootstrapProject(projectId)
  }

  async function pauseProject(projectId: string): Promise<void> {
    const epoch = lifecycleEpoch
    const registry = await requireRuntime().setProjectPaused(projectId, true)
    if (current(epoch)) await applyRegistry(registry, epoch)
  }

  async function retry(): Promise<void> {
    if (!hasProvisionedKey.value) throw new Error('Encryption provisioning is required before sync.')
    await runCycle(() => requireRuntime().retry())
  }

  async function lock(): Promise<void> {
    const epoch = ++lifecycleEpoch
    clearPending()
    try {
      await requireRuntime().lock()
    } finally {
      if (current(epoch)) {
        blockedEvents.value = []
        hasRemainingWork.value = false
        errorMessage.value = null
        projects.value = []
        canRunCycle.value = false
        busy.value = false
        if (username.value !== null) status.value = 'key_locked'
      }
    }
  }

  async function logout(): Promise<void> {
    const epoch = ++lifecycleEpoch
    clearPending()
    try {
      await runtime?.logout()
    } finally {
      if (current(epoch)) {
        resetVisibleSession()
        busy.value = false
        status.value = supported.value ? 'logged_out' : 'unavailable'
      }
    }
  }

  async function dispose(): Promise<void> {
    ++lifecycleEpoch
    clearPending()
    syncFlight = null
    projectFlight = null
    const activeRuntime = runtime
    runtime = null
    await activeRuntime?.dispose()
    resetVisibleSession()
    busy.value = false
    status.value = supported.value ? 'logged_out' : 'unavailable'
  }

  return {
    supported, status, username, hasProvisionedKey, errorMessage, blockedEvents,
    hasRemainingWork, lastCycleAt, busy, authenticated, projects, canRunCycle,
    projectBootstrapEnabled,
    initialize, login, prepareProvisioning, submitProvisioning, reconcileProvisioning,
    cancelProvisioning, unlock, refreshProjects, prepareProjectConnection,
    bootstrapProject, importProject, resumeProject, pauseProject,
    retry, lock, logout, dispose,
  }
})
