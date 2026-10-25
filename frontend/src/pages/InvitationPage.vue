<script setup lang="ts">
import { computed, onMounted, onBeforeUnmount, ref } from 'vue'
import { invitationApi } from '@/api/invitations'
import { useLocaleStore } from '@/stores/locale'
import type { SupportedLanguage } from '@/types/api'

const copy: Record<SupportedLanguage, { title: string; detail: string; password: string; confirm: string; submit: string; invalid: string; mismatch: string; failed: string; done: string }> = {
  ru: { title: 'Приглашение в WORTA', detail: 'Закрытое тестирование. Задайте пароль для созданного администратором аккаунта.', password: 'Новый пароль (не менее 15 символов)', confirm: 'Повторите пароль', submit: 'Создать пароль', invalid: 'Ссылка недействительна или срок её действия истёк.', mismatch: 'Пароли не совпадают.', failed: 'Не удалось принять приглашение. Проверьте ссылку и повторите попытку.', done: 'Пароль создан. Аккаунт готов к входу в тестовый Web-клиент.' },
  en: { title: 'WORTA invitation', detail: 'Private testing. Set a password for the account created by an administrator.', password: 'New password (at least 15 characters)', confirm: 'Repeat password', submit: 'Set password', invalid: 'This link is invalid or has expired.', mismatch: 'Passwords do not match.', failed: 'Could not accept the invitation. Check the link and try again.', done: 'Password set. The account can now sign in to the test Web client.' },
  es: { title: 'Invitación a WORTA', detail: 'Prueba privada. Establece una contraseña para la cuenta creada por un administrador.', password: 'Nueva contraseña (al menos 15 caracteres)', confirm: 'Repite la contraseña', submit: 'Establecer contraseña', invalid: 'Este enlace no es válido o ha caducado.', mismatch: 'Las contraseñas no coinciden.', failed: 'No se pudo aceptar la invitación. Comprueba el enlace e inténtalo de nuevo.', done: 'Contraseña establecida. Ya puedes entrar en el cliente Web de prueba.' },
  de: { title: 'WORTA-Einladung', detail: 'Geschlossener Test. Lege ein Passwort für das vom Administrator erstellte Konto fest.', password: 'Neues Passwort (mindestens 15 Zeichen)', confirm: 'Passwort wiederholen', submit: 'Passwort festlegen', invalid: 'Dieser Link ist ungültig oder abgelaufen.', mismatch: 'Die Passwörter stimmen nicht überein.', failed: 'Die Einladung konnte nicht angenommen werden. Prüfe den Link und versuche es erneut.', done: 'Passwort festgelegt. Das Konto kann sich jetzt im Test-Webclient anmelden.' },
  fr: { title: 'Invitation WORTA', detail: 'Test privé. Définissez le mot de passe du compte créé par un administrateur.', password: 'Nouveau mot de passe (15 caractères minimum)', confirm: 'Répétez le mot de passe', submit: 'Définir le mot de passe', invalid: 'Ce lien est invalide ou a expiré.', mismatch: 'Les mots de passe ne correspondent pas.', failed: 'Impossible d’accepter l’invitation. Vérifiez le lien et réessayez.', done: 'Mot de passe défini. Le compte peut se connecter au client Web de test.' },
  pt_BR: { title: 'Convite para WORTA', detail: 'Teste fechado. Defina uma senha para a conta criada por um administrador.', password: 'Nova senha (pelo menos 15 caracteres)', confirm: 'Repita a senha', submit: 'Definir senha', invalid: 'Este link é inválido ou expirou.', mismatch: 'As senhas não coincidem.', failed: 'Não foi possível aceitar o convite. Confira o link e tente novamente.', done: 'Senha definida. A conta já pode entrar no cliente Web de teste.' },
}

const locale = useLocaleStore()
const words = computed(() => copy[locale.language])
const passwordInput = ref<HTMLInputElement | null>(null)
const confirmInput = ref<HTMLInputElement | null>(null)
const busy = ref(false)
const complete = ref(false)
const hasInvitation = ref(false)
const error = ref('')
let invitationToken: string | null = null

onMounted(() => {
  invitationToken = new URLSearchParams(window.location.hash.slice(1)).get('token')
  window.history.replaceState(window.history.state, '', window.location.pathname + window.location.search)
  hasInvitation.value = Boolean(invitationToken)
  if (!invitationToken) error.value = words.value.invalid
})
onBeforeUnmount(() => {
  invitationToken = null
  if (passwordInput.value) passwordInput.value.value = ''
  if (confirmInput.value) confirmInput.value.value = ''
})

async function submit(): Promise<void> {
  if (busy.value || !invitationToken || !passwordInput.value || !confirmInput.value) return
  const password = passwordInput.value.value
  const confirmation = confirmInput.value.value
  passwordInput.value.value = ''
  confirmInput.value.value = ''
  if (password !== confirmation) { error.value = words.value.mismatch; return }
  busy.value = true
  error.value = ''
  try {
    await invitationApi.accept(invitationToken, password)
    invitationToken = null
    hasInvitation.value = false
    complete.value = true
  } catch {
    error.value = words.value.failed
  } finally { busy.value = false }
}
</script>

<template>
  <main class="ion-page invitation-page">
    <section>
      <h1>{{ words.title }}</h1>
      <p>{{ words.detail }}</p>
      <p v-if="complete" role="status">{{ words.done }}</p>
      <p v-if="error" role="alert">{{ error }}</p>
      <form v-if="hasInvitation && !complete" @submit.prevent="submit">
        <label>{{ words.password }}<input ref="passwordInput" type="password" autocomplete="new-password" minlength="15" required /></label>
        <label>{{ words.confirm }}<input ref="confirmInput" type="password" autocomplete="new-password" minlength="15" required /></label>
        <button class="nf-button" :disabled="busy">{{ words.submit }}</button>
      </form>
    </section>
  </main>
</template>

<style scoped>
.invitation-page { min-height: 100dvh; display: grid; place-items: center; padding: 2rem; }
.invitation-page section { width: min(30rem, 100%); }
.invitation-page form, .invitation-page label { display: grid; gap: .7rem; }
.invitation-page form { margin-top: 1.5rem; }
.invitation-page input { padding: .65rem; border: 1px solid var(--nf-color-border); border-radius: .4rem; }
</style>
