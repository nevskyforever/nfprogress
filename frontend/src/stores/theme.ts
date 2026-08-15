import { defineStore } from 'pinia'
import { computed, ref, watch } from 'vue'

import { syncNativeSystemBars } from '@/platform/runtime'

export const THEME_PREFERENCES = ['system', 'light', 'dark'] as const
export type ThemePreference = (typeof THEME_PREFERENCES)[number]
type ResolvedTheme = Exclude<ThemePreference, 'system'>

const STORAGE_KEY = 'nfprogress.theme'

function savedPreference(): ThemePreference {
  try {
    const value = window.localStorage.getItem(STORAGE_KEY)
    if (THEME_PREFERENCES.includes(value as ThemePreference)) {
      return value as ThemePreference
    }
  } catch {
    // Storage can be unavailable in privacy-restricted webviews.
  }
  return 'system'
}

export const useThemeStore = defineStore('theme', () => {
  const preference = ref<ThemePreference>(savedPreference())
  const systemIsDark = ref(false)
  let mediaQuery: MediaQueryList | null = null

  const resolved = computed<ResolvedTheme>(() => {
    if (preference.value !== 'system') return preference.value
    return systemIsDark.value ? 'dark' : 'light'
  })

  function applyTheme(): void {
    const root = document.documentElement
    root.dataset.theme = resolved.value
    root.style.colorScheme = resolved.value
    root.classList.toggle('ion-palette-dark', resolved.value === 'dark')
    const browserColor = resolved.value === 'dark' ? '#171b1a' : '#f7f5ef'
    document.querySelectorAll<HTMLMetaElement>('meta[name="theme-color"]').forEach((meta) => {
      meta.content = browserColor
    })
    void syncNativeSystemBars(resolved.value)
  }

  function handleSystemTheme(event: MediaQueryListEvent): void {
    systemIsDark.value = event.matches
  }

  function setPreference(value: ThemePreference): void {
    preference.value = value
    try {
      window.localStorage.setItem(STORAGE_KEY, value)
    } catch {
      // The in-memory preference still applies for this session.
    }
  }

  function initialize(): void {
    mediaQuery = window.matchMedia('(prefers-color-scheme: dark)')
    systemIsDark.value = mediaQuery.matches
    mediaQuery.addEventListener('change', handleSystemTheme)
    applyTheme()
  }

  function dispose(): void {
    mediaQuery?.removeEventListener('change', handleSystemTheme)
    mediaQuery = null
  }

  watch(resolved, applyTheme)

  return { preference, resolved, initialize, dispose, setPreference }
})
