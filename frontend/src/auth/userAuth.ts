import { ApiError } from '@/api/client'
import { userAuthApi, type CurrentUserAccount, type UserAuthTokens, type UserAuthTransport } from '@/api/userAuth'

const CANONICAL_UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/

export interface AuthContextSnapshot {
  readonly userId: string
  readonly username: string
  readonly authEpoch: number
}

export class AuthenticationRequiredError extends Error {
  readonly name = 'AuthenticationRequiredError'
}

export class StaleAuthContextError extends Error {
  readonly name = 'StaleAuthContextError'
}

type InvalidationListener = () => void | Promise<void>

function validTokens(value: UserAuthTokens): boolean {
  return typeof value.access_token === 'string' && value.access_token.length > 0
    && typeof value.refresh_token === 'string' && value.refresh_token.length > 0
    && Number.isFinite(value.access_expires_in) && value.access_expires_in > 0
}

function validNormalUser(value: CurrentUserAccount): boolean {
  return CANONICAL_UUID.test(value.id) && value.role === 'user' && value.status === 'active'
}

export class NormalUserAuthRuntime {
  private tokens: UserAuthTokens | null = null
  private user: CurrentUserAccount | null = null
  private epoch = 0
  private readonly listeners = new Set<InvalidationListener>()

  constructor(private readonly transport: UserAuthTransport = userAuthApi) {}

  get state(): 'authenticated' | 'unauthenticated' {
    return this.tokens !== null && this.user !== null ? 'authenticated' : 'unauthenticated'
  }

  get authEpoch(): number {
    return this.epoch
  }

  onInvalidated(listener: InvalidationListener): () => void {
    this.listeners.add(listener)
    return () => this.listeners.delete(listener)
  }

  private async invalidate(): Promise<void> {
    this.tokens = null
    this.user = null
    this.epoch += 1
    await Promise.all(Array.from(this.listeners, listener => listener()))
  }

  private activate(tokens: UserAuthTokens, user: CurrentUserAccount): AuthContextSnapshot {
    if (!validTokens(tokens) || !validNormalUser(user)) throw new AuthenticationRequiredError()
    this.tokens = tokens
    this.user = user
    this.epoch += 1
    return this.requireContext()
  }

  async login(username: string, password: string): Promise<AuthContextSnapshot> {
    const previous = this.tokens
    await this.invalidate()
    const expectedEpoch = this.epoch
    if (previous) void this.transport.logout(previous.access_token).catch(() => undefined)
    const tokens = await this.transport.login(username, password)
    try {
      const user = await this.transport.me(tokens.access_token)
      if (this.epoch !== expectedEpoch || this.state !== 'unauthenticated') {
        throw new StaleAuthContextError()
      }
      return this.activate(tokens, user)
    } catch (error) {
      void this.transport.logout(tokens.access_token).catch(() => undefined)
      if (this.epoch === expectedEpoch && this.state === 'unauthenticated') {
        await this.invalidate()
      }
      throw error
    }
  }

  async refresh(): Promise<AuthContextSnapshot> {
    const current = this.tokens
    if (!current) throw new AuthenticationRequiredError()
    const expectedEpoch = this.epoch
    try {
      const replacement = await this.transport.refresh(current.refresh_token)
      const user = await this.transport.me(replacement.access_token)
      if (this.epoch !== expectedEpoch || this.tokens !== current) throw new StaleAuthContextError()
      await this.invalidate()
      return this.activate(replacement, user)
    } catch (error) {
      if (!(error instanceof StaleAuthContextError)
        && this.epoch === expectedEpoch && this.tokens === current) {
        await this.invalidate()
      }
      throw error
    }
  }

  async logout(): Promise<void> {
    const current = this.tokens
    await this.invalidate()
    if (current) await this.transport.logout(current.access_token)
  }

  requireContext(): AuthContextSnapshot {
    if (!this.user || !this.tokens) throw new AuthenticationRequiredError()
    return { userId: this.user.id, username: this.user.username, authEpoch: this.epoch }
  }

  isCurrent(context: AuthContextSnapshot): boolean {
    return this.state === 'authenticated'
      && context.authEpoch === this.epoch
      && context.userId === this.user?.id
  }

  async authorized<T>(request: (accessToken: string) => Promise<T>): Promise<{ value: T; context: AuthContextSnapshot }> {
    const context = this.requireContext()
    const accessToken = this.tokens!.access_token
    try {
      const value = await request(accessToken)
      if (!this.isCurrent(context)) throw new StaleAuthContextError()
      return { value, context }
    } catch (error) {
      if (error instanceof ApiError && error.status === 401 && this.isCurrent(context)) {
        await this.invalidate()
      }
      throw error
    }
  }
}
