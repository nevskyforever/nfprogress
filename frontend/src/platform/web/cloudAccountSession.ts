import { accountCryptoApi, type AccountCryptoTransport } from '@/api/accountCrypto'
import { AuthoritativeAccountBinding } from '@/auth/accountBinding'
import { KeyNotProvisionedError, RuntimeKeyContext, type AuthoritativeKeyContextLease } from '@/auth/keyContext'
import { NormalUserAuthRuntime, StaleAuthContextError, type AuthContextSnapshot } from '@/auth/userAuth'
import { currentPlatform } from '@/platform/runtime'
import { BrowserPersistenceError, openBrowserPersistence } from './persistence'
import type { BrowserLocalAuthorityRuntime } from './localAuthority'
import type { BrowserSyncScope } from './syncDurability'

type BrowserStorage = Awaited<ReturnType<typeof openBrowserPersistence>>
type BrowserIdentity = { readonly local_account_id: string; readonly device_id: string }

export interface BrowserLocalNoteRepository {
  /** Account/device scope derived from the authenticated, unlocked Web session. */
  readonly scope: BrowserSyncScope
  /** Existing C21 encrypted local source. It has no cloud transport or Note writer. */
  readonly source: Pick<BrowserLocalAuthorityRuntime, 'readSnapshot' | 'withDecryptedSnapshot' | 'assertSnapshot' | 'initializeProject' | 'createProject' | 'createNote' | 'updateNote' | 'tombstoneNote' | 'replaceProject' | 'deleteProject'>
}

export interface BrowserAccountSessionOptions {
  readonly auth?: NormalUserAuthRuntime
  readonly cryptoTransport?: AccountCryptoTransport
  readonly openStorage?: typeof openBrowserPersistence
}

/** Test-Web account/key composition. It owns no Note transport or reader authority. */
export class BrowserCloudAccountSession {
  private readonly auth: NormalUserAuthRuntime
  private readonly cryptoTransport: AccountCryptoTransport
  private readonly openStorage: typeof openBrowserPersistence
  private readonly unsubscribe: () => void
  private storage: BrowserStorage | null = null
  private bindings: AuthoritativeAccountBinding | null = null
  private keys: RuntimeKeyContext | null = null
  private identity: BrowserIdentity | null = null
  private controller: AbortController | null = null
  private opening: Promise<void> | null = null
  private generation = 0
  private everUnlocked = false
  private disposed = false
  private readonly onPageHide = () => { void this.logout().catch(() => undefined) }

  constructor(options: BrowserAccountSessionOptions = {}) {
    this.auth = options.auth ?? new NormalUserAuthRuntime()
    this.cryptoTransport = options.cryptoTransport ?? accountCryptoApi
    this.openStorage = options.openStorage ?? openBrowserPersistence
    this.unsubscribe = this.auth.onInvalidated(() => this.revoke(true))
    if (typeof window !== 'undefined') window.addEventListener('pagehide', this.onPageHide)
  }

  get status(): 'logged_out' | 'authenticated' | 'unlocked' | 'locked' {
    if (this.auth.state !== 'authenticated') return 'logged_out'
    if (this.identity && this.keys?.leaseForAccount(this.identity.local_account_id)?.isCurrent()) return 'unlocked'
    return this.everUnlocked ? 'locked' : 'authenticated'
  }

  get currentIdentity(): BrowserIdentity | null {
    return this.auth.state === 'authenticated' && this.identity ? { ...this.identity } : null
  }

  get username(): string | null {
    return this.auth.state === 'authenticated' ? this.auth.requireContext().username : null
  }

  private assertWeb(): void {
    if (this.disposed || currentPlatform() !== 'web' || !import.meta.env.DEV) {
      throw new BrowserPersistenceError('unavailable')
    }
  }

  private async revoke(clearIdentity: boolean): Promise<void> {
    this.generation += 1
    this.controller?.abort()
    this.controller = null
    const keys = this.keys, storage = this.storage
    this.keys = null
    this.bindings = null
    this.storage = null
    if (clearIdentity) { this.identity = null; this.everUnlocked = false }
    await Promise.all([keys?.dispose(), storage?.close()])
  }

  private async openFor(context: AuthContextSnapshot): Promise<void> {
    if (this.storage) return
    if (this.opening) {
      await this.opening
      if (!this.auth.isCurrent(context)) throw new StaleAuthContextError()
      return
    }
    const opening = this.openFreshFor(context)
    this.opening = opening
    try { await opening } finally { if (this.opening === opening) this.opening = null }
  }

  private async openFreshFor(context: AuthContextSnapshot): Promise<void> {
    const generation = this.generation
    const controller = new AbortController()
    this.controller = controller
    let storage: BrowserStorage | null = null
    try {
      storage = await this.openStorage(context.userId, controller.signal)
      const identity = await storage.read(context.userId)
      if (!identity || !this.auth.isCurrent(context) || this.generation !== generation || controller.signal.aborted) {
        throw new StaleAuthContextError()
      }
      if (this.identity && (this.identity.local_account_id !== identity.local_account_id || this.identity.device_id !== identity.device_id)) {
        throw new BrowserPersistenceError('account_mismatch')
      }
      const bindings = new AuthoritativeAccountBinding(this.auth, storage)
      this.storage = storage
      this.bindings = bindings
      this.identity = { local_account_id: identity.local_account_id, device_id: identity.device_id }
      this.keys = new RuntimeKeyContext(this.auth, bindings, this.cryptoTransport)
    } catch (error) {
      await storage?.close()
      if (this.controller === controller) this.controller = null
      throw error
    }
  }

  async login(username: string, password: string): Promise<BrowserIdentity> {
    this.assertWeb()
    const context = await this.auth.login(username, password)
    try {
      const record = await this.auth.authorized(token => this.cryptoTransport.get(token))
      if (!record.value.provisioned) throw new KeyNotProvisionedError()
      await this.openFor(context)
      if (!this.identity || !this.auth.isCurrent(context)) throw new StaleAuthContextError()
      return { ...this.identity }
    } catch (error) {
      if (this.auth.isCurrent(context)) await this.auth.logout().catch(() => undefined)
      throw error
    }
  }

  async unlock(passphrase: string): Promise<AuthoritativeKeyContextLease> {
    this.assertWeb()
    const context = this.auth.requireContext()
    await this.openFor(context)
    const keys = this.keys, identity = this.identity, generation = this.generation
    if (!keys || !identity) throw new BrowserPersistenceError('closed')
    const lease = await keys.unlockWithPassphrase(identity.local_account_id, passphrase)
    if (!this.auth.isCurrent(context) || generation !== this.generation || !lease.isCurrent()) {
      await keys.lock()
      throw new StaleAuthContextError()
    }
    this.everUnlocked = true
    return lease
  }

  /** Internal local-only composition. The returned source becomes unusable on lock/logout. */
  localNoteRepository(): BrowserLocalNoteRepository {
    this.assertWeb()
    const context = this.auth.requireContext(), identity = this.identity
    const storage = this.storage, bindings = this.bindings, keys = this.keys
    const lease = identity && keys?.leaseForAccount(identity.local_account_id)
    if (!identity || !storage || !bindings || !keys || !lease?.isCurrent()) throw new BrowserPersistenceError('closed')
    const scope = Object.freeze({ canonicalUserId: context.userId, accountId: identity.local_account_id, deviceId: identity.device_id })
    return Object.freeze({ scope, source: storage.localSource.bind(this.auth, bindings, keys) })
  }

  async lock(): Promise<void> {
    await this.revoke(false)
    if (this.auth.state === 'authenticated') this.everUnlocked = true
  }

  async logout(): Promise<void> {
    await this.auth.logout()
  }

  async dispose(): Promise<void> {
    if (this.disposed) return
    this.disposed = true
    if (typeof window !== 'undefined') window.removeEventListener('pagehide', this.onPageHide)
    try { await this.logout() } finally { this.unsubscribe(); await this.revoke(true) }
  }
}
