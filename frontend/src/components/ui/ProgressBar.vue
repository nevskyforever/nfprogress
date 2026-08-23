<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'

import { useMotionStore } from '@/stores/motion'

const props = defineProps<{
  value: number
  label: string
}>()
const motion = useMotionStore()

const targetValue = computed(() => Math.min(100, Math.max(0, props.value)))
const displayedValue = ref(0)
const animating = ref(false)
let animationFrame: number | undefined

const fillStyle = computed(() => ({
  transform: `scaleX(${displayedValue.value / 100})`,
}))

function stopAnimation(): void {
  if (animationFrame !== undefined) cancelAnimationFrame(animationFrame)
  animationFrame = undefined
  animating.value = false
}

function animateTo(target: number): void {
  stopAnimation()
  const from = displayedValue.value
  if (motion.reduced || Math.abs(target - from) < 0.01) {
    displayedValue.value = target
    return
  }

  const startedAt = performance.now()
  const duration = 900
  animating.value = true
  const tick = (now: number): void => {
    const progress = Math.min(1, (now - startedAt) / duration)
    displayedValue.value = from + (target - from) * (1 - (1 - progress) ** 3)
    if (progress < 1) animationFrame = requestAnimationFrame(tick)
    else {
      displayedValue.value = target
      animationFrame = undefined
      animating.value = false
    }
  }

  animationFrame = requestAnimationFrame(tick)
}

watch(targetValue, animateTo)
watch(() => motion.reduced, (reduced) => {
  if (reduced) {
    stopAnimation()
    displayedValue.value = targetValue.value
    return
  }
  displayedValue.value = 0
  animateTo(targetValue.value)
})
onMounted(() => animateTo(targetValue.value))
onBeforeUnmount(stopAnimation)
</script>

<template>
  <div
    class="progress-bar"
    :class="{ 'progress-bar--animating': animating }"
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
  position: relative;
  display: block;
  width: 100%;
  height: 100%;
  border-radius: inherit;
  overflow: hidden;
  background: linear-gradient(90deg, var(--nf-color-primary), var(--nf-color-accent));
  transform-origin: left center;
  will-change: transform;
}

.progress-bar__fill::after {
  position: absolute;
  inset: 0;
  background: linear-gradient(
    105deg,
    transparent 18%,
    rgb(255 255 255 / 45%) 48%,
    transparent 78%
  );
  content: '';
  opacity: 0;
  transform: translateX(-100%);
}

.progress-bar--animating .progress-bar__fill {
  animation: progress-bar-glow 900ms cubic-bezier(0.22, 1, 0.36, 1);
}

.progress-bar--animating .progress-bar__fill::after {
  animation: progress-bar-sheen 900ms cubic-bezier(0.22, 1, 0.36, 1);
}

:global(html[data-motion='reduced']) .progress-bar--animating .progress-bar__fill,
:global(html[data-motion='reduced']) .progress-bar--animating .progress-bar__fill::after {
  animation: none;
}

@keyframes progress-bar-glow {
  0% { filter: saturate(0.45); }
  45% { filter: saturate(1.25) drop-shadow(0 0 0.3rem color-mix(in srgb, var(--nf-color-primary) 35%, transparent)); }
  100% { filter: saturate(1); }
}

@keyframes progress-bar-sheen {
  0% { opacity: 0; transform: translateX(-100%); }
  22% { opacity: 0.7; }
  100% { opacity: 0; transform: translateX(100%); }
}
</style>
