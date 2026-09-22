import type { CloudAccountBindingRepository, EnsureCloudAccountBindingResult } from '@/infrastructure/sqlite/cloudAccountBindingRepository'
import { NormalUserAuthRuntime, StaleAuthContextError, type AuthContextSnapshot } from './userAuth'

export class AuthoritativeAccountBinding {
  constructor(
    private readonly auth: NormalUserAuthRuntime,
    private readonly repository: CloudAccountBindingRepository,
  ) {}

  async ensureForCurrentUser(localAccountId: string): Promise<{
    context: AuthContextSnapshot
    result: EnsureCloudAccountBindingResult
  }> {
    if (typeof localAccountId !== 'string' || localAccountId.length < 1 || localAccountId.length > 512) {
      throw new TypeError('Invalid local account identity.')
    }
    const context = this.auth.requireContext()
    const result = await this.repository.ensure(localAccountId, context.userId)
    if (!this.auth.isCurrent(context)) throw new StaleAuthContextError()
    return { context, result }
  }
}
