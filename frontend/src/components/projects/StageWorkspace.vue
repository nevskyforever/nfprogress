<script setup lang="ts">
import { computed, ref } from 'vue'
import { IonIcon } from '@ionic/vue'
import {
  addOutline,
  arrowDownOutline,
  arrowUpOutline,
  checkmarkCircleOutline,
  createOutline,
  trashOutline,
} from 'ionicons/icons'

import { useLocaleStore } from '@/stores/locale'
import type { Project } from '@/types/api'
import ProgressRing from '@/components/ui/ProgressRing.vue'
import StreakBadge from './StreakBadge.vue'
import ProgressShareMenu from './ProgressShareMenu.vue'

type StageSort = 'progress' | 'updated' | 'deadline' | 'name'

const props = withDefaults(defineProps<{
  project: Project
  busy: boolean
  sharing?: boolean
  streaksEnabled?: boolean
}>(), {
  sharing: false,
  streaksEnabled: false,
})

const emit = defineEmits<{
  add: []
  edit: [stage: Project]
  remove: [stage: Project]
  complete: [stage: Project]
  reorder: [stageIds: string[]]
  copy: [stage: Project]
  save: [stage: Project]
  open: [stage: Project]
}>()

const locale = useLocaleStore()
const t = locale.translate
const readOnly = computed(() => props.project.status === 'завершен')
const sharedProject = computed(() => props.project.name === 'Общий проект')
const fractionDigits = computed(() => (props.project.unit === 'symbols' ? 0 : 2))
const sort = ref<StageSort>('progress')
const sortedStages = computed(() => [...props.project.stages].sort((left, right) => {
  if (sort.value === 'name') return left.name.localeCompare(right.name, locale.localeTag)
  if (sort.value === 'progress') return right.progress - left.progress
  if (sort.value === 'updated') return String(right.updated_at ?? '').localeCompare(String(left.updated_at ?? ''))
  return String(left.deadline ?? '9999-12-31').localeCompare(String(right.deadline ?? '9999-12-31'))
}))

function stageProgress(stage: Project): number {
  return Math.min(100, Math.max(0, stage.progress || 0))
}

function canComplete(stage: Project): boolean {
  return stage.status !== 'завершен'
    && !stage.infinite
    && stage.goal !== null
    && stage.total >= stage.goal
}

function showStageStreak(stage: Project): boolean {
  return props.streaksEnabled
    && props.project.deadline === null
    && stage.deadline !== null
    && stage.streak_enabled
}

function requestRemove(stage: Project): void {
  const confirmed = window.confirm(
    t('Удалить этап «{name}» и всю его историю прогресса? Это действие нельзя отменить.', {
      name: stage.name,
    }),
  )
  if (confirmed) emit('remove', stage)
}

function move(index: number, offset: -1 | 1): void {
  const target = index + offset
  if (sort.value !== 'progress' || target < 0 || target >= sortedStages.value.length) return
  const ids = sortedStages.value.map((stage) => stage.id)
  const currentId = ids[index]
  const targetId = ids[target]
  if (!currentId || !targetId) return
  ids[index] = targetId
  ids[target] = currentId
  emit('reorder', ids)
}
</script>

<template>
  <section class="stages-section" aria-labelledby="stages-heading">
    <div class="section-heading stage-section-heading">
      <div>
        <p>{{ t('Структура рукописи') }}</p>
        <h2 id="stages-heading">{{ t('Этапы') }}</h2>
      </div>
      <div class="stage-heading-actions">
        <label class="stage-sort" for="stage-sort">
          <span class="visually-hidden">{{ t('Сортировка') }}</span>
          <select id="stage-sort" v-model="sort" :disabled="busy">
            <option value="progress">{{ t('По прогрессу') }}</option>
            <option value="updated">{{ t('Недавно изменённые') }}</option>
            <option value="deadline">{{ t('По сроку') }}</option>
            <option value="name">{{ t('По названию') }}</option>
          </select>
        </label>
        <button
          v-if="!readOnly"
          class="nf-button nf-button--secondary"
          type="button"
          :disabled="busy"
          @click="emit('add')"
        >
          <IonIcon :icon="addOutline" aria-hidden="true" />
          {{ t('Добавить этап') }}
        </button>
      </div>
    </div>

    <TransitionGroup v-if="project.stages.length" tag="ol" class="stage-list">
      <li v-for="(stage, index) in sortedStages" :key="stage.id" class="stage-card">
        <button
          class="stage-open-button"
          type="button"
          :aria-label="`${t('Этапы')}: ${stage.name}`"
          @click="emit('open', stage)"
        >
          <span class="stage-index" aria-hidden="true">{{ index + 1 }}</span>
          <div class="stage-title-row">
            <div>
              <h3>{{ stage.name }}</h3>
              <span v-if="stage.status === 'завершен'" class="stage-completed">
                {{ t('Завершён') }}
              </span>
              <p>
                {{ locale.formatNumber(stage.total, fractionDigits) }} /
                {{ stage.infinite || stage.goal === null ? t('Без лимита') : locale.formatNumber(stage.goal, fractionDigits) }}
              </p>
              <StreakBadge
                v-if="showStageStreak(stage)"
                class="stage-streak"
                :length="stage.streak_length"
                :status="stage.streak_status"
                scope="stage"
                compact
              />
            </div>
            <ProgressRing
              :value="sharedProject && stage.infinite ? 100 : stageProgress(stage)"
              :infinite="stage.infinite"
              :full="sharedProject && stage.infinite"
              :label="`${t('Прогресс этапа')} ${stage.name}: ${stage.infinite ? t('Без лимита') : `${locale.formatNumber(stageProgress(stage), 1)}%`}`"
            />
          </div>
        </button>

        <div class="stage-actions" :aria-label="`${t('Действия этапа')}: ${stage.name}`">
            <button
              class="stage-icon-button"
              type="button"
              :aria-label="t('Поднять этап «{name}»', { name: stage.name })"
              :disabled="busy || readOnly || sort !== 'progress' || index === 0"
              @click="move(index, -1)"
            >
              <IonIcon :icon="arrowUpOutline" aria-hidden="true" />
            </button>
            <button
              class="stage-icon-button"
              type="button"
              :aria-label="t('Опустить этап «{name}»', { name: stage.name })"
              :disabled="busy || readOnly || sort !== 'progress' || index === sortedStages.length - 1"
              @click="move(index, 1)"
            >
              <IonIcon :icon="arrowDownOutline" aria-hidden="true" />
            </button>
            <ProgressShareMenu
              :label="t('Поделиться прогрессом «{name}»', { name: stage.name })"
              :title="stage.infinite ? t('Для проекта без цели нельзя создать картинку прогресса') : undefined"
              :disabled="busy || sharing || sharedProject || stage.infinite"
              @copy="emit('copy', stage)"
              @save="emit('save', stage)"
            />
            <button
              class="stage-action-button"
              type="button"
              :disabled="busy || readOnly || sharedProject || stage.status === 'завершен'"
              @click="emit('edit', stage)"
            >
              <IonIcon :icon="createOutline" aria-hidden="true" />
              {{ t('Изменить') }}
            </button>
            <button
              class="stage-action-button"
              type="button"
              :title="!canComplete(stage) ? t('Чтобы завершить этап, сначала достигните его цели.') : undefined"
              :disabled="busy || readOnly || sharedProject || !canComplete(stage)"
              @click="emit('complete', stage)"
            >
              <IonIcon :icon="checkmarkCircleOutline" aria-hidden="true" />
              {{ t('Завершить') }}
            </button>
            <button
              class="stage-action-button stage-action-button--danger"
              type="button"
              :disabled="busy || readOnly || sharedProject"
              @click="requestRemove(stage)"
            >
              <IonIcon :icon="trashOutline" aria-hidden="true" />
              {{ t('Удалить') }}
            </button>
        </div>
      </li>
    </TransitionGroup>

    <div v-else class="stages-empty">
      <p>{{ t('Разбейте рукопись на главы или другие рабочие этапы.') }}</p>
      <button v-if="!readOnly" class="nf-button nf-button--secondary" type="button" :disabled="busy" @click="emit('add')">
        <IonIcon :icon="addOutline" aria-hidden="true" />
        {{ t('Создать первый этап') }}
      </button>
    </div>
  </section>
</template>

<style scoped>
.stages-section { margin-top: var(--nf-space-7); }
.stage-section-heading { align-items: center; }
.stage-heading-actions { display: flex; flex-wrap: wrap; gap: var(--nf-space-2); align-items: center; }
.stage-sort { display: inline-flex; min-height: 2.75rem; align-items: center; border: 1px solid var(--nf-color-border); border-radius: var(--nf-radius-sm); background: var(--nf-color-surface-raised); }
.stage-sort select { min-height: 2.65rem; padding: 0 2rem 0 0.75rem; border: 0; background: transparent; color: var(--nf-color-text); font: inherit; font-size: .82rem; font-weight: 700; }
.section-heading {
  display: flex;
  gap: var(--nf-space-4);
  align-items: flex-end;
  justify-content: space-between;
  margin-bottom: var(--nf-space-4);
}
.section-heading p { margin: 0 0 var(--nf-space-1); color: var(--nf-color-accent); font-size: 0.72rem; font-weight: 800; letter-spacing: 0.08em; text-transform: uppercase; }
.section-heading h2 { margin: 0; color: var(--nf-color-text); font-family: var(--nf-font-serif); font-size: clamp(1.7rem, 4vw, 2.3rem); }
.stage-list { display: grid; grid-template-columns: repeat(auto-fit, minmax(min(100%, 18rem), 1fr)); gap: var(--nf-space-3); margin: 0; padding: 0; list-style: none; }
.stage-card { display: grid; gap: var(--nf-space-3); padding: var(--nf-space-4); border: 1px solid var(--nf-color-border); border-radius: var(--nf-radius-md); background: var(--nf-color-surface); box-shadow: var(--nf-shadow-card); }
.stage-open-button { display: grid; grid-template-columns: auto minmax(0, 1fr); gap: var(--nf-space-3); padding: 0; border: 0; background: transparent; color: inherit; text-align: left; cursor: pointer; }
.stage-open-button:focus-visible { border-radius: var(--nf-radius-sm); outline: 3px solid var(--nf-color-primary-soft); outline-offset: 3px; }
.stage-open-button:hover .stage-title-row h3 { color: var(--nf-color-primary); }
.stage-index { display: grid; width: 2.5rem; height: 2.5rem; place-items: center; border-radius: var(--nf-radius-pill); background: var(--nf-color-primary-soft); color: var(--nf-color-primary); font-family: var(--nf-font-serif); font-weight: 800; }
.stage-title-row { display: flex; gap: var(--nf-space-3); align-items: baseline; justify-content: space-between; }
.stage-title-row > div { min-width: 0; }
.stage-title-row h3 { overflow-wrap: anywhere; margin: 0; color: var(--nf-color-text); font-size: 1rem; }
.stage-title-row p { margin: var(--nf-space-2) 0 0; color: var(--nf-color-text-muted); font-size: 0.78rem; }
.stage-completed { display: inline-block; margin-top: var(--nf-space-1); color: var(--nf-color-success); font-size: 0.75rem; font-weight: 700; }
.stage-streak { margin-top: var(--nf-space-3); }
.stage-actions { display: flex; flex-wrap: wrap; gap: var(--nf-space-2); margin-top: var(--nf-space-4); }
.stage-icon-button,
.stage-action-button { display: inline-flex; gap: var(--nf-space-1); align-items: center; justify-content: center; min-height: 2.75rem; padding: 0.55rem 0.75rem; border: 1px solid var(--nf-color-border); border-radius: var(--nf-radius-sm); background: var(--nf-color-surface-raised); color: var(--nf-color-text); font-size: 0.8rem; font-weight: 700; cursor: pointer; }
.stage-icon-button { width: 2.75rem; padding: 0; }
.stage-icon-button:disabled,
.stage-action-button:disabled { opacity: 0.45; cursor: not-allowed; }
.stage-action-button--danger { color: var(--nf-color-danger); }
.stages-empty { display: grid; justify-items: start; gap: var(--nf-space-3); padding: var(--nf-space-5); border: 1px dashed var(--nf-color-border); border-radius: var(--nf-radius-md); color: var(--nf-color-text-muted); }
.stages-empty p { margin: 0; }
.stage-list-move, .stage-list-enter-active, .stage-list-leave-active { transition: transform 360ms ease, opacity 220ms ease; }
.stage-list-enter-from, .stage-list-leave-to { opacity: 0; transform: translateY(.75rem) scale(.98); }
.stage-list-leave-active { position: absolute; }

@media (max-width: 37.5rem) {
  .section-heading { align-items: stretch; flex-direction: column; }
  .stage-index { width: 2rem; height: 2rem; }
  .stage-actions { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .stage-icon-button { width: 100%; }
}
</style>
