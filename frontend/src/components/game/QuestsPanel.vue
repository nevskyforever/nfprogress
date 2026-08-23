<script setup lang="ts">
import { useLocaleStore } from '@/stores/locale'
import type { GameQuests } from '@/types/game'

defineProps<{
  quests: GameQuests
  level: number
  busy: boolean
}>()

const emit = defineEmits<{
  start: [questId: string]
  abandon: [questId: string]
}>()

const locale = useLocaleStore()
const t = locale.translate

function questStatus(status: string): string {
  const labels: Record<string, string> = {
    available: 'Доступно',
    active: 'Выполняется',
    completed: 'Выполнено',
  }
  return t(labels[status] ?? status)
}
</script>

<template>
  <div class="quest-list">
    <p v-if="quests.items.length === 0" class="notice">{{ t('Заданий пока нет.') }}</p>
    <article v-for="quest in quests.items" v-else :key="quest.id" class="quest-card">
      <div>
        <span class="status" :class="`status--${quest.status}`">{{ questStatus(quest.status) }}</span>
        <h3>{{ t(quest.name) }}</h3>
        <p>{{ t(quest.description) }}</p>
        <small>
          {{ t('Награда') }}: {{ locale.formatNumber(quest.reward.coins) }} {{ t('монет') }} ·
          {{ locale.formatNumber(quest.reward.experience) }} {{ t('опыта') }}
        </small>
      </div>
      <button
        v-if="quest.status === 'available'"
        class="nf-button"
        type="button"
        :disabled="busy || level < quest.required_level"
        @click="emit('start', quest.id)"
      >
        {{ level < quest.required_level ? t('Нужен уровень {level}', { level: quest.required_level }) : t('Начать') }}
      </button>
      <button
        v-else-if="quest.status === 'active'"
        class="nf-button nf-button--secondary"
        type="button"
        :disabled="busy"
        @click="emit('abandon', quest.id)"
      >
        {{ t('Отказаться') }}
      </button>
    </article>
  </div>
</template>

<style scoped>
.quest-list {
  display: grid;
  gap: var(--nf-space-3);
}

.notice,
.quest-card h3,
.quest-card p {
  margin: 0;
}

.notice,
.quest-card p,
.quest-card small {
  color: var(--nf-color-text-muted);
  line-height: 1.5;
}

.quest-card {
  display: flex;
  gap: var(--nf-space-4);
  align-items: center;
  justify-content: space-between;
  padding: var(--nf-space-4);
  border: 1px solid var(--nf-color-border);
  border-radius: var(--nf-radius-md);
  background: var(--nf-color-surface-raised);
}

.quest-card > div {
  display: grid;
  gap: var(--nf-space-2);
}

.quest-card h3 {
  font-family: var(--nf-font-serif);
}

.quest-card .nf-button {
  flex: 0 0 auto;
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

.status--active,
.status--completed {
  background: var(--nf-color-primary-soft);
  color: var(--nf-color-success);
}

@media (max-width: 44rem) {
  .quest-card {
    align-items: stretch;
    flex-direction: column;
  }

  .quest-card .nf-button {
    width: 100%;
  }
}
</style>
