<script setup lang="ts">
import { computed, onBeforeUnmount, ref } from 'vue'
import { ApiError } from '@/api/client'
import { KeyNotProvisionedError } from '@/auth/keyContext'
import { StaleAuthContextError } from '@/auth/userAuth'
import { CryptoError } from '@/crypto'
import { BrowserCloudAccountSession } from '@/platform/web/cloudAccountSession'
import { BrowserPersistenceError } from '@/platform/web/persistence'
import { useLocaleStore } from '@/stores/locale'
import type { SupportedLanguage } from '@/types/api'

const copy: Record<SupportedLanguage, { unlocked: string; badPassword: string; writerBusy: string; storageUnavailable: string }> = {
  ru: { unlocked: 'Ключ шифрования разблокирован.', badPassword: 'Не удалось разблокировать ключ. Проверьте пароль шифрования.', writerBusy: 'Другая вкладка использует защищённое хранилище. Закройте её и повторите попытку.', storageUnavailable: 'Защищённое хранилище браузера недоступно.' },
  en: { unlocked: 'Encryption key unlocked.', badPassword: 'Could not unlock the key. Check the encryption password.', writerBusy: 'Another tab is using secure storage. Close it and try again.', storageUnavailable: 'Secure browser storage is unavailable.' },
  es: { unlocked: 'Clave de cifrado desbloqueada.', badPassword: 'No se pudo desbloquear la clave. Comprueba la contraseña de cifrado.', writerBusy: 'Otra pestaña está usando el almacenamiento seguro. Ciérrala e inténtalo de nuevo.', storageUnavailable: 'El almacenamiento seguro del navegador no está disponible.' },
  de: { unlocked: 'Verschlüsselungsschlüssel entsperrt.', badPassword: 'Der Schlüssel konnte nicht entsperrt werden. Prüfe das Verschlüsselungspasswort.', writerBusy: 'Ein anderer Tab verwendet den sicheren Speicher. Schließe ihn und versuche es erneut.', storageUnavailable: 'Sicherer Browserspeicher ist nicht verfügbar.' },
  fr: { unlocked: 'Clé de chiffrement déverrouillée.', badPassword: 'Impossible de déverrouiller la clé. Vérifiez le mot de passe de chiffrement.', writerBusy: 'Un autre onglet utilise le stockage sécurisé. Fermez-le et réessayez.', storageUnavailable: 'Le stockage sécurisé du navigateur est indisponible.' },
  pt_BR: { unlocked: 'Chave de criptografia desbloqueada.', badPassword: 'Não foi possível desbloquear a chave. Verifique a senha de criptografia.', writerBusy: 'Outra aba está usando o armazenamento seguro. Feche-a e tente novamente.', storageUnavailable: 'O armazenamento seguro do navegador não está disponível.' },
}

const locale = useLocaleStore()
const t = locale.translate
const words = computed(() => copy[locale.language])
const session = new BrowserCloudAccountSession()
const status = ref(session.status)
const username = ref('')
const accountPasswordInput = ref<HTMLInputElement | null>(null)
const encryptionPasswordInput = ref<HTMLInputElement | null>(null)
const connectedUsername = ref<string | null>(null)
const busy = ref(false)
const error = ref<string | null>(null)

function refresh(): void {
  status.value = session.status
  connectedUsername.value = session.username
}

function safeError(value: unknown, action: 'login' | 'unlock'): string {
  if (value instanceof BrowserPersistenceError) {
    if (value.code === 'writer_busy') return words.value.writerBusy
    if (value.code === 'corrupt_record') return t('Хранилище проектов повреждено.')
    if (value.code === 'account_mismatch') return t('Сеанс аккаунта изменился. Войдите снова.')
    return words.value.storageUnavailable
  }
  if (value instanceof KeyNotProvisionedError) return t('Для этого аккаунта нужно настроить сквозное шифрование.')
  if (value instanceof StaleAuthContextError) return t('Сеанс аккаунта изменился. Войдите снова.')
  if (value instanceof ApiError && value.status === 401) return t('Сеанс аккаунта истёк. Войдите снова.')
  if (value instanceof ApiError) return t('Не удалось подключиться к nfprogress API.')
  if (value instanceof CryptoError && value.code === 'decrypt_failed') return words.value.badPassword
  return action === 'unlock' ? t('Произошла непредвиденная ошибка.') : t('Не удалось войти.')
}

async function act(action: 'login' | 'unlock' | 'lock' | 'logout', operation: () => Promise<unknown>): Promise<void> {
  if (busy.value) return
  busy.value = true
  error.value = null
  try { await operation() }
  catch (cause) { error.value = safeError(cause, action === 'unlock' ? 'unlock' : 'login') }
  finally {
    refresh()
    busy.value = false
  }
}

function signIn(): Promise<void> {
  const input = accountPasswordInput.value
  if (!input || !input.value || !username.value) return Promise.resolve()
  const password = input.value
  input.value = ''
  return act('login', () => session.login(username.value, password))
}
function unlock(): Promise<void> {
  const input = encryptionPasswordInput.value
  if (!input || !input.value) return Promise.resolve()
  const password = input.value
  input.value = ''
  return act('unlock', () => session.unlock(password))
}
function lock(): Promise<void> { return act('lock', () => session.lock()) }
function logout(): Promise<void> { return act('logout', () => session.logout()) }

onBeforeUnmount(() => {
  if (accountPasswordInput.value) accountPasswordInput.value.value = ''
  if (encryptionPasswordInput.value) encryptionPasswordInput.value.value = ''
  void session.dispose().catch(() => undefined)
})
</script>

<template>
  <section class="settings-card" aria-labelledby="browser-cloud-account-title" data-testid="browser-cloud-account">
    <div class="settings-card__heading">
      <h2 id="browser-cloud-account-title">{{ t('Режим разработчика') }} · {{ t('Облачная синхронизация заметок') }}</h2>
      <p>{{ t('Веб-приложение') }} · {{ t('Синхронизация отключена') }}</p>
    </div>
    <p :data-status="status" aria-live="polite">
      <template v-if="status === 'logged_out'">{{ t('Войдите в аккаунт') }}</template>
      <template v-else-if="status === 'authenticated'">{{ t('Подключён аккаунт') }}</template>
      <template v-else-if="status === 'locked'">{{ t('Ключ шифрования заблокирован. Введите пароль шифрования.') }}</template>
      <template v-else>{{ words.unlocked }}</template>
    </p>
    <p v-if="connectedUsername">{{ t('Подключён аккаунт') }}: <strong>{{ connectedUsername }}</strong></p>
    <p v-if="error" role="alert">{{ error }}</p>
    <form v-if="status === 'logged_out'" class="browser-cloud-account__inputs" @submit.prevent="signIn">
      <label>{{ t('Имя пользователя или e-mail') }} <input v-model="username" autocomplete="username" /></label>
      <label>{{ t('Пароль аккаунта') }} <input ref="accountPasswordInput" type="password" autocomplete="current-password" required /></label>
      <button class="nf-button" type="submit" :disabled="busy || !username">{{ t('Войти в облачный аккаунт') }}</button>
    </form>
    <div v-else class="browser-cloud-account__inputs">
      <form v-if="status !== 'unlocked'" class="browser-cloud-account__inputs" @submit.prevent="unlock">
        <label>{{ t('Пароль шифрования') }} <input ref="encryptionPasswordInput" type="password" autocomplete="off" required /></label>
        <button class="nf-button" type="submit" :disabled="busy">{{ t('Разблокировать') }}</button>
      </form>
      <button v-if="status === 'unlocked'" class="nf-button nf-button--secondary" type="button" :disabled="busy" @click="lock">{{ t('Заблокировать ключ') }}</button>
      <button class="nf-button nf-button--secondary" type="button" :disabled="busy" @click="logout">{{ t('Выйти из аккаунта') }}</button>
    </div>
  </section>
</template>

<style scoped>
.browser-cloud-account__inputs { display: flex; flex-wrap: wrap; gap: .75rem; align-items: end; }
.browser-cloud-account__inputs label { display: grid; gap: .25rem; min-width: 14rem; }
[role="alert"] { color: var(--ion-color-danger); }
</style>
