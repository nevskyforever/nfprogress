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
const RING_CIRCUMFERENCE = 2 * Math.PI * 46

function legacyProgressColor(progress: number): string {
  const ratio = Math.min(1, Math.max(0, progress / 100))
  const start = { red: 169, green: 169, blue: 169 }
  const end = { red: 37, green: 104, blue: 172 }
  const channel = (from: number, to: number) => Math.round(from + (to - from) * ratio)

  return `rgb(${channel(start.red, end.red)}, ${channel(start.green, end.green)}, ${channel(start.blue, end.blue)})`
}

const ringStyle = computed(() => ({
  strokeDasharray: `${RING_CIRCUMFERENCE}`,
  strokeDashoffset: `${RING_CIRCUMFERENCE * (1 - normalizedValue.value / 100)}`,
  stroke: legacyProgressColor(normalizedValue.value),
}))
</script>

<template>
  <div
    class="progress-ring"
    :class="[`progress-ring--${size}`, { 'progress-ring--infinite': infinite }]"
    role="img"
    :aria-label="label"
  >
    <svg class="progress-ring__svg" viewBox="0 0 100 100" aria-hidden="true">
      <circle class="progress-ring__track" cx="50" cy="50" r="46" />
      <circle
        class="progress-ring__value"
        :class="{ 'progress-ring__value--infinite': infinite }"
        cx="50"
        cy="50"
        r="46"
        :style="infinite ? undefined : ringStyle"
      />
    </svg>
    <span aria-hidden="true">{{ infinite ? '∞' : `${Math.round(normalizedValue)}%` }}</span>
  </div>
</template>

<style scoped>
.progress-ring {
  --ring-size: 4.75rem;
  --ring-stroke: 2.15;
  display: grid;
  position: relative;
  width: var(--ring-size);
  height: var(--ring-size);
  flex: 0 0 var(--ring-size);
  place-items: center;
  border-radius: 50%;
}

.progress-ring__svg {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  transform: rotate(-90deg);
}

.progress-ring__track,
.progress-ring__value {
  fill: none;
  stroke-width: var(--ring-stroke);
  stroke-linecap: round;
}

.progress-ring__track { stroke: var(--nf-color-progress-track); }
.progress-ring__value {
  stroke: var(--nf-color-progress);
  transition: stroke-dashoffset 500ms cubic-bezier(0.22, 1, 0.36, 1), stroke 500ms ease;
}
.progress-ring__value--infinite { stroke-dasharray: 5 4; }

@media (prefers-reduced-motion: reduce) {
  .progress-ring__value { transition: none; }
}

.progress-ring span {
  color: var(--nf-color-text);
  font-family: var(--nf-font-serif);
  font-size: 1.1rem;
  font-weight: 800;
}

.progress-ring--large {
  --ring-size: clamp(6.5rem, 11vw, 8rem);
  --ring-stroke: 1.9;
}

.progress-ring--large span {
  font-size: clamp(1.35rem, 2.7vw, 1.85rem);
}

</style>
