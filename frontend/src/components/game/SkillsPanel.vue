<script setup lang="ts">
import { useLocaleStore } from '@/stores/locale'
import type { GameSkills } from '@/types/game'

defineProps<{
  skills: GameSkills
  busy: boolean
}>()

const emit = defineEmits<{
  increase: [skillId: string]
}>()

const locale = useLocaleStore()
const t = locale.translate
</script>

<template>
  <p class="notice">
    {{ t('Доступно очков навыков') }}: <strong>{{ skills.available_points }}</strong>
  </p>
  <div class="card-grid">
    <article v-for="skill in skills.items" :key="skill.key" class="feature-card">
      <h3>{{ t(skill.name) }}</h3>
      <strong class="skill-level">{{ skill.points }}</strong>
      <p>{{ t('Текущий бонус') }}: +{{ locale.formatNumber(skill.bonus * 100) }}%</p>
      <button
        class="nf-button"
        type="button"
        :disabled="busy || skills.available_points < 1"
        @click="emit('increase', skill.key)"
      >
        {{ t('Вложить 1 очко') }}
      </button>
    </article>
  </div>
  <details class="coefficients">
    <summary>{{ t('Подробные коэффициенты') }}</summary>
    <dl>
      <div v-for="coefficient in skills.coefficients" :key="coefficient.key">
        <dt>{{ t(coefficient.name) }}</dt>
        <dd>{{ locale.formatNumber(coefficient.value) }} · {{ t(coefficient.description) }}</dd>
      </div>
    </dl>
  </details>
</template>

<style scoped>
.notice,
.feature-card h3,
.feature-card p {
  margin: 0;
}

.notice,
.feature-card p {
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

.feature-card {
  display: grid;
  gap: var(--nf-space-3);
  padding: var(--nf-space-4);
  border: 1px solid var(--nf-color-border);
  border-radius: var(--nf-radius-md);
  background: var(--nf-color-surface-raised);
}

.feature-card h3 {
  font-family: var(--nf-font-serif);
}

.feature-card .nf-button {
  align-self: end;
  width: fit-content;
}

.skill-level {
  color: var(--nf-color-primary);
  font-size: 2rem;
}

.coefficients {
  margin-top: var(--nf-space-5);
  padding: var(--nf-space-4);
  border: 1px solid var(--nf-color-border);
  border-radius: var(--nf-radius-md);
}

.coefficients summary {
  cursor: pointer;
  font-weight: 750;
}

.coefficients dl {
  display: grid;
  gap: var(--nf-space-2);
  margin: var(--nf-space-4) 0 0;
}

.coefficients dl div {
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

@media (max-width: 72rem) {
  .card-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 44rem) {
  .card-grid {
    grid-template-columns: 1fr;
  }

  .feature-card .nf-button {
    width: 100%;
  }
}
</style>
