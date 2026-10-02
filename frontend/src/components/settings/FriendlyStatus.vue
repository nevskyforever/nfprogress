<script setup lang="ts">
import { computed } from 'vue'
import { useLocaleStore } from '@/stores/locale'
import { presentStatus } from '@/diagnostics/presentation'
import type { Subsystem, Operation } from '@/diagnostics/events'
import DiagnosticDetails from './DiagnosticDetails.vue'
const props = defineProps<{ domain?: 'session' | 'project' | 'metadata' | 'structure' | 'catalog' | 'error'; code: string; subsystem?: Subsystem; operation?: Operation; correlation?: string; detailCode?: string }>()
const presentation = computed(() => presentStatus(props.domain ?? 'error', props.code))
const t = useLocaleStore().translate
</script>
<template>
  <div class="friendly-status" :data-severity="presentation.severity">
    <p><strong>{{ t(presentation.title) }}</strong></p><p>{{ t(presentation.description) }}</p>
    <p v-if="presentation.action">{{ t(presentation.action) }}</p>
    <DiagnosticDetails :code="detailCode ?? presentation.technicalCode" :subsystem="subsystem" :operation="operation" :correlation="correlation" />
  </div>
</template>
<style scoped>
p { margin:.25rem 0; } .friendly-status { overflow-wrap:anywhere; }
</style>
