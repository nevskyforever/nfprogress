import { describe, expect, it, vi } from 'vitest'
import type { LegalDocumentStatus } from '@/api/legalDocuments'
import type { UserAuthTransport } from '@/api/userAuth'
import { NormalUserAuthRuntime } from '@/auth/userAuth'
import { BrowserCloudAccountSession } from './cloudAccountSession'

const document = {
  document_id: 'wotra.beta_terms',
  document_type: 'beta_terms' as const,
  revision: 'private-beta-warning-1',
  content_checksum: 'a'.repeat(64),
  language: 'ru' as const,
  title: 'Закрытое тестирование WORTA',
  content: 'Возможны ошибки и потеря данных.',
  mandatory: true,
  requires_explicit_acceptance: true,
  accepted: false,
}

function authRuntime(): NormalUserAuthRuntime {
  const transport: UserAuthTransport = {
    login: vi.fn(async () => ({ access_token: 'access', refresh_token: 'refresh', access_expires_in: 60 })),
    refresh: vi.fn(async () => ({ access_token: 'access-2', refresh_token: 'refresh-2', access_expires_in: 60 })),
    me: vi.fn(async () => ({
      id: '00000000-0000-0000-0000-000000000101', username: 'writer',
      email: 'writer@example.test', email_verified: true, role: 'user', status: 'active', created_at: 'now',
    })),
    logout: vi.fn(async () => undefined),
  }
  return new NormalUserAuthRuntime(transport)
}

describe('browser cloud legal gate', () => {
  it('checks current documents after login and opens protected storage only after acceptance', async () => {
    const pending: LegalDocumentStatus = {
      documents: [document], missing_required_document_ids: [document.document_id],
    }
    const accepted: LegalDocumentStatus = {
      documents: [{ ...document, accepted: true }], missing_required_document_ids: [],
    }
    const legalTransport = {
      status: vi.fn(async () => pending),
      accept: vi.fn(async () => accepted),
    }
    const cryptoTransport = { get: vi.fn(async () => ({
      provisioned: true as const,
      password: { crypto_version: 1, wrapping_version: 1, kdf: { kdf_version: 1, algorithm: 'argon2id13', salt: '', opslimit: 2, memlimit: 1 }, nonce: '', ciphertext: '' },
      recovery: null,
    })) }
    const storage = {
      read: vi.fn(async () => ({
        local_account_id: 'local-account', device_id: '00000000-0000-4000-8000-000000000102',
      })),
      close: vi.fn(async () => undefined),
    }
    const openStorage = vi.fn(async () => storage)
    const session = new BrowserCloudAccountSession({
      auth: authRuntime(), legalTransport,
      cryptoTransport,
      openStorage: openStorage as never,
    })

    expect(await session.login('writer', 'password', 'ru')).toBeNull()
    expect(session.status).toBe('legal_required')
    expect(session.legalDocuments).toEqual([document])
    expect(cryptoTransport.get).not.toHaveBeenCalled()
    expect(openStorage).not.toHaveBeenCalled()

    await session.acceptLegalDocuments('ru', [{
      document_id: document.document_id,
      revision: document.revision,
      content_checksum: document.content_checksum,
      language: document.language,
    }])
    expect(legalTransport.accept).toHaveBeenCalledOnce()
    expect(cryptoTransport.get).toHaveBeenCalledOnce()
    expect(openStorage).toHaveBeenCalledOnce()
    expect(session.status).toBe('authenticated')
    await session.dispose()
  })
})
