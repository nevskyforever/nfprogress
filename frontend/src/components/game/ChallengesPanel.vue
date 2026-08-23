<script setup lang="ts">
import { computed } from 'vue'

import { useLocaleStore } from '@/stores/locale'
import type { DailyChallengeState, WeeklyChallengeState } from '@/types/game'

const props = defineProps<{
  daily: DailyChallengeState
  weekly: WeeklyChallengeState
  inspiration: number
  busy: boolean
}>()

const emit = defineEmits<{
  selectDaily: [optionId: string]
  startWeekly: [challengeId: string]
}>()

const locale = useLocaleStore()
const t = locale.translate

const canChangeDaily = computed(() => props.inspiration >= props.daily.change_cost)
</script>

<template>
  <div class="challenge-grid">
    <section class="game-panel" :aria-labelledby="'daily-challenge-title'">
      <header>
        <div>
          <p>{{ t('Сегодня') }}</p>
          <h2 id="daily-challenge-title">{{ t('Дневное испытание') }}</h2>
        </div>
        <span v-if="daily.current?.completed" class="status status--success">
          {{ t('Выполнено') }}
        </span>
      </header>

      <article v-if="daily.current" class="current-challenge">
        <h3>{{ t(daily.current.name) }} · {{ t(daily.current.difficulty_name) }}</h3>
        <p>{{ t(daily.current.description) }}</p>
        <progress
          :value="daily.current.progress"
          :max="daily.current.target || 1"
          :aria-label="t('Прогресс дневного испытания')"
        />
        <strong>
          {{ locale.formatNumber(daily.current.progress, 0) }} /
          {{ locale.formatNumber(daily.current.target, 0) }}
        </strong>
        <small>
          {{ t('Награда') }}: {{ locale.formatNumber(daily.current.reward.coins) }}
          {{ t('монет') }}, {{ locale.formatNumber(daily.current.reward.experience) }}
          {{ t('опыта') }}
        </small>
      </article>

      <div class="option-list" :aria-label="t('Варианты дневного испытания')">
        <article v-for="option in daily.options" :key="option.option_id" class="option-card">
          <div>
            <strong>{{ t(option.name) }}</strong>
            <span>{{ t(option.difficulty_name) }} · {{ locale.formatNumber(option.target, 0) }}</span>
          </div>
          <button
            class="nf-button nf-button--secondary"
            type="button"
            :disabled="
              busy ||
              option.option_id === daily.current?.option_id ||
              (daily.current !== null && !canChangeDaily)
            "
            @click="emit('selectDaily', option.option_id)"
          >
            {{
              option.option_id === daily.current?.option_id
                ? t('Выбрано')
                : daily.current
                  ? t('Сменить за {count}', { count: daily.change_cost })
                  : t('Выбрать')
            }}
          </button>
        </article>
      </div>
      <p v-if="daily.current && !canChangeDaily" class="hint">
        {{ t('Для смены испытания не хватает вдохновения.') }}
      </p>
    </section>

    <section class="game-panel" :aria-labelledby="'weekly-challenge-title'">
      <header>
        <div>
          <p>{{ t('Эта неделя') }}</p>
          <h2 id="weekly-challenge-title">{{ t('Недельное испытание') }}</h2>
        </div>
        <span v-if="weekly.current?.completed" class="status status--success">
          {{ t('Выполнено') }}
        </span>
      </header>

      <article v-if="weekly.current" class="current-challenge">
        <h3>{{ t(weekly.current.name) }}</h3>
        <p>{{ t(weekly.current.description) }}</p>
        <progress
          :value="weekly.current.progress ?? 0"
          :max="weekly.current.target || 1"
          :aria-label="t('Прогресс недельного испытания')"
        />
        <strong>
          {{ locale.formatNumber(weekly.current.progress ?? 0, 0) }} /
          {{ locale.formatNumber(weekly.current.target, 0) }}
        </strong>
        <small>
          {{ t('Награда') }}: {{ locale.formatNumber(weekly.current.reward.coins) }}
          {{ t('монет') }}, {{ locale.formatNumber(weekly.current.reward.experience) }}
          {{ t('опыта') }}
        </small>
      </article>

      <div v-else class="option-list" :aria-label="t('Варианты недельного испытания')">
        <article v-for="challenge in weekly.catalog" :key="challenge.key" class="option-card">
          <div>
            <strong>{{ t(challenge.name) }}</strong>
            <span>{{ t(challenge.description) }}</span>
          </div>
          <button
            class="nf-button nf-button--secondary"
            type="button"
            :disabled="busy"
            @click="emit('startWeekly', challenge.key)"
          >
            {{ t('Начать') }}
          </button>
        </article>
      </div>
    </section>
  </div>
</template>

<style scoped>
.challenge-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: var(--nf-space-4);
  align-items: start;
}

.game-panel {
  padding: var(--nf-space-5);
  border: 1px solid var(--nf-color-border);
  border-radius: var(--nf-radius-lg);
  background: var(--nf-color-surface);
  box-shadow: var(--nf-shadow-card);
}

header,
.option-card,
.option-card > div {
  display: flex;
  gap: var(--nf-space-3);
}

header,
.option-card {
  align-items: center;
  justify-content: space-between;
}

header p,
header h2,
.current-challenge h3,
.current-challenge p,
.hint {
  margin: 0;
}

header p {
  color: var(--nf-color-accent);
  font-size: 0.75rem;
  font-weight: 800;
  letter-spacing: 0.1em;
  text-transform: uppercase;
}

header h2,
.current-challenge h3 {
  font-family: var(--nf-font-serif);
}

.status {
  padding: 0.4rem 0.65rem;
  border-radius: var(--nf-radius-pill);
  font-size: 0.8rem;
  font-weight: 800;
}

.status--success {
  background: var(--nf-color-primary-soft);
  color: var(--nf-color-success);
}

.current-challenge {
  display: grid;
  gap: var(--nf-space-2);
  margin-top: var(--nf-space-5);
  padding: var(--nf-space-4);
  border-radius: var(--nf-radius-md);
  background: var(--nf-color-surface-muted);
}

.current-challenge p,
.current-challenge small,
.option-card span,
.hint {
  color: var(--nf-color-text-muted);
  line-height: 1.45;
}

progress {
  width: 100%;
  height: 0.65rem;
  margin-top: var(--nf-space-2);
  accent-color: var(--nf-color-primary);
}

.option-list {
  display: grid;
  gap: var(--nf-space-2);
  margin-top: var(--nf-space-4);
}

.option-card {
  padding: var(--nf-space-3) 0;
  border-bottom: 1px solid var(--nf-color-border);
}

.option-card > div {
  min-width: 0;
  flex-direction: column;
  gap: var(--nf-space-1);
}

.option-card .nf-button {
  flex: 0 0 auto;
}

.hint {
  margin-top: var(--nf-space-3);
  font-size: 0.875rem;
}

@media (max-width: 62rem) {
  .challenge-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 38rem) {
  .game-panel {
    padding: var(--nf-space-4);
  }

  .option-card {
    align-items: stretch;
    flex-direction: column;
  }

  .option-card .nf-button {
    width: 100%;
  }
}
</style>
