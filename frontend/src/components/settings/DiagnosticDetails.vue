<script setup lang="ts">
import { useLocaleStore } from '@/stores/locale'
import { technicalCode } from '@/diagnostics/presentation'
import type { Subsystem, Operation } from '@/diagnostics/events'
defineProps<{ code: string; subsystem?: Subsystem; operation?: Operation; correlation?: string }>()
const t = useLocaleStore().translate
</script>
<template>
  <details class="diagnostic-details"><summary>{{ t('Технические сведения') }}</summary>
    <dl><dt>{{ t('Код') }}</dt><dd>{{ technicalCode(code) }}</dd>
      <template v-if="subsystem"><dt>{{ t('Подсистема') }}</dt><dd>{{ subsystem }}</dd></template>
      <template v-if="operation"><dt>{{ t('Операция') }}</dt><dd>{{ operation }}</dd></template>
      <template v-if="correlation && /^[0-9a-f-]{36}$/i.test(correlation)"><dt>{{ t('Номер обращения') }}</dt><dd>{{ correlation }}</dd></template>
    </dl>
  </details>
</template>
<style scoped>
dl { display:grid; grid-template-columns:auto 1fr; gap:.3rem 1rem; } dd { margin:0; overflow-wrap:anywhere; } summary { cursor:pointer; }
</style>
