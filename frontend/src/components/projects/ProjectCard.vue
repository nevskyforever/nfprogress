<script setup lang="ts">
import { computed } from 'vue'
import { IonIcon } from '@ionic/vue'
import { calendarClearOutline, layersOutline } from 'ionicons/icons'

import { useProjectPresentation } from '@/composables/useProjectPresentation'
import StreakBadge from '@/components/projects/StreakBadge.vue'
import ProgressRing from '@/components/ui/ProgressRing.vue'
import { useLocaleStore } from '@/stores/locale'
import type { Project } from '@/types/api'

const props = withDefaults(defineProps<{
  project: Project
  streaksEnabled?: boolean
}>(), {
  streaksEnabled: false,
})
const locale = useLocaleStore()
const t = locale.translate
const presentation = useProjectPresentation(() => props.project)

const stageCountLabel = computed(() => {
  const count = props.project.stages.length
  return `${t('Этапов')}: ${locale.formatNumber(count, 0)}`
})

const isOverdue = computed(() => {
  if (!props.project.deadline || props.project.status !== 'активен') return false
  return props.project.deadline.slice(0, 10) < new Date().toISOString().slice(0, 10)
})

const showStreak = computed(() =>
  props.streaksEnabled
  && props.project.streak_enabled
  && props.project.deadline !== null,
)

const progressAriaLabel = computed(() =>
  t('Прогресс проекта {name}: {progress}', {
    name: props.project.name,
    progress: props.project.name === 'Общий проект' ? '100%' : presentation.progressLabel,
  }),
)
</script>

<template>
  <article class="project-card" :class="`project-card--${project.status.replaceAll(' ', '-')}`">
    <RouterLink
      class="project-card__link"
      :to="{ name: 'project-detail', params: { projectId: project.id } }"
      :aria-label="`${t('Открыть проект')}: ${project.name}`"
    >
      <div class="project-card__header">
        <span class="project-card__status">{{ presentation.statusLabel }}</span>
        <span v-if="project.infinite" class="project-card__kind">∞ {{ t('Без лимита') }}</span>
      </div>

      <div class="project-card__body">
        <ProgressRing
          :value="presentation.progress"
          :infinite="project.infinite"
          :full="project.name === 'Общий проект'"
          :label="progressAriaLabel"
        />
        <div class="project-card__summary">
          <div class="project-card__title-row">
            <h2>{{ project.name }}</h2>
            <span class="project-card__open" aria-hidden="true">↗</span>
          </div>
          <div class="project-card__progress-copy">
            <span>
              <strong>{{ presentation.totalLabel }}</strong>
              <span> / {{ presentation.goalLabel }} {{ presentation.unitLabel }}</span>
            </span>
          </div>
        </div>
      </div>

      <StreakBadge
        v-if="showStreak"
        class="project-card__streak"
        :length="project.streak_length"
        :status="project.streak_status"
        scope="project"
        compact
      />

      <footer class="project-card__meta">
        <span :class="{ 'project-card__deadline--overdue': isOverdue }">
          <IonIcon :icon="calendarClearOutline" aria-hidden="true" />
          <span>{{ locale.formatDate(project.deadline) }}</span>
          <span v-if="isOverdue" class="visually-hidden"> — {{ t('срок прошёл') }}</span>
        </span>
        <span v-if="project.stages_enabled">
          <IonIcon :icon="layersOutline" aria-hidden="true" />
          {{ stageCountLabel }}
        </span>
      </footer>
    </RouterLink>
  </article>
</template>

<style scoped>
.project-card {
  position: relative;
  min-width: 0;
  overflow: hidden;
  border: 1px solid var(--nf-color-border);
  border-radius: var(--nf-radius-lg);
  background: var(--nf-color-surface);
  box-shadow: var(--nf-shadow-card);
  transition: border-color 160ms ease, transform 160ms ease, box-shadow 160ms ease;
}

.project-card::before {
  position: absolute;
  top: 0;
  bottom: 0;
  left: 0;
  width: 0.3rem;
  background: var(--nf-color-primary);
  content: '';
}

.project-card--в-архиве::before {
  background: var(--nf-color-text-muted);
}

.project-card--завершен::before {
  background: var(--nf-color-accent);
}

.project-card:hover {
  border-color: color-mix(in srgb, var(--nf-color-primary) 45%, var(--nf-color-border));
  transform: translateY(-2px);
  box-shadow: 0 18px 42px rgb(43 55 50 / 13%);
}

.project-card__link {
  display: flex;
  min-height: 15.5rem;
  padding: var(--nf-space-5);
  padding-left: calc(var(--nf-space-5) + 0.25rem);
  flex-direction: column;
  color: inherit;
  text-decoration: none;
}

.project-card__header,
.project-card__title-row,
.project-card__progress-copy,
.project-card__meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.project-card__streak {
  align-self: flex-start;
  margin-top: var(--nf-space-4);
}

.project-card__header {
  min-height: 1.75rem;
}

.project-card__status,
.project-card__kind {
  padding: 0.3rem 0.6rem;
  border-radius: var(--nf-radius-pill);
  background: var(--nf-color-primary-soft);
  color: var(--nf-color-primary);
  font-size: 0.75rem;
  font-weight: 750;
}

.project-card__kind {
  background: var(--nf-color-surface-muted);
  color: var(--nf-color-text-muted);
}

.project-card__title-row {
  gap: var(--nf-space-3);
  align-items: flex-start;
  margin: 0 0 var(--nf-space-3);
}

.project-card__body {
  display: flex;
  gap: var(--nf-space-4);
  align-items: center;
  margin-top: var(--nf-space-5);
}

.project-card__summary {
  min-width: 0;
  flex: 1;
}

.project-card h2 {
  display: -webkit-box;
  overflow: hidden;
  margin: 0;
  color: var(--nf-color-text);
  font-family: var(--nf-font-serif);
  font-size: clamp(1.35rem, 2.5vw, 1.65rem);
  line-height: 1.15;
  overflow-wrap: anywhere;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}

.project-card__open {
  color: var(--nf-color-text-muted);
  font-size: 1.15rem;
}

.project-card__progress-copy {
  gap: var(--nf-space-3);
  margin-bottom: var(--nf-space-2);
  color: var(--nf-color-text-muted);
  font-size: 0.82rem;
}

.project-card__progress-copy strong {
  color: var(--nf-color-text);
  font-size: 0.95rem;
}

.project-card__meta {
  gap: var(--nf-space-3);
  margin-top: auto;
  padding-top: var(--nf-space-5);
  color: var(--nf-color-text-muted);
  font-size: 0.78rem;
}

.project-card__meta > span {
  display: flex;
  gap: var(--nf-space-1);
  align-items: center;
}

.project-card__deadline--overdue {
  color: var(--nf-color-danger);
  font-weight: 700;
}

@media (max-width: 31rem) {
  .project-card__link {
    min-height: 13.75rem;
    padding: var(--nf-space-4);
    padding-left: calc(var(--nf-space-4) + 0.25rem);
  }

  .project-card__body {
    align-items: flex-start;
  }
}
</style>
