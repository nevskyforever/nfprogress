<script setup lang="ts">
import { ref } from 'vue'
import { IonApp } from '@ionic/vue'

import { apiErrorMessage } from '@/api/client'
import { settingsApi } from '@/api/settings'
import UserAgreementGate from '@/components/agreement/UserAgreementGate.vue'
import AppShell from '@/layouts/AppShell.vue'
import { isSupportedLanguage, useLocaleStore } from '@/stores/locale'
import { isThemePreference, useThemeStore } from '@/stores/theme'
import type { SettingsResponse } from '@/types/content'

type BootstrapState = 'loading' | 'agreement' | 'ready' | 'error'

const locale = useLocaleStore()
const theme = useThemeStore()
const t = locale.translate
const bootstrapState = ref<BootstrapState>('loading')
const bootstrapError = ref<string | null>(null)

async function applyBackendPreferences(settings: SettingsResponse): Promise<void> {
  if (isThemePreference(settings.values.frontend_theme)) {
    theme.setPreference(settings.values.frontend_theme)
  }
  const language = isSupportedLanguage(settings.values.language)
    ? settings.values.language
    : locale.language
  await locale.setLanguage(language)
}

async function bootstrapApplication(): Promise<void> {
  bootstrapState.value = 'loading'
  bootstrapError.value = null
  try {
    const settings = await settingsApi.get()
    await applyBackendPreferences(settings)
    bootstrapState.value = settings.values.user_agreement === true ? 'ready' : 'agreement'
  } catch (error) {
    await locale.initialize()
    bootstrapError.value = t(apiErrorMessage(error))
    bootstrapState.value = 'error'
  }
}

async function handleAgreementAccepted(settings: SettingsResponse): Promise<void> {
  await applyBackendPreferences(settings)
  bootstrapState.value = 'ready'
}

void bootstrapApplication()
</script>

<template>
  <IonApp>
    <div
      v-if="bootstrapState === 'loading'"
      class="application-bootstrap"
      role="status"
      aria-live="polite"
    >
      <span class="application-bootstrap__mark" aria-hidden="true">nf</span>
      <p>{{ t('Запускаем nfprogress…') }}</p>
    </div>

    <div
      v-else-if="bootstrapState === 'error'"
      class="application-bootstrap"
      role="alert"
    >
      <span class="application-bootstrap__mark" aria-hidden="true">nf</span>
      <h1>{{ t('Не удалось открыть nfprogress') }}</h1>
      <p>{{ bootstrapError ?? t('Backend недоступен.') }}</p>
      <button class="nf-button" type="button" @click="bootstrapApplication">
        {{ t('Повторить') }}
      </button>
    </div>

    <UserAgreementGate
      v-else-if="bootstrapState === 'agreement'"
      @accepted="handleAgreementAccepted"
    />
    <AppShell v-else />
  </IonApp>
</template>

<style scoped>
.application-bootstrap {
  display: grid;
  min-height: 100dvh;
  gap: var(--nf-space-3);
  align-content: center;
  justify-items: center;
  padding: var(--nf-space-5);
  background: var(--nf-color-canvas);
  color: var(--nf-color-text);
  text-align: center;
}

.application-bootstrap h1,
.application-bootstrap p {
  max-width: 38rem;
  margin: 0;
}

.application-bootstrap h1 {
  font-family: var(--nf-font-serif);
  font-size: clamp(1.8rem, 5vw, 2.7rem);
}

.application-bootstrap p {
  color: var(--nf-color-text-muted);
  line-height: 1.5;
}

.application-bootstrap__mark {
  display: grid;
  width: 4rem;
  height: 4rem;
  place-items: center;
  border-radius: var(--nf-radius-md);
  background: var(--nf-color-primary);
  color: #fff;
  font-family: var(--nf-font-serif);
  font-size: 1.7rem;
  font-weight: 800;
}
</style>
