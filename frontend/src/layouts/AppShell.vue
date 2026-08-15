<script setup lang="ts">
import { computed } from 'vue'
import { IonIcon, IonRouterOutlet } from '@ionic/vue'
import {
  cloudOfflineOutline,
  contrastOutline,
  folderOpenOutline,
  languageOutline,
} from 'ionicons/icons'

import { useNetworkStatus } from '@/composables/useNetworkStatus'
import { SUPPORTED_LANGUAGES, useLocaleStore } from '@/stores/locale'
import { useThemeStore, type ThemePreference } from '@/stores/theme'
import type { SupportedLanguage } from '@/types/api'

const { online } = useNetworkStatus()
const theme = useThemeStore()
const locale = useLocaleStore()
const t = locale.translate
const startupError = window.__NFPROGRESS_RUNTIME__?.startupError ?? ''
const hasBanner = computed(() => !online.value || Boolean(startupError))

const themeLabel = computed(() => {
  const labels: Record<ThemePreference, string> = {
    system: t('Системная тема'),
    light: t('Светлая тема'),
    dark: t('Тёмная тема'),
  }
  return labels[theme.preference]
})

function selectTheme(event: Event): void {
  theme.setPreference((event.target as HTMLSelectElement).value as ThemePreference)
}

function selectLanguage(event: Event): void {
  void locale.setLanguage((event.target as HTMLSelectElement).value as SupportedLanguage)
}
</script>

<template>
  <a class="skip-link" href="#main-content">{{ t('Перейти к содержимому') }}</a>

  <div class="app-shell">
    <aside class="sidebar" :aria-label="t('Основная навигация')">
      <RouterLink class="brand" to="/projects" aria-label="nfprogress — проекты">
        <span class="brand-mark" aria-hidden="true">nf</span>
        <span>
          <strong>nfprogress</strong>
          <small>{{ t('Пространство писателя') }}</small>
        </span>
      </RouterLink>

      <nav class="primary-navigation" :aria-label="t('Разделы приложения')">
        <RouterLink class="navigation-link" to="/projects">
          <IonIcon :icon="folderOpenOutline" aria-hidden="true" />
          <span>{{ t('Проекты') }}</span>
        </RouterLink>
      </nav>

      <div class="sidebar-controls">
        <label class="compact-select">
          <IonIcon :icon="languageOutline" aria-hidden="true" />
          <span class="visually-hidden">{{ t('Язык интерфейса') }}</span>
          <select
            :value="locale.language"
            :aria-label="t('Язык интерфейса')"
            @change="selectLanguage"
          >
            <option
              v-for="language in SUPPORTED_LANGUAGES"
              :key="language.code"
              :value="language.code"
            >
              {{ language.displayName }}
            </option>
          </select>
        </label>

        <label class="compact-select">
          <IonIcon :icon="contrastOutline" aria-hidden="true" />
          <span class="visually-hidden">{{ t('Тема') }}</span>
          <select
            :value="theme.preference"
            :aria-label="t('Тема')"
            @change="selectTheme"
          >
            <option value="system">{{ t('Системная') }}</option>
            <option value="light">{{ t('Светлая') }}</option>
            <option value="dark">{{ t('Тёмная') }}</option>
          </select>
        </label>
        <p class="theme-summary">{{ themeLabel }}</p>
      </div>
    </aside>

    <div
      v-if="startupError"
      class="network-banner network-banner--error"
      role="alert"
    >
      <IonIcon :icon="cloudOfflineOutline" aria-hidden="true" />
      {{ t('Не удалось запустить локальный backend') }}: {{ startupError }}
    </div>
    <div
      v-else-if="!online"
      class="network-banner"
      role="status"
      aria-live="polite"
    >
      <IonIcon :icon="cloudOfflineOutline" aria-hidden="true" />
      {{ t('Нет сети. Изменения станут доступны после восстановления подключения.') }}
    </div>

    <main
      id="main-content"
      class="app-main"
      :class="{ 'app-main--with-banner': hasBanner }"
      tabindex="-1"
    >
      <IonRouterOutlet />
    </main>

    <nav class="mobile-navigation" :aria-label="t('Основная навигация')">
      <RouterLink class="mobile-navigation-link" to="/projects">
        <IonIcon :icon="folderOpenOutline" aria-hidden="true" />
        <span>{{ t('Проекты') }}</span>
      </RouterLink>
      <label class="mobile-theme-select">
        <IonIcon :icon="contrastOutline" aria-hidden="true" />
        <span class="visually-hidden">{{ t('Тема') }}</span>
        <select
          :value="theme.preference"
          :aria-label="t('Тема')"
          @change="selectTheme"
        >
          <option value="system">{{ t('Системная') }}</option>
          <option value="light">{{ t('Светлая') }}</option>
          <option value="dark">{{ t('Тёмная') }}</option>
        </select>
      </label>
      <label class="mobile-theme-select">
        <IonIcon :icon="languageOutline" aria-hidden="true" />
        <span class="visually-hidden">{{ t('Язык интерфейса') }}</span>
        <select
          :value="locale.language"
          :aria-label="t('Язык интерфейса')"
          @change="selectLanguage"
        >
          <option
            v-for="language in SUPPORTED_LANGUAGES"
            :key="language.code"
            :value="language.code"
          >
            {{ language.displayName }}
          </option>
        </select>
      </label>
    </nav>
  </div>
</template>
