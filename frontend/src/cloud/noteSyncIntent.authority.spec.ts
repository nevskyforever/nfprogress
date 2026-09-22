// @vitest-environment node
import { beforeAll, describe, expect, it, vi } from 'vitest'

import { encodeBase64Url } from '@/api/base64url'
import type { AccountCryptoTransport, CurrentUserCryptoRecord } from '@/api/accountCrypto'
import { ApiError } from '@/api/client'
import type { UserAuthTransport } from '@/api/userAuth'
import { AuthoritativeAccountBinding } from '@/auth/accountBinding'
import { RuntimeKeyContext } from '@/auth/keyContext'
import { NormalUserAuthRuntime } from '@/auth/userAuth'
import {
  generateAccountMasterKey,
  wrapAmkWithPassphrase,
  type AccountMasterKey,
  type ObjectCryptoEnvelope,
} from '@/crypto'
import type { CloudAccountBindingRepository } from '@/infrastructure/sqlite/cloudAccountBindingRepository'
import { openNoteSyncEvent } from './encryptedSyncProtocol'
import {
  sealPendingNoteSyncIntents,
  type NoteSyncIntentRepository,
  type UnsealedNoteSyncIntent,
} from './noteSyncIntent'

const USER_ONE = '00000000-0000-0000-0000-000000000101'
const USER_TWO = '00000000-0000-0000-0000-000000000102'
const ACCOUNT = 'authoritative-local-account'
const EVENT_ID = '123e4567-e89b-42d3-a456-426614174000'
const DEVICE_ID = '123e4567-e89b-42d3-a456-426614174001'
const TIME = '2026-09-22T00:00:00.000000Z'

let record: CurrentUserCryptoRecord
let authoritativeAmk: AccountMasterKey

beforeAll(async () => {
  authoritativeAmk = await generateAccountMasterKey()
  const wrapped = await wrapAmkWithPassphrase(authoritativeAmk, 'master passphrase')
  record = {
    provisioned: true,
    password: {
      crypto_version: wrapped.crypto_version,
      wrapping_version: wrapped.wrapping_version,
      kdf: { ...wrapped.kdf, salt: encodeBase64Url(wrapped.kdf.salt) },
      nonce: encodeBase64Url(wrapped.nonce),
      ciphertext: encodeBase64Url(wrapped.ciphertext),
    },
    recovery: null,
  }
})

function authTransport(): UserAuthTransport {
  return {
    login: vi.fn(async username => ({
      access_token: username,
      refresh_token: `refresh-${username}`,
      access_expires_in: 60,
    })),
    refresh: vi.fn(),
    logout: vi.fn(async () => undefined),
    me: vi.fn(async token => ({
      id: token === 'one' ? USER_ONE : USER_TWO,
      username: token,
      email: `${token}@example.test`,
      email_verified: true,
      role: 'user',
      status: 'active',
      created_at: TIME,
    })),
  }
}

async function authoritativeRuntime() {
  const auth = new NormalUserAuthRuntime(authTransport())
  await auth.login('one', 'account password')
  const bindingRepository: CloudAccountBindingRepository = {
    ensure: vi.fn(async (accountId, userId) => {
      if (accountId !== ACCOUNT || userId !== USER_ONE) throw new Error('binding mismatch')
      return 'validated' as const
    }),
  }
  const binding = new AuthoritativeAccountBinding(auth, bindingRepository)
  const cryptoTransport: AccountCryptoTransport = { get: vi.fn(async () => record) }
  const keys = new RuntimeKeyContext(auth, binding, cryptoTransport)
  await keys.unlockWithPassphrase(ACCOUNT, 'master passphrase')
  return { auth, keys, bindingRepository, cryptoTransport }
}

function intent(accountId = ACCOUNT): UnsealedNoteSyncIntent {
  return {
    event_id: EVENT_ID,
    account_id: accountId,
    device_id: DEVICE_ID,
    project_id: 'project-1',
    entity_id: 'note-1',
    entity_type: 'note',
    operation: 'upsert',
    revision: 1,
    parent_event_id: null,
    updated_at: TIME,
    deleted_at: null,
    local_ordinal: 1,
    mutation_generation: 3,
    snapshot_json: JSON.stringify({
      id: 'note-1',
      project_id: 'project-1',
      stage_id: null,
      source_type: 'project',
      source_map_id: null,
      source_node_id: null,
      content_format: 'html',
      title: 'Authoritative',
      content: '<p>Secret</p>',
      checklist: [],
      color: 'default',
      pinned: false,
      archived: false,
      sort_order: 0,
      tags: [],
      created_at: TIME,
      updated_at: TIME,
      revision: 1,
      metadata: {},
    }),
    seal_state: 'pending',
    seal_attempt_count: 0,
    last_error_code: null,
    next_attempt_at: null,
  }
}

function repository(
  source: UnsealedNoteSyncIntent,
  commit: NoteSyncIntentRepository['commitSealedEvent'],
): NoteSyncIntentRepository {
  return {
    list: vi.fn(async () => [source]),
    recordSealFailure: vi.fn(async () => 'recorded' as const),
    commitSealedEvent: vi.fn(commit),
  }
}

function deferred(): { promise: Promise<void>; resolve: () => void } {
  let resolve!: () => void
  const promise = new Promise<void>(done => { resolve = done })
  return { promise, resolve }
}

describe('authoritative Note sealing lease integration', () => {
  it('seals with the persisted binding, authenticated user, and unwrapped AMK', async () => {
    const { keys, bindingRepository, cryptoTransport } = await authoritativeRuntime()
    const source = intent()
    let envelope: ObjectCryptoEnvelope | undefined
    const store = repository(source, async input => {
      envelope = input.envelope
      return 'sealed'
    })

    await expect(sealPendingNoteSyncIntents(store, keys)).resolves.toMatchObject({
      results: [{ status: 'sealed' }],
    })
    expect(bindingRepository.ensure).toHaveBeenCalledWith(ACCOUNT, USER_ONE)
    expect(cryptoTransport.get).toHaveBeenCalledWith('one')
    await expect(openNoteSyncEvent(authoritativeAmk, USER_ONE, {
      event_id: source.event_id,
      project_id: source.project_id,
      entity_id: source.entity_id,
      entity_type: source.entity_type,
      operation: source.operation,
      revision: source.revision,
      updated_at: source.updated_at,
      deleted_at: source.deleted_at,
    }, envelope!)).resolves.toMatchObject({ note: { content: '<p>Secret</p>' } })
  })

  it('fails closed for the wrong account and for a locked or switched key context', async () => {
    const { auth, keys } = await authoritativeRuntime()
    const wrongAccount = intent('other-account')
    const wrongStore = repository(wrongAccount, async () => 'sealed')
    await expect(sealPendingNoteSyncIntents(wrongStore, keys)).resolves.toMatchObject({
      results: [{ status: 'failure_recorded', error_code: 'key_unavailable' }],
    })
    expect(wrongStore.commitSealedEvent).not.toHaveBeenCalled()

    await expect(keys.unlockWithPassphrase(ACCOUNT, 'wrong passphrase')).rejects.toThrow()
    const lockedStore = repository(intent(), async () => 'sealed')
    await expect(sealPendingNoteSyncIntents(lockedStore, keys)).resolves.toMatchObject({
      results: [{ status: 'failure_recorded', error_code: 'key_unavailable' }],
    })
    expect(lockedStore.commitSealedEvent).not.toHaveBeenCalled()

    await auth.login('two', 'account password')
    const switchedStore = repository(intent(), async () => 'sealed')
    await sealPendingNoteSyncIntents(switchedStore, keys)
    expect(switchedStore.commitSealedEvent).not.toHaveBeenCalled()
  })

  it.each(['logout', 'account_switch', 'key_lock', 'session_401'] as const)(
    'orders %s after an in-flight sealing commit',
    async lifecycle => {
      const { auth, keys } = await authoritativeRuntime()
      const enteredCommit = deferred()
      const releaseCommit = deferred()
      const store = repository(intent(), async () => {
        enteredCommit.resolve()
        await releaseCommit.promise
        return 'sealed'
      })
      const sealing = sealPendingNoteSyncIntents(store, keys)
      await enteredCommit.promise

      let invalidationCompleted = false
      const invalidation = (lifecycle === 'logout'
        ? auth.logout()
        : lifecycle === 'account_switch'
          ? auth.login('two', 'account password').then(() => undefined)
          : lifecycle === 'key_lock'
            ? keys.lock()
            : auth.authorized(async () => {
              throw new ApiError(401, 'invalid_token', 'expired')
            }).then(() => undefined, () => undefined)
      ).then(() => { invalidationCompleted = true })
      await Promise.resolve()

      expect(invalidationCompleted).toBe(false)
      expect(keys.leaseForAccount(ACCOUNT)).toBeNull()

      releaseCommit.resolve()
      await expect(sealing).resolves.toMatchObject({ results: [{ status: 'sealed' }] })
      await invalidation
      expect(invalidationCompleted).toBe(true)
      expect(store.commitSealedEvent).toHaveBeenCalledTimes(1)
    },
  )

  it('retries from the durable intent after a rejected locked-context pass', async () => {
    const { auth, keys, bindingRepository } = await authoritativeRuntime()
    await keys.lock()
    const source = intent()
    const store = repository(source, async () => 'sealed')

    const rejected = await sealPendingNoteSyncIntents(store, keys)
    expect(rejected.results).toMatchObject([
      { status: 'failure_recorded', error_code: 'key_unavailable' },
    ])
    expect(store.commitSealedEvent).not.toHaveBeenCalled()

    await keys.unlockWithPassphrase(ACCOUNT, 'master passphrase')
    source.seal_state = 'blocked'
    const retried = await sealPendingNoteSyncIntents(store, keys, { retryBlocked: true })
    expect(retried.results).toMatchObject([{ status: 'sealed' }])
    expect(store.commitSealedEvent).toHaveBeenCalledTimes(1)
    expect(auth.requireContext().userId).toBe(USER_ONE)
    expect(bindingRepository.ensure).toHaveBeenCalledTimes(2)
  })
})
