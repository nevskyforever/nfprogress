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
  --ring-size: 4.75rem;
  --ring-width: 0.28rem;
  display: grid;
  width: var(--ring-size);
  height: var(--ring-size);
  flex: 0 0 var(--ring-size);
  place-items: center;
  border-radius: 50%;
  background:
    radial-gradient(circle, var(--nf-color-surface) calc(50% - var(--ring-width)), transparent calc(50% - var(--ring-width) + 1px)),
    conic-gradient(var(--nf-color-progress) var(--progress), var(--nf-color-progress-track) 0);
  box-shadow: inset 0 0 0 1px color-mix(in srgb, var(--nf-color-border) 35%, transparent);
}

.progress-ring span {
  color: var(--nf-color-text);
  font-family: var(--nf-font-serif);
  font-size: 1.1rem;
  font-weight: 800;
}

.progress-ring--large {
  --ring-size: clamp(6.5rem, 11vw, 8rem);
  --ring-width: 0.36rem;
}

.progress-ring--large span {
  font-size: clamp(1.35rem, 2.7vw, 1.85rem);
}

.progress-ring--infinite {
  background:
    radial-gradient(circle, var(--nf-color-surface) calc(50% - var(--ring-width)), transparent calc(50% - var(--ring-width) + 1px)),
    repeating-conic-gradient(
      var(--nf-color-progress) 0 12deg,
      var(--nf-color-progress-track) 12deg 24deg
    );
}
</style>
