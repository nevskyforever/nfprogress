import { apiRequest } from './client'
import type { LanguageOption, SupportedLanguage } from '@/types/api'

export const contentApi = {
  languages(): Promise<LanguageOption[]> {
    return apiRequest<LanguageOption[]>('/api/content/languages')
  },

  locale(language: SupportedLanguage): Promise<Record<string, string>> {
    return apiRequest<Record<string, string>>(
      `/api/content/locales/${encodeURIComponent(language)}`,
    )
  },
}
