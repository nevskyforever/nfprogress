<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { adminSession } from '@/api/admin'

const router = useRouter()
const username = ref('')
const password = ref('')
const error = ref('')
const loading = ref(false)
async function submit(): Promise<void> {
  loading.value = true; error.value = ''
  try { await adminSession.login(username.value, password.value); await router.replace('/admin') }
  catch (reason) { error.value = reason instanceof Error ? reason.message : 'Не удалось войти.' }
  finally { loading.value = false }
}
</script>
<template><main class="admin-login"><form @submit.prevent="submit"><h1>Администрирование nfprogress</h1><label>Имя пользователя<input v-model="username" autocomplete="username" required /></label><label>Пароль<input v-model="password" type="password" autocomplete="current-password" required /></label><p v-if="error" role="alert">{{ error }}</p><button class="nf-button" :disabled="loading">{{ loading ? 'Входим…' : 'Войти' }}</button></form></main></template>
<style scoped>.admin-login{min-height:100dvh;display:grid;place-items:center;padding:2rem}.admin-login form{display:grid;gap:1rem;width:min(28rem,100%)}label{display:grid;gap:.35rem}input{padding:.65rem;border:1px solid var(--nf-color-border);border-radius:.4rem}</style>
