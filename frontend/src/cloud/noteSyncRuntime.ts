import { AuthoritativeAccountBinding } from '@/auth/accountBinding'
import { KeyNotProvisionedError, RuntimeKeyContext, type AuthoritativeKeyContextLease } from '@/auth/keyContext'
import { NormalUserAuthRuntime, StaleAuthContextError, type AuthContextSnapshot } from '@/auth/userAuth'
import { SQLiteCloudAccountBindingRepository, type CloudAccountBindingRepository } from '@/infrastructure/sqlite/cloudAccountBindingRepository'
import { SQLiteCloudIdentityRepository, type CloudIdentity, type CloudIdentityRepository } from '@/infrastructure/sqlite/cloudIdentityRepository'
import { SQLiteCloudProjectBootstrapRepository } from '@/infrastructure/sqlite/cloudProjectBootstrapRepository'
import { SQLiteNoteSyncAckRepository } from '@/infrastructure/sqlite/noteSyncAckRepository'
import { SQLiteNoteSyncInboxRepository } from '@/infrastructure/sqlite/noteSyncInboxRepository'
import { SQLiteNoteSyncIntentRepository } from '@/infrastructure/sqlite/noteSyncIntentRepository'
import { SQLiteNoteSyncOutboxRepository } from '@/infrastructure/sqlite/noteSyncOutboxRepository'
import { SQLiteNoteSyncRemoteApplyRepository } from '@/infrastructure/sqlite/noteSyncRemoteApplyRepository'
import { NoteSyncDeviceAckAdapter } from './noteSyncDeviceAck'
import { accountCryptoApi, type CurrentUserCryptoRecord } from '@/api/accountCrypto'
import { PendingAccountCryptoProvisioning } from './accountCryptoProvisioning'
import { NoteSyncInboxRemoteApplier } from './noteSyncInboxApply'
import { DurableNoteSyncInbox } from './noteSyncInbox'
import { NoteSyncOrchestrator, type NoteSyncOrchestratorOptions, type NoteSyncOrchestratorResult } from './noteSyncOrchestrator'
import { NoteSyncPuller } from './noteSyncPull'
import { NoteSyncUploader } from './noteSyncUpload'
import { sealPendingNoteSyncIntents } from './noteSyncIntent'
import {
  CloudProjectBootstrapCoordinator,
  type CloudProjectBootstrapReporter,
  type CloudProjectBootstrapProgress,
  type CloudRegistryReconciliation,
} from './projectBootstrap'

const CANONICAL_UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/

interface NoteSyncRunner {
  runOnce(localAccountId: string, deviceId: string, options?: NoteSyncOrchestratorOptions): Promise<NoteSyncOrchestratorResult>
}

interface RuntimeKeyManager {
  unlockWithPassphrase(localAccountId: string, passphrase: string): Promise<AuthoritativeKeyContextLease>
  leaseForAccount(localAccountId: string): AuthoritativeKeyContextLease | null
  lock(): Promise<void>
  dispose(): Promise<void>
}

interface ProjectBootstrapGate {
  reconcile(identity: { localAccountId: string, deviceId: string }): Promise<CloudRegistryReconciliation>
  preflightLocalProject(projectId: string): Promise<Array<{ note_id: string, code: string }>>
  runReadyCycle(identity: { localAccountId: string, deviceId: string }): Promise<NoteSyncOrchestratorResult>
  bootstrapLocalProject(identity: { localAccountId: string, deviceId: string }, projectId: string, report?: CloudProjectBootstrapReporter): Promise<CloudProjectBootstrapProgress>
  importRemoteProject(identity: { localAccountId: string, deviceId: string }, projectId: string, displayName: string, report?: CloudProjectBootstrapReporter): Promise<CloudProjectBootstrapProgress>
  setPaused(identity: { localAccountId: string, deviceId: string }, projectId: string, paused: boolean): Promise<CloudRegistryReconciliation>
}

export interface NoteSyncRuntimeDependencies {
  readonly auth?: NormalUserAuthRuntime
  readonly identityRepository?: CloudIdentityRepository
  readonly bindingRepository?: CloudAccountBindingRepository
  readonly bindings?: AuthoritativeAccountBinding
  readonly keys?: RuntimeKeyManager
  readonly orchestrator?: NoteSyncRunner
  readonly bootstrap?: ProjectBootstrapGate
}

export interface NoteSyncRuntimeLoginResult {
  readonly context: AuthContextSnapshot
  readonly identity: CloudIdentity
}

export interface NoteSyncRuntimeUnlockResult {
  readonly identity: CloudIdentity
  readonly registry: CloudRegistryReconciliation
}

export class CloudIdentityUnavailableError extends Error {
  readonly name = 'CloudIdentityUnavailableError'
}

export class NoteSyncRuntimeDisposedError extends Error {
  readonly name = 'NoteSyncRuntimeDisposedError'
}

/**
 * Headless normal-user session composition. It is deliberately not connected
 * to desktop startup, UI, scheduler, or legacy document synchronization.
 */
export class NoteSyncRuntime {
  private readonly auth: NormalUserAuthRuntime
  private readonly identityRepository: CloudIdentityRepository
  private readonly bindings: AuthoritativeAccountBinding
  private readonly keys: RuntimeKeyManager
  private readonly orchestrator: NoteSyncRunner
  private readonly bootstrap: ProjectBootstrapGate
  private flight: { readonly key: string, readonly promise: Promise<NoteSyncOrchestratorResult> } | null = null
  private disposed = false

  constructor(dependencies: NoteSyncRuntimeDependencies = {}) {
    this.auth = dependencies.auth ?? new NormalUserAuthRuntime()
    this.identityRepository = dependencies.identityRepository ?? new SQLiteCloudIdentityRepository()
    const bindingRepository = dependencies.bindingRepository ?? new SQLiteCloudAccountBindingRepository()
    this.bindings = dependencies.bindings ?? new AuthoritativeAccountBinding(this.auth, bindingRepository)
    this.keys = dependencies.keys ?? new RuntimeKeyContext(this.auth, this.bindings)
    const composition = this.composeSync(dependencies.orchestrator)
    this.orchestrator = composition.orchestrator
    this.bootstrap = dependencies.bootstrap ?? composition.bootstrap
  }

  async login(username: string, password: string): Promise<NoteSyncRuntimeLoginResult> {
    this.assertNotDisposed()
    const context = await this.auth.login(username, password)
    const identity = await this.provisionFor(context)
    return { context, identity }
  }

  /** Reads the authenticated user's immutable E2EE bootstrap record. */
  async cryptoRecord(): Promise<CurrentUserCryptoRecord> {
    this.assertNotDisposed()
    return (await this.auth.authorized(accessToken => accountCryptoApi.get(accessToken))).value
  }

  /** Starts a transient first-provisioning context without exposing auth tokens. */
  async beginCryptoProvisioning(encryptionPassword: string): Promise<PendingAccountCryptoProvisioning> {
    this.assertNotDisposed()
    return PendingAccountCryptoProvisioning.begin(this.auth, encryptionPassword)
  }

  async submitCryptoProvisioning(pending: PendingAccountCryptoProvisioning): Promise<CurrentUserCryptoRecord> {
    this.assertNotDisposed()
    return pending.submit(this.auth)
  }

  async reconcileCryptoProvisioning(pending: PendingAccountCryptoProvisioning): Promise<CurrentUserCryptoRecord | null> {
    this.assertNotDisposed()
    return pending.reconcile(this.auth)
  }

  /** Unlocks an existing wrapped AMK without starting pull, upload, or ACK. */
  async unlock(passphrase: string): Promise<NoteSyncRuntimeUnlockResult> {
    this.assertNotDisposed()
    const context = this.auth.requireContext()
    const identity = await this.readFor(context)
    const lease = await this.keys.unlockWithPassphrase(identity.local_account_id, passphrase)
    this.assertLease(context, identity, lease)
    return { identity, registry: await this.bootstrap.reconcile(this.bootstrapIdentity(identity)) }
  }

  async retry(options?: NoteSyncOrchestratorOptions): Promise<NoteSyncOrchestratorResult> {
    this.assertNotDisposed()
    const context = this.auth.requireContext()
    const identity = await this.readFor(context)
    return this.runFor(context, identity, options)
  }

  async reconcileProjects(): Promise<CloudRegistryReconciliation> {
    this.assertNotDisposed()
    const context = this.auth.requireContext()
    const identity = await this.readFor(context)
    this.assertUnlocked(context, identity)
    return this.bootstrap.reconcile(this.bootstrapIdentity(identity))
  }

  async preflightLocalProject(projectId: string): Promise<Array<{ note_id: string, code: string }>> {
    this.assertNotDisposed()
    const context = this.auth.requireContext()
    const identity = await this.readFor(context)
    this.assertUnlocked(context, identity)
    const issues = await this.bootstrap.preflightLocalProject(projectId)
    this.assertCurrent(context)
    return issues
  }

  async bootstrapLocalProject(projectId: string, report?: CloudProjectBootstrapReporter): Promise<CloudProjectBootstrapProgress> {
    this.assertNotDisposed()
    const context = this.auth.requireContext()
    const identity = await this.readFor(context)
    this.assertUnlocked(context, identity)
    return this.bootstrap.bootstrapLocalProject(this.bootstrapIdentity(identity), projectId, report)
  }

  async importRemoteProject(projectId: string, displayName: string, report?: CloudProjectBootstrapReporter): Promise<CloudProjectBootstrapProgress> {
    this.assertNotDisposed()
    const context = this.auth.requireContext()
    const identity = await this.readFor(context)
    this.assertUnlocked(context, identity)
    return this.bootstrap.importRemoteProject(this.bootstrapIdentity(identity), projectId, displayName, report)
  }

  async setProjectPaused(projectId: string, paused: boolean): Promise<CloudRegistryReconciliation> {
    this.assertNotDisposed()
    const context = this.auth.requireContext()
    const identity = await this.readFor(context)
    this.assertUnlocked(context, identity)
    return this.bootstrap.setPaused(this.bootstrapIdentity(identity), projectId, paused)
  }

  async lock(): Promise<void> {
    this.assertNotDisposed()
    await this.keys.lock()
  }

  async logout(): Promise<void> {
    this.assertNotDisposed()
    // auth invalidation invokes RuntimeKeyContext.lock() and drains existing uses.
    await this.auth.logout()
  }

  async dispose(): Promise<void> {
    if (this.disposed) return
    this.disposed = true
    await this.keys.dispose()
  }

  private composeSync(injected?: NoteSyncRunner): { orchestrator: NoteSyncRunner, bootstrap: ProjectBootstrapGate } {
    const intents = new SQLiteNoteSyncIntentRepository()
    const outbox = new SQLiteNoteSyncOutboxRepository()
    const inboxRepository = new SQLiteNoteSyncInboxRepository()
    const puller = new NoteSyncPuller(this.auth, this.bindings)
    const inbox = new DurableNoteSyncInbox(this.auth, this.bindings, puller, inboxRepository)
    const applier = new NoteSyncInboxRemoteApplier(
      this.auth, this.bindings, this.keys as RuntimeKeyContext, inboxRepository, new SQLiteNoteSyncRemoteApplyRepository(),
    )
    const uploader = new NoteSyncUploader(this.auth, this.bindings, outbox)
    const deviceAck = new NoteSyncDeviceAckAdapter(this.auth, this.bindings, new SQLiteNoteSyncAckRepository())
    const orchestrator = injected ?? new NoteSyncOrchestrator(
      this.auth, this.keys as RuntimeKeyContext, intents, uploader, inbox, applier, deviceAck,
    )
    const bootstrap = new CloudProjectBootstrapCoordinator(
      this.auth,
      new SQLiteCloudProjectBootstrapRepository(),
      {
        registerDevice: (localAccountId, deviceId) => deviceAck.registerOnce(localAccountId, deviceId),
        sealOnce: () => sealPendingNoteSyncIntents(intents, this.keys as RuntimeKeyContext),
        uploadOnce: localAccountId => uploader.uploadOnce(localAccountId),
        runOnce: (localAccountId, deviceId) => orchestrator.runOnce(localAccountId, deviceId),
      },
    )
    return { orchestrator, bootstrap }
  }

  private async provisionFor(context: AuthContextSnapshot): Promise<CloudIdentity> {
    const identity = await this.identityRepository.provision(context.userId)
    this.assertCurrent(context)
    this.assertIdentity(identity)
    const binding = await this.bindings.ensureForCurrentUser(identity.local_account_id)
    if (binding.context.userId !== context.userId || binding.context.authEpoch !== context.authEpoch) throw new StaleAuthContextError()
    this.assertCurrent(context)
    return identity
  }

  private async readFor(context: AuthContextSnapshot): Promise<CloudIdentity> {
    const identity = await this.identityRepository.read(context.userId)
    this.assertCurrent(context)
    if (identity === null) throw new CloudIdentityUnavailableError('No durable cloud identity is provisioned for this user.')
    this.assertIdentity(identity)
    const binding = await this.bindings.ensureForCurrentUser(identity.local_account_id)
    if (binding.context.userId !== context.userId || binding.context.authEpoch !== context.authEpoch) throw new StaleAuthContextError()
    this.assertCurrent(context)
    return identity
  }

  private async runFor(context: AuthContextSnapshot, identity: CloudIdentity, options?: NoteSyncOrchestratorOptions): Promise<NoteSyncOrchestratorResult> {
    const lease = this.keys.leaseForAccount(identity.local_account_id)
    if (lease === null) throw new KeyNotProvisionedError()
    this.assertLease(context, identity, lease)
    const key = `${context.userId}\u0000${context.authEpoch}\u0000${identity.local_account_id}\u0000${identity.device_id}\u0000${lease.keyContextId}\u0000${lease.keyEpoch}`
    if (this.flight?.key === key) return this.flight.promise
    const promise = options === undefined
      ? this.bootstrap.runReadyCycle(this.bootstrapIdentity(identity))
      : this.runGatedWithOptions(identity, options)
    this.flight = { key, promise }
    try {
      return await promise
    } finally {
      if (this.flight?.promise === promise) this.flight = null
    }
  }

  private async runGatedWithOptions(identity: CloudIdentity, options: NoteSyncOrchestratorOptions): Promise<NoteSyncOrchestratorResult> {
    const bootstrapIdentity = this.bootstrapIdentity(identity)
    const registry = await this.bootstrap.reconcile(bootstrapIdentity)
    if (!registry.readyForNormalCycle) return this.bootstrap.runReadyCycle(bootstrapIdentity)
    return this.orchestrator.runOnce(identity.local_account_id, identity.device_id, options)
  }

  private assertUnlocked(context: AuthContextSnapshot, identity: CloudIdentity): void {
    const lease = this.keys.leaseForAccount(identity.local_account_id)
    if (lease === null) throw new KeyNotProvisionedError()
    this.assertLease(context, identity, lease)
  }

  private bootstrapIdentity(identity: CloudIdentity): { localAccountId: string, deviceId: string } {
    return { localAccountId: identity.local_account_id, deviceId: identity.device_id }
  }

  private assertLease(context: AuthContextSnapshot, identity: CloudIdentity, lease: AuthoritativeKeyContextLease): void {
    this.assertCurrent(context)
    if (!lease.isCurrent() || lease.localAccountId !== identity.local_account_id
      || lease.canonicalUserId !== context.userId || lease.authEpoch !== context.authEpoch) {
      throw new StaleAuthContextError()
    }
  }

  private assertCurrent(context: AuthContextSnapshot): void {
    if (!this.auth.isCurrent(context)) throw new StaleAuthContextError()
  }

  private assertIdentity(identity: CloudIdentity): void {
    if (typeof identity.local_account_id !== 'string' || identity.local_account_id.length < 1
      || identity.local_account_id.length > 512 || !CANONICAL_UUID.test(identity.device_id)) {
      throw new CloudIdentityUnavailableError('Durable cloud identity is malformed.')
    }
  }

  private assertNotDisposed(): void {
    if (this.disposed) throw new NoteSyncRuntimeDisposedError()
  }
}
