<script setup lang="ts">
import { computed, ref } from 'vue'

import { useLocaleStore } from '@/stores/locale'
import type { BankState, GameBuffs, GameProfile, StreakFreezesState } from '@/types/game'

const props = defineProps<{
  profile: GameProfile
  bank: BankState
  buffs: GameBuffs
  streakFreezes: StreakFreezesState
  busy: boolean
}>()

const emit = defineEmits<{
  applyFreeze: [target: 'global' | 'project', projectId?: string]
}>()

const locale = useLocaleStore()
const t = locale.translate

const levelProgress = computed(() => {
  if (props.profile.next_level_experience === null) return 100
  if (props.profile.next_level_experience <= 0) return 0
  return Math.min(100, (props.profile.experience / props.profile.next_level_experience) * 100)
})

const pendingBonuses = computed(() =>
  Object.entries(props.profile.pending_bonuses).filter(([, value]) => value > 0),
)
const freezeTarget = ref('global')

const selectedFreezeProject = computed(() =>
  props.streakFreezes.projects.find((project) => project.project_id === freezeTarget.value),
)

function bonusName(key: string): string {
  const names: Record<string, string> = {
    writing: 'Запись текста',
    session: 'Писательская сессия',
    challenge: 'Испытание',
    manuscript: 'Рубеж рукописи',
  }
  return t(names[key] ?? key)
}
</script>

<template>
  <section class="overview" :aria-label="t('Состояние героя')">
    <div class="resource-grid">
      <article class="level-card resource-card">
        <p>{{ t('Уровень') }}</p>
        <strong>{{ profile.level }}</strong>
        <progress
          :value="levelProgress"
          max="100"
          :aria-label="t('Опыт до следующего уровня')"
        />
        <small v-if="profile.next_level_experience !== null">
          {{ locale.formatNumber(profile.experience, 0) }} /
          {{ locale.formatNumber(profile.next_level_experience, 0) }} {{ t('опыта') }}
        </small>
        <small v-else>{{ t('Максимальный уровень') }}</small>
      </article>

      <article class="resource-card">
        <p>{{ t('Монеты') }}</p>
        <strong>{{ locale.formatNumber(profile.coins) }}</strong>
        <small v-if="bank.credit">
          {{ t('Кредит') }}: {{ locale.formatNumber(bank.credit.remaining) }}
        </small>
        <small v-if="bank.deposit">
          {{ t('Вклад') }}: {{ locale.formatNumber(bank.deposit.total) }}
        </small>
      </article>

      <article class="resource-card">
        <p>{{ t('Здоровье') }}</p>
        <strong>{{ locale.formatNumber(profile.health) }} / {{ locale.formatNumber(profile.max_health) }}</strong>
        <progress
          :value="profile.health"
          :max="profile.max_health || 1"
          :aria-label="t('Запас здоровья')"
        />
      </article>

      <article class="resource-card">
        <p>{{ t('Вдохновение') }}</p>
        <strong>
          {{ locale.formatNumber(profile.inspiration) }} /
          {{ locale.formatNumber(profile.max_inspiration) }}
        </strong>
        <progress
          :value="profile.inspiration"
          :max="profile.max_inspiration || 1"
          :aria-label="t('Запас вдохновения')"
        />
      </article>

      <article class="resource-card">
        <p>{{ t('Серия сессий') }}</p>
        <strong>{{ profile.writing_session_streak }}</strong>
        <small>
          {{ t('Щиты') }}: {{ profile.session_streak_shields }} ·
          {{ t('Медали качества') }}: {{ profile.session_grade_boosts }}
        </small>
      </article>
    </div>

    <div v-if="pendingBonuses.length" class="summary-panel">
      <h2>{{ t('Ожидающие усиления') }}</h2>
      <ul class="tag-list">
        <li v-for="[key, value] in pendingBonuses" :key="key">
          {{ bonusName(key) }} +{{ locale.formatNumber(value * 100) }}%
        </li>
      </ul>
    </div>

    <section class="summary-panel freeze-panel" aria-labelledby="streak-freeze-title">
      <div>
        <h2 id="streak-freeze-title">{{ t('Заморозка серии') }}</h2>
        <p>
          {{ t('Сохраните серию на сегодня, если не получится написать текст.') }}
          {{ t('В инвентаре') }}: <strong>{{ streakFreezes.inventory_count }}</strong>
        </p>
      </div>
      <label>
        <span>{{ t('Серия') }}</span>
        <select v-model="freezeTarget" class="freeze-target-select">
          <option value="global">{{ t('Общая серия') }}</option>
          <option
            v-for="project in streakFreezes.projects"
            :key="project.project_id"
            :value="project.project_id"
          >
            {{ project.name }} · {{ project.source_count }}
          </option>
        </select>
      </label>
      <button
        class="nf-button"
        type="button"
        :disabled="
          busy ||
          (freezeTarget === 'global'
            ? !streakFreezes.global_available
            : (selectedFreezeProject?.source_count ?? 0) < 1)
        "
        @click="
          freezeTarget === 'global'
            ? emit('applyFreeze', 'global')
            : emit('applyFreeze', 'project', freezeTarget)
        "
      >
        {{ t('Применить заморозку') }}
      </button>
    </section>

    <div class="buff-columns">
      <section class="summary-panel">
        <h2>{{ t('Активные усиления') }}</h2>
        <p v-if="buffs.positive.length === 0" class="empty-copy">
          {{ t('Сейчас активных усилений нет.') }}
        </p>
        <ul v-else class="buff-list">
          <li v-for="buff in buffs.positive" :key="`${buff.name}:${buff.started_at}`">
            <strong>{{ t(buff.name) }}<span v-if="buff.stacks > 1"> ×{{ buff.stacks }}</span></strong>
            <span>{{ t(buff.description) }}</span>
          </li>
        </ul>
      </section>

      <section class="summary-panel">
        <h2>{{ t('Активные ограничения') }}</h2>
        <p v-if="buffs.negative.length === 0" class="empty-copy">
          {{ t('Сейчас активных ограничений нет.') }}
        </p>
        <ul v-else class="buff-list">
          <li v-for="buff in buffs.negative" :key="`${buff.name}:${buff.started_at}`">
            <strong>{{ t(buff.name) }}<span v-if="buff.stacks > 1"> ×{{ buff.stacks }}</span></strong>
            <span>{{ t(buff.description) }}</span>
          </li>
        </ul>
      </section>
    </div>
  </section>
</template>

<style scoped>
.overview,
.buff-columns {
  display: grid;
  gap: var(--nf-space-4);
}

.resource-grid {
  display: grid;
  grid-template-columns: repeat(5, minmax(9rem, 1fr));
  gap: var(--nf-space-3);
}

.resource-card,
.summary-panel {
  border: 1px solid var(--nf-color-border);
  border-radius: var(--nf-radius-md);
  background: var(--nf-color-surface);
  box-shadow: var(--nf-shadow-card);
}

.freeze-panel {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(12rem, auto) auto;
  gap: var(--nf-space-4);
  align-items: end;
}

.freeze-panel p {
  margin: 0;
  color: var(--nf-color-text-muted);
  line-height: 1.5;
}

.freeze-panel label {
  display: grid;
  gap: var(--nf-space-1);
  color: var(--nf-color-text-muted);
  font-size: 0.8rem;
  font-weight: 700;
}

.freeze-target-select {
  box-sizing: border-box;
  width: 100%;
  min-height: 2.75rem;
  padding: 0.6rem 0.7rem;
  border: 1px solid var(--nf-color-border);
  border-radius: var(--nf-radius-sm);
  background: var(--nf-color-surface-raised);
  color: var(--nf-color-text);
  font: inherit;
  font-weight: 700;
}

.resource-card {
  display: grid;
  gap: var(--nf-space-2);
  min-height: 8.5rem;
  padding: var(--nf-space-4);
  align-content: start;
}

.resource-card p,
.resource-card small,
.empty-copy {
  margin: 0;
  color: var(--nf-color-text-muted);
}

.resource-card strong {
  color: var(--nf-color-text);
  font-family: var(--nf-font-serif);
  font-size: clamp(1.35rem, 3vw, 2rem);
}

progress {
  width: 100%;
  height: 0.55rem;
  overflow: hidden;
  border: 0;
  border-radius: var(--nf-radius-pill);
  accent-color: var(--nf-color-primary);
}

.summary-panel {
  padding: var(--nf-space-5);
}

.summary-panel h2 {
  margin: 0 0 var(--nf-space-3);
  font-family: var(--nf-font-serif);
  font-size: 1.2rem;
}

.tag-list,
.buff-list {
  padding: 0;
  margin: 0;
  list-style: none;
}

.tag-list {
  display: flex;
  flex-wrap: wrap;
  gap: var(--nf-space-2);
}

.tag-list li {
  padding: 0.4rem 0.7rem;
  border-radius: var(--nf-radius-pill);
  background: var(--nf-color-primary-soft);
  color: var(--nf-color-primary);
  font-size: 0.875rem;
  font-weight: 700;
}

.buff-columns {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.buff-list {
  display: grid;
  gap: var(--nf-space-3);
}

.buff-list li {
  display: grid;
  gap: var(--nf-space-1);
}

.buff-list span {
  color: var(--nf-color-text-muted);
  line-height: 1.45;
}

@media (max-width: 75rem) {
  .resource-grid {
    grid-template-columns: repeat(3, minmax(10rem, 1fr));
  }
}

@media (max-width: 42rem) {
  .resource-grid,
  .buff-columns {
    grid-template-columns: 1fr;
  }

  .resource-card {
    min-height: 0;
  }

  .freeze-panel {
    grid-template-columns: 1fr;
  }

  .freeze-panel .nf-button {
    width: 100%;
  }
}
</style>
