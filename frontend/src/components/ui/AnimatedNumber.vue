<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'

import { useLocaleStore } from '@/stores/locale'
import { useMotionStore } from '@/stores/motion'

const props = withDefaults(defineProps<{ value: number; digits?: number }>(), { digits: 0 })
const locale = useLocaleStore()
const motion = useMotionStore()
const displayed = ref(0)
let frame: number | undefined

function animate(next: number): void {
  if (frame !== undefined) cancelAnimationFrame(frame)
  if (motion.reduced) {
    displayed.value = next
    return
  }
  const startedAt = performance.now()
  const from = displayed.value
  const duration = 420
  const tick = (now: number) => {
    const progress = Math.min(1, (now - startedAt) / duration)
    const eased = 1 - (1 - progress) ** 3
    displayed.value = from + (next - from) * eased
    if (progress < 1) frame = requestAnimationFrame(tick)
  }
  frame = requestAnimationFrame(tick)
}

watch(() => props.value, animate)
watch(() => motion.reduced, () => animate(props.value))
onMounted(() => animate(props.value))

onBeforeUnmount(() => { if (frame !== undefined) cancelAnimationFrame(frame) })
</script>

<template><span class="animated-number">{{ locale.formatNumber(displayed, digits) }}</span></template>

<style scoped>
.animated-number { font-variant-numeric: tabular-nums; }
</style>
