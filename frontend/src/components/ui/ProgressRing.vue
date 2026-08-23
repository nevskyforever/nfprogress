<script setup lang="ts">
import { computed } from 'vue'

const props = withDefaults(
  defineProps<{
    value: number
    label: string
    infinite?: boolean
    size?: 'small' | 'large'
  }>(),
  { infinite: false, size: 'small' },
)

const normalizedValue = computed(() => Math.min(100, Math.max(0, props.value)))
const ringStyle = computed(() => ({ '--progress': `${normalizedValue.value * 3.6}deg` }))
</script>

<template>
  <div
    class="progress-ring"
    :class="[`progress-ring--${size}`, { 'progress-ring--infinite': infinite }]"
    :style="ringStyle"
    role="img"
    :aria-label="label"
  >
    <span aria-hidden="true">{{ infinite ? '∞' : `${Math.round(normalizedValue)}%` }}</span>
  </div>
</template>

<style scoped>
.progress-ring {
  --ring-size: 5.5rem;
  --ring-width: 0.48rem;
  display: grid;
  width: var(--ring-size);
  height: var(--ring-size);
  flex: 0 0 var(--ring-size);
  place-items: center;
  border-radius: 50%;
  background:
    radial-gradient(circle, var(--nf-color-surface) calc(50% - var(--ring-width)), transparent calc(50% - var(--ring-width) + 1px)),
    conic-gradient(var(--nf-color-primary) var(--progress), var(--nf-color-surface-muted) 0);
  box-shadow: inset 0 0 0 1px color-mix(in srgb, var(--nf-color-border) 35%, transparent);
}

.progress-ring span {
  color: var(--nf-color-text);
  font-family: var(--nf-font-serif);
  font-size: 1.1rem;
  font-weight: 800;
}

.progress-ring--large {
  --ring-size: clamp(8.25rem, 17vw, 11rem);
  --ring-width: 0.7rem;
}

.progress-ring--large span {
  font-size: clamp(1.65rem, 4vw, 2.35rem);
}

.progress-ring--infinite {
  background:
    radial-gradient(circle, var(--nf-color-surface) calc(50% - var(--ring-width)), transparent calc(50% - var(--ring-width) + 1px)),
    repeating-conic-gradient(
      var(--nf-color-primary) 0 12deg,
      var(--nf-color-primary-soft) 12deg 24deg
    );
}
</style>
