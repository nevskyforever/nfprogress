<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { diagnostics, type DiagnosticStats } from '@/diagnostics/service'
import { useLocaleStore } from '@/stores/locale'
import FriendlyStatus from './FriendlyStatus.vue'
const t = useLocaleStore().translate
const stats = ref<DiagnosticStats>({ count: 0, bytes: 0, last_event_at: null })
const busy = ref(false), error = ref(false), done = ref('')
async function refresh() { stats.value = await diagnostics.stats(); error.value = stats.value.write_failed === true }
async function action(kind: 'copy' | 'export' | 'clear') {
  if (busy.value) return
  busy.value = true; error.value = false; done.value = ''
  try {
    const result = await diagnostics[kind]()
    if (kind !== 'export' || result !== false) done.value = kind === 'copy' ? 'Журнал скопирован.' : kind === 'export' ? 'Журнал экспортирован.' : 'Журнал очищен.'
    await refresh()
  } catch { error.value = true } finally { busy.value = false }
}
onMounted(() => { void refresh().catch(() => { error.value = true }) })
</script>
<template>
  <section class="settings-card" aria-labelledby="diagnostics-title">
    <h2 id="diagnostics-title">{{ t('Диагностика') }}</h2>
    <p>{{ t('Журнал хранится только на этом компьютере. Тексты, названия, пароли и ключи в него не записываются. Автоматической отправки нет.') }}</p>
    <p>{{ t('Событий') }}: {{ stats.count }} · {{ Math.ceil(stats.bytes / 1024) }} {{ t('КБ') }}</p>
    <p>{{ t('Последнее событие') }}: {{ stats.last_event_at ?? '—' }}</p>
    <p>{{ t('Очистите журнал, повторите проблему и скопируйте или экспортируйте результат для проверки.') }}</p>
    <div class="diagnostic-actions">
      <button class="nf-button" :disabled="busy" @click="action('copy')">{{ t('Скопировать журнал') }}</button>
      <button class="nf-button" :disabled="busy" @click="action('export')">{{ t('Экспортировать журнал') }}</button>
      <button class="nf-button nf-button--secondary" :disabled="busy" @click="action('clear')">{{ t('Очистить журнал') }}</button>
    </div>
    <p v-if="done" role="status">{{ t(done) }}</p>
    <FriendlyStatus v-if="error" code="diagnostic_storage_unavailable" subsystem="application" />
  </section>
</template>
<style scoped>
.diagnostic-actions {display:flex;gap:.5rem;flex-wrap:wrap;}
</style>
