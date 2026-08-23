<script setup lang="ts">
import { computed } from 'vue'

import { useLocaleStore } from '@/stores/locale'
import type { SpecializationsState } from '@/types/game'

const props = defineProps<{
  specializations: SpecializationsState
  level: number
  busy: boolean
}>()

const emit = defineEmits<{
  select: [specializationId: string]
  activate: []
}>()

const locale = useLocaleStore()
const t = locale.translate
const selected = computed(() => props.specializations.items.find((item) => item.selected))

function formatDuration(seconds: number): string {
  if (seconds <= 0) return t('Готово')
  const hours = Math.floor(seconds / 3_600)
  const minutes = Math.ceil((seconds % 3_600) / 60)
  if (hours > 0) return t('{hours} ч {minutes} мин', { hours, minutes })
  return t('{minutes} мин', { minutes })
}
</script>

<template>
  <p v-if="level < specializations.unlocks_at_level" class="notice">
    {{ t('Специализации откроются на уровне {level}.', { level: specializations.unlocks_at_level }) }}
  </p>
  <p v-else-if="specializations.change_days_remaining > 0" class="notice">
    {{ t('Сменить специализацию можно через {days} дн.', { days: specializations.change_days_remaining }) }}
  </p>

  <div class="card-grid">
    <article
      v-for="item in specializations.items"
      :key="item.key"
      class="feature-card"
      :class="{ 'feature-card--selected': item.selected }"
    >
      <span v-if="item.selected" class="status">{{ t('Выбрано') }}</span>
      <h3>{{ t(item.name) }}</h3>
      <p>{{ t(item.description) }}</p>
      <dl>
        <div><dt>{{ t('Ранг мастерства') }}</dt><dd>{{ item.mastery_rank }}</dd></div>
        <div>
          <dt>{{ t('Опыт мастерства') }}</dt>
          <dd>{{ locale.formatNumber(item.mastery_experience, 0) }}</dd>
        </div>
        <div>
          <dt>{{ t('Пассивный бонус') }}</dt>
          <dd>+{{ locale.formatNumber(item.passive_bonus * 100) }}%</dd>
        </div>
      </dl>
      <button
        class="nf-button nf-button--secondary"
        type="button"
        :disabled="
          busy ||
          item.selected ||
          level < specializations.unlocks_at_level ||
          specializations.change_days_remaining > 0
        "
        @click="emit('select', item.key)"
      >
        {{ item.selected ? t('Выбрано') : t('Выбрать специализацию') }}
      </button>
    </article>
  </div>

  <article v-if="selected" class="active-ability">
    <div>
      <span>{{ t('Активная способность') }}</span>
      <h3>{{ t(selected.ability.name) }}</h3>
      <p>{{ t(selected.ability.description) }}</p>
    </div>
    <button
      class="nf-button"
      type="button"
      :disabled="busy || selected.ability.remaining_seconds > 0 || selected.ability.pending"
      @click="emit('activate')"
    >
      <template v-if="selected.ability.pending">{{ t('Эффект ожидает применения') }}</template>
      <template v-else-if="selected.ability.remaining_seconds > 0">
        {{ formatDuration(selected.ability.remaining_seconds) }}
      </template>
      <template v-else>{{ t('Активировать') }}</template>
    </button>
  </article>
</template>

<style scoped>
.notice,
.feature-card h3,
.feature-card p,
.active-ability h3,
.active-ability p {
  margin: 0;
}

.notice,
.feature-card p,
.active-ability p {
  color: var(--nf-color-text-muted);
  line-height: 1.5;
}

.notice {
  margin-bottom: var(--nf-space-4);
}

.card-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: var(--nf-space-3);
}

.feature-card,
.active-ability {
  border: 1px solid var(--nf-color-border);
  border-radius: var(--nf-radius-md);
  background: var(--nf-color-surface-raised);
}

.feature-card {
  display: grid;
  gap: var(--nf-space-3);
  padding: var(--nf-space-4);
}

.feature-card--selected {
  border-color: var(--nf-color-primary);
  background: var(--nf-color-primary-soft);
}

.feature-card h3,
.active-ability h3 {
  font-family: var(--nf-font-serif);
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

.feature-card dl {
  display: grid;
  gap: var(--nf-space-2);
  margin: 0;
}

.feature-card dl div {
  display: flex;
  gap: var(--nf-space-2);
  justify-content: space-between;
}

dt {
  color: var(--nf-color-text-muted);
}

dd {
  margin: 0;
  font-weight: 750;
}

.active-ability {
  display: flex;
  gap: var(--nf-space-4);
  align-items: center;
  justify-content: space-between;
  margin-top: var(--nf-space-4);
  padding: var(--nf-space-5);
}

.active-ability > div > span {
  color: var(--nf-color-accent);
  font-size: 0.75rem;
  font-weight: 800;
  letter-spacing: 0.1em;
  text-transform: uppercase;
}

.active-ability h3 {
  margin-top: var(--nf-space-1);
}

@media (max-width: 72rem) {
  .card-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 44rem) {
  .card-grid {
    grid-template-columns: 1fr;
  }

  .active-ability {
    align-items: stretch;
    flex-direction: column;
  }

  .active-ability .nf-button,
  .feature-card .nf-button {
    width: 100%;
  }
}
</style>
