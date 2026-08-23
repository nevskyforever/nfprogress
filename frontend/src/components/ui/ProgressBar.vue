<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'

const props = defineProps<{
  value: number
  label: string
}>()

const targetValue = computed(() => Math.min(100, Math.max(0, props.value)))
const displayedValue = ref(0)
let animationFrame: number | undefined

const fillStyle = computed(() => ({
  transform: `scaleX(${displayedValue.value / 100})`,
}))

function stopAnimation(): void {
  if (animationFrame !== undefined) cancelAnimationFrame(animationFrame)
  animationFrame = undefined
}

function reducedMotion(): boolean {
  return window.matchMedia?.('(prefers-reduced-motion: reduce)').matches ?? false
}

function animateTo(target: number): void {
  stopAnimation()
  const from = displayedValue.value
  if (reducedMotion() || Math.abs(target - from) < 0.01) {
    displayedValue.value = target
    return
  }

  const startedAt = performance.now()
  const duration = 680
  const tick = (now: number): void => {
    const progress = Math.min(1, (now - startedAt) / duration)
    displayedValue.value = from + (target - from) * (1 - (1 - progress) ** 3)
    if (progress < 1) animationFrame = requestAnimationFrame(tick)
    else {
      displayedValue.value = target
      animationFrame = undefined
    }
  }

  animationFrame = requestAnimationFrame(tick)
}

watch(targetValue, animateTo)
onMounted(() => animateTo(targetValue.value))
onBeforeUnmount(stopAnimation)
</script>

<template>
  <div
    class="progress-bar"
    role="progressbar"
    :aria-label="label"
    aria-valuemin="0"
    aria-valuemax="100"
    :aria-valuenow="Math.round(targetValue)"
  >
    <span class="progress-bar__fill" :style="fillStyle" />
  </div>
</template>

<style scoped>
.progress-bar {
  height: 0.75rem;
  overflow: hidden;
  border-radius: var(--nf-radius-pill);
  background: var(--nf-color-surface-muted);
}

.progress-bar__fill {
  display: block;
  width: 100%;
  height: 100%;
  border-radius: inherit;
  background: linear-gradient(90deg, var(--nf-color-primary), var(--nf-color-accent));
  transform-origin: left center;
  will-change: transform;
}
</style>
