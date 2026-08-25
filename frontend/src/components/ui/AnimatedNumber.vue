<script setup lang="ts">
import { onBeforeUnmount, ref, watch } from 'vue'

import { useLocaleStore } from '@/stores/locale'

const props = withDefaults(defineProps<{ value: number; digits?: number }>(), { digits: 0 })
const locale = useLocaleStore()
const displayed = ref(props.value)
let frame: number | undefined

watch(() => props.value, (next, previous) => {
  if (frame !== undefined) cancelAnimationFrame(frame)
  const startedAt = performance.now()
  const from = Number.isFinite(previous) ? previous : displayed.value
  const duration = 420
  const tick = (now: number) => {
    const progress = Math.min(1, (now - startedAt) / duration)
    const eased = 1 - (1 - progress) ** 3
    displayed.value = from + (next - from) * eased
    if (progress < 1) frame = requestAnimationFrame(tick)
  }
  frame = requestAnimationFrame(tick)
})

onBeforeUnmount(() => { if (frame !== undefined) cancelAnimationFrame(frame) })
</script>

<template><span class="animated-number">{{ locale.formatNumber(displayed, digits) }}</span></template>

<style scoped>
.animated-number { font-variant-numeric: tabular-nums; }
</style>
