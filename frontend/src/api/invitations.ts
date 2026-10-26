import { apiRequest } from './client'
import type { LegalDocumentConfirmation, LegalDocumentStatus } from './legalDocuments'
import type { SupportedLanguage } from '@/types/api'

/** The invitation secret stays in memory and is never persisted by this client. */
export const invitationApi = {
  documents: (token: string, language: SupportedLanguage) => apiRequest<LegalDocumentStatus>(
    '/api/v1/auth/invitations/documents', { method: 'POST', body: { token, language } },
  ),
  accept: (token: string, password: string, language: SupportedLanguage,
    documents: LegalDocumentConfirmation[]) => apiRequest<{ code: string; username: string }>(
    '/api/v1/auth/invitations/accept', {
      method: 'POST', body: { token, password, language, documents },
    },
  ),
}
