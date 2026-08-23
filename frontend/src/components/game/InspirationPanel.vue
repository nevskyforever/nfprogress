<script setup lang="ts">
import { useLocaleStore } from '@/stores/locale'
import type { InspirationState } from '@/types/game'

defineProps<{
  inspiration: InspirationState
  points: number
  busy: boolean
}>()

const emit = defineEmits<{
  activate: [abilityId: string]
  resolve: [choice: 'safe' | 'risk']
}>()

const locale = useLocaleStore()
const t = locale.translate
</script>

<template>
  <article v-if="inspiration.creative_event" class="creative-event">
    <div>
      <span>{{ t('Творческое событие') }}</span>
      <h3>{{ t(inspiration.creative_event.name) }}</h3>
      <p>{{ t(inspiration.creative_event.description) }}</p>
    </div>
    <div class="choice-grid">
      <button
        type="button"
        class="choice-card"
        :disabled="busy"
        @click="emit('resolve', 'safe')"
      >
        <strong>{{ t('Надёжный выбор') }}</strong>
        <span>{{ t(inspiration.creative_event.safe_description) }}</span>
      </button>
      <button
        type="button"
        class="choice-card choice-card--risk"
        :disabled="busy"
        @click="emit('resolve', 'risk')"
      >
        <strong>{{ t('Рискнуть') }}</strong>
        <span>{{ t(inspiration.creative_event.risk_description) }}</span>
      </button>
    </div>
  </article>

  <div class="card-grid">
    <article v-for="ability in inspiration.abilities" :key="ability.key" class="feature-card">
      <span v-if="ability.active" class="status">{{ t('Ожидает применения') }}</span>
      <h3>{{ t(ability.name) }}</h3>
      <p>{{ t(ability.description) }}</p>
      <button
        class="nf-button"
        type="button"
        :disabled="busy || ability.active || points < ability.cost"
        @click="emit('activate', ability.key)"
      >
        {{ t('Активировать за {count}', { count: ability.cost }) }}
      </button>
    </article>
  </div>
</template>

<style scoped>
.creative-event {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(20rem, 1.2fr);
  gap: var(--nf-space-5);
  margin-bottom: var(--nf-space-5);
  padding: var(--nf-space-5);
  border: 1px solid color-mix(in srgb, var(--nf-color-accent) 45%, var(--nf-color-border));
  border-radius: var(--nf-radius-md);
  background: color-mix(in srgb, var(--nf-color-accent) 8%, var(--nf-color-surface));
}

.creative-event > div > span {
  color: var(--nf-color-accent);
  font-size: 0.75rem;
  font-weight: 800;
  letter-spacing: 0.1em;
  text-transform: uppercase;
}

.creative-event h3,
.feature-card h3,
.creative-event p,
.feature-card p {
  margin: 0;
}

.creative-event h3,
.feature-card h3 {
  font-family: var(--nf-font-serif);
}

.creative-event h3 {
  margin-top: var(--nf-space-1);
}

.creative-event p,
.feature-card p {
  color: var(--nf-color-text-muted);
  line-height: 1.5;
}

.choice-grid,
.card-grid {
  display: grid;
  gap: var(--nf-space-3);
}

.choice-grid {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.choice-card {
  display: grid;
  gap: var(--nf-space-2);
  min-height: 7rem;
  padding: var(--nf-space-4);
  border: 1px solid var(--nf-color-border);
  border-radius: var(--nf-radius-md);
  background: var(--nf-color-surface-raised);
  color: var(--nf-color-text);
  text-align: left;
  cursor: pointer;
}

.choice-card--risk {
  border-color: color-mix(in srgb, var(--nf-color-warning) 55%, var(--nf-color-border));
}

.choice-card span {
  color: var(--nf-color-text-muted);
  line-height: 1.4;
}

.choice-card:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

.card-grid {
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

.feature-card {
  display: grid;
  gap: var(--nf-space-3);
  padding: var(--nf-space-4);
  border: 1px solid var(--nf-color-border);
  border-radius: var(--nf-radius-md);
  background: var(--nf-color-surface-raised);
}

.feature-card .nf-button {
  align-self: end;
  width: fit-content;
}

.status {
  width: fit-content;
  padding: 0.35rem 0.6rem;
  border-radius: var(--nf-radius-pill);
  background: var(--nf-color-primary-soft);
  color: var(--nf-color-success);
  font-size: 0.75rem;
  font-weight: 800;
}

@media (max-width: 72rem) {
  .creative-event {
    grid-template-columns: 1fr;
  }

  .card-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 44rem) {
  .choice-grid,
  .card-grid {
    grid-template-columns: 1fr;
  }

  .feature-card .nf-button {
    width: 100%;
  }
}
</style>
