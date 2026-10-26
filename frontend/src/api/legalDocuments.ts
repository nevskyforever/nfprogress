import { apiRequest } from './client'
import type { SupportedLanguage } from '@/types/api'

export interface LegalDocument {
  document_id: string
  document_type: 'user_agreement' | 'privacy_policy' | 'personal_data_consent' | 'beta_terms'
  revision: string
  content_checksum: string
  language: SupportedLanguage
  title: string
  content: string
  mandatory: boolean
  requires_explicit_acceptance: boolean
  accepted: boolean
}

export interface LegalDocumentStatus {
  documents: LegalDocument[]
  missing_required_document_ids: string[]
}

export interface LegalDocumentConfirmation {
  document_id: string
  revision: string
  content_checksum: string
  language: SupportedLanguage
}

export function confirmationFor(document: LegalDocument): LegalDocumentConfirmation {
  return {
    document_id: document.document_id,
    revision: document.revision,
    content_checksum: document.content_checksum,
    language: document.language,
  }
}

function authorization(accessToken: string): Headers {
  return new Headers({ Authorization: `Bearer ${accessToken}` })
}

export const legalDocumentsApi = {
  status(accessToken: string, language: SupportedLanguage): Promise<LegalDocumentStatus> {
    return apiRequest(`/api/v1/legal/documents/status?language=${encodeURIComponent(language)}`, {
      headers: authorization(accessToken),
    })
  },
  accept(accessToken: string, language: SupportedLanguage,
    documents: LegalDocumentConfirmation[]): Promise<LegalDocumentStatus> {
    return apiRequest('/api/v1/legal/documents/accept', {
      method: 'POST',
      headers: authorization(accessToken),
      body: { language, documents },
    })
  },
}
