import { defineStore } from 'pinia'
import { computed, ref } from 'vue'

import { contentApi } from '@/api/content'
import type { SupportedLanguage } from '@/types/api'

const STORAGE_KEY = 'nfprogress.language'

export const SUPPORTED_LANGUAGES: ReadonlyArray<{
  code: SupportedLanguage
  displayName: string
}> = [
  { code: 'ru', displayName: 'Русский' },
  { code: 'en', displayName: 'English' },
  { code: 'es', displayName: 'Español' },
  { code: 'de', displayName: 'Deutsch' },
  { code: 'fr', displayName: 'Français' },
  { code: 'pt_BR', displayName: 'Português (Brasil)' },
]

const SUPPORTED_CODES = new Set<SupportedLanguage>(
  SUPPORTED_LANGUAGES.map(({ code }) => code),
)

function normalizeLanguage(value: string | null | undefined): SupportedLanguage | null {
  if (!value) return null
  const normalized = value.replace('-', '_')
  if (SUPPORTED_CODES.has(normalized as SupportedLanguage)) {
    return normalized as SupportedLanguage
  }
  const primary = normalized.split('_')[0]?.toLowerCase()
  if (primary === 'pt') return 'pt_BR'
  if (primary && SUPPORTED_CODES.has(primary as SupportedLanguage)) {
    return primary as SupportedLanguage
  }
  return null
}

function initialLanguage(): SupportedLanguage {
  try {
    const stored = normalizeLanguage(window.localStorage.getItem(STORAGE_KEY))
    if (stored) return stored
  } catch {
    // Fall through to the browser language.
  }
  return normalizeLanguage(navigator.language) ?? 'ru'
}

export const useLocaleStore = defineStore('locale', () => {
  const language = ref<SupportedLanguage>(initialLanguage())
  const messages = ref<Record<string, string>>({})
  const loading = ref(false)
  const loadFailed = ref(false)
  let requestSequence = 0

  const localeTag = computed(() => (language.value === 'pt_BR' ? 'pt-BR' : language.value))

  function translate(source: string, parameters: Record<string, string | number> = {}): string {
    const template = language.value === 'ru' ? source : (messages.value[source] ?? source)
    return template.replace(/\{(\w+)\}/g, (placeholder, key: string) => {
      const value = parameters[key]
      return value === undefined ? placeholder : String(value)
    })
  }

  async function setLanguage(value: SupportedLanguage): Promise<void> {
    language.value = value
    document.documentElement.lang = localeTag.value
    try {
      window.localStorage.setItem(STORAGE_KEY, value)
    } catch {
      // The selected language still applies until this webview closes.
    }

    const sequence = ++requestSequence
    loadFailed.value = false
    if (value === 'ru') {
      messages.value = {}
      loading.value = false
      return
    }

    loading.value = true
    try {
      const catalog = await contentApi.locale(value)
      if (sequence === requestSequence) messages.value = catalog
    } catch {
      if (sequence === requestSequence) {
        messages.value = {}
        loadFailed.value = true
      }
    } finally {
      if (sequence === requestSequence) loading.value = false
    }
  }

  async function initialize(): Promise<void> {
    await setLanguage(language.value)
  }

  function formatNumber(value: number, maximumFractionDigits = 1): string {
    return new Intl.NumberFormat(localeTag.value, { maximumFractionDigits }).format(value)
  }

  function formatDate(value: string | null): string {
    if (!value) return translate('Без срока')
    const date = new Date(`${value.slice(0, 10)}T00:00:00`)
    if (Number.isNaN(date.getTime())) return value
    return new Intl.DateTimeFormat(localeTag.value, {
      day: 'numeric',
      month: 'short',
      year: 'numeric',
    }).format(date)
  }

  return {
    language,
    messages,
    loading,
    loadFailed,
    localeTag,
    translate,
    setLanguage,
    initialize,
    formatNumber,
    formatDate,
  }
})
