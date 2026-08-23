<script setup lang="ts">
import { ref } from 'vue'

import { useLocaleStore } from '@/stores/locale'
import type { ManuscriptsState } from '@/types/game'

defineProps<{
  manuscripts: ManuscriptsState
}>()

const locale = useLocaleStore()
const t = locale.translate
const view = ref<'relics' | 'sets' | 'journeys'>('relics')
</script>

<template>
  <section class="game-panel" :aria-labelledby="'cabinet-title'">
    <header class="panel-heading">
      <div>
        <p>{{ t('Достижения рукописей') }}</p>
        <h2 id="cabinet-title">{{ t('Кабинет реликвий') }}</h2>
      </div>
      <div class="view-switch" role="tablist" :aria-label="t('Раздел кабинета')">
        <button
          v-for="item in (['relics', 'sets', 'journeys'] as const)"
          :key="item"
          type="button"
          role="tab"
          :aria-selected="view === item"
          :class="{ active: view === item }"
          @click="view = item"
        >
          {{ t({ relics: 'Реликвии', sets: 'Наборы', journeys: 'Рукописи' }[item]) }}
        </button>
      </div>
    </header>

    <div v-if="view === 'relics'" class="card-grid">
      <article
        v-for="relic in manuscripts.cabinet.relics"
        :key="relic.key"
        class="relic-card"
        :class="{ 'relic-card--locked': !relic.unlocked }"
      >
        <span class="status" :class="{ 'status--unlocked': relic.unlocked }">
          {{ relic.unlocked ? t('Открыто') : t('Закрыто') }}
        </span>
        <h3>{{ relic.unlocked ? t(relic.name ?? relic.key) : t('Неизвестная реликвия') }}</h3>
        <p>{{ relic.unlocked ? t(relic.description ?? '') : t(relic.condition) }}</p>
        <progress
          :value="relic.progress"
          :max="relic.required || 1"
          :aria-label="t('Прогресс открытия реликвии')"
        />
        <small>{{ locale.formatNumber(relic.progress) }} / {{ locale.formatNumber(relic.required) }}</small>
        <strong v-if="relic.unlocked && relic.effect_description">
          {{ t(relic.effect_description) }}
        </strong>
      </article>
    </div>

    <div v-else-if="view === 'sets'" class="card-grid">
      <article
        v-for="collection in manuscripts.cabinet.sets"
        :key="collection.key"
        class="relic-card"
        :class="{ 'relic-card--locked': !collection.unlocked }"
      >
        <span class="status" :class="{ 'status--unlocked': collection.unlocked }">
          {{ collection.unlocked ? t('Собрано') : t('Не собрано') }}
        </span>
        <h3>{{ t(collection.name) }}</h3>
        <p>{{ t(collection.description) }}</p>
        <small>{{ t('Реликвий в наборе') }}: {{ collection.relics.length }}</small>
        <strong v-if="collection.unlocked">
          {{ t('Бонус набора') }}: +{{ locale.formatNumber(collection.bonus * 100) }}%
        </strong>
      </article>
    </div>

    <div v-else class="journey-list">
      <p v-if="manuscripts.journeys.length === 0" class="empty-copy">
        {{ t('Рубежи рукописей появятся после работы над проектами.') }}
      </p>
      <article v-for="journey in manuscripts.journeys" v-else :key="journey.owner_key">
        <h3>{{ journey.owner_name ?? t('Удалённая рукопись') }}</h3>
        <p>{{ t('Полученные рубежи') }}</p>
        <ul>
          <li v-for="milestone in journey.received_milestones" :key="milestone">
            {{ milestone }}%
          </li>
        </ul>
      </article>
    </div>
  </section>
</template>

<style scoped>
.game-panel {
  padding: var(--nf-space-5);
  border: 1px solid var(--nf-color-border);
  border-radius: var(--nf-radius-lg);
  background: var(--nf-color-surface);
  box-shadow: var(--nf-shadow-card);
}

.panel-heading {
  display: flex;
  gap: var(--nf-space-4);
  align-items: center;
  justify-content: space-between;
}

.panel-heading p,
.panel-heading h2,
.relic-card h3,
.relic-card p,
.journey-list h3,
.journey-list p,
.empty-copy {
  margin: 0;
}

.panel-heading p {
  color: var(--nf-color-accent);
  font-size: 0.75rem;
  font-weight: 800;
  letter-spacing: 0.1em;
  text-transform: uppercase;
}

.panel-heading h2,
.relic-card h3,
.journey-list h3 {
  font-family: var(--nf-font-serif);
}

.view-switch {
  display: inline-flex;
  max-width: 100%;
  padding: var(--nf-space-1);
  overflow-x: auto;
  border: 1px solid var(--nf-color-border);
  border-radius: var(--nf-radius-pill);
  background: var(--nf-color-surface-muted);
}

.view-switch button {
  flex: 0 0 auto;
  min-height: 2.4rem;
  padding: 0.45rem 0.75rem;
  border: 0;
  border-radius: var(--nf-radius-pill);
  background: transparent;
  color: var(--nf-color-text-muted);
  cursor: pointer;
}

.view-switch button.active {
  background: var(--nf-color-surface-raised);
  color: var(--nf-color-primary);
  font-weight: 750;
}

.card-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: var(--nf-space-3);
  margin-top: var(--nf-space-5);
}

.relic-card {
  display: grid;
  gap: var(--nf-space-3);
  min-width: 0;
  padding: var(--nf-space-4);
  border: 1px solid var(--nf-color-border);
  border-radius: var(--nf-radius-md);
  background: var(--nf-color-surface-raised);
}

.relic-card--locked {
  background: var(--nf-color-surface-muted);
}

.relic-card p,
.relic-card small,
.journey-list p,
.empty-copy {
  color: var(--nf-color-text-muted);
  line-height: 1.5;
}

.status {
  width: fit-content;
  padding: 0.35rem 0.6rem;
  border-radius: var(--nf-radius-pill);
  background: var(--nf-color-surface-muted);
  color: var(--nf-color-text-muted);
  font-size: 0.75rem;
  font-weight: 800;
}

.status--unlocked {
  background: var(--nf-color-primary-soft);
  color: var(--nf-color-success);
}

progress {
  width: 100%;
  height: 0.6rem;
  accent-color: var(--nf-color-primary);
}

.journey-list {
  display: grid;
  gap: var(--nf-space-3);
  margin-top: var(--nf-space-5);
}

.journey-list article {
  padding: var(--nf-space-4);
  border: 1px solid var(--nf-color-border);
  border-radius: var(--nf-radius-md);
}

.journey-list ul {
  display: flex;
  flex-wrap: wrap;
  gap: var(--nf-space-2);
  padding: 0;
  margin: var(--nf-space-3) 0 0;
  list-style: none;
}

.journey-list li {
  padding: 0.4rem 0.65rem;
  border-radius: var(--nf-radius-pill);
  background: var(--nf-color-primary-soft);
  color: var(--nf-color-primary);
  font-weight: 750;
}

@media (max-width: 68rem) {
  .card-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 44rem) {
  .game-panel {
    padding: var(--nf-space-4);
  }

  .panel-heading {
    align-items: stretch;
    flex-direction: column;
  }

  .card-grid {
    grid-template-columns: 1fr;
  }
}
</style>
