import { apiRequest } from './client'
import type { LanguageOption, SupportedLanguage } from '@/types/api'
import type { AgreementContent, HelpSection } from '@/types/content'

export const contentApi = {
  languages(): Promise<LanguageOption[]> {
    return apiRequest<LanguageOption[]>('/api/content/languages')
  },

  locale(language: SupportedLanguage): Promise<Record<string, string>> {
    return apiRequest<Record<string, string>>(
      `/api/content/locales/${encodeURIComponent(language)}`,
    )
  },

  help(language: SupportedLanguage, signal?: AbortSignal): Promise<HelpSection[]> {
    const params = new URLSearchParams({ language })
    return apiRequest<HelpSection[]>(`/api/content/help?${params.toString()}`, { signal })
  },

  agreement(language: SupportedLanguage, signal?: AbortSignal): Promise<AgreementContent> {
    const params = new URLSearchParams({ language })
    return apiRequest<AgreementContent>(`/api/content/agreement?${params.toString()}`, { signal })
  },
}
