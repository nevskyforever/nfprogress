import type { LanguageOption, SupportedLanguage } from '@/types/api'
import type { AgreementContent, HelpSection } from '@/types/content'

type LocaleCatalog = Record<string, string>

const localeCatalogs = import.meta.glob<LocaleCatalog>(
  '../i18n/generated/locales/*.json',
  { eager: true, import: 'default' },
)
const helpCatalogs = import.meta.glob<HelpSection[]>(
  '../i18n/generated/help/*.json',
  { eager: true, import: 'default' },
)

const languages: LanguageOption[] = [
  { code: 'ru', display_name: 'Русский' },
  { code: 'en', display_name: 'English' },
  { code: 'es', display_name: 'Español' },
  { code: 'de', display_name: 'Deutsch' },
  { code: 'fr', display_name: 'Français' },
  { code: 'pt_BR', display_name: 'Português (Brasil)' },
]

function catalog(language: SupportedLanguage): LocaleCatalog {
  const entry = Object.entries(localeCatalogs).find(([path]) => path.endsWith(`/${language}.json`))
  return entry?.[1] ?? {}
}

export function bundledLanguages(): LanguageOption[] {
  return languages.map((language) => ({ ...language }))
}

export function bundledLocale(language: SupportedLanguage): LocaleCatalog {
  return catalog(language)
}

export function bundledHelp(language: SupportedLanguage): HelpSection[] {
  const entry = Object.entries(helpCatalogs).find(([path]) => path.endsWith(`/${language}.json`))
  return entry?.[1] ?? []
}

export function bundledAgreement(language: SupportedLanguage): AgreementContent {
  const values = catalog(language)
  const source = Object.keys(values).find((key) => key.startsWith('<!DOCTYPE HTML')) ?? ''
  return {
    id: 'd6157bbe87d88dc1',
    language,
    html: language === 'ru' ? source : values[source] ?? source,
  }
}
