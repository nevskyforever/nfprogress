<script setup lang="ts">
import { computed } from 'vue'
import { IonIcon } from '@ionic/vue'
import {
  addOutline,
  arrowDownOutline,
  arrowUpOutline,
  checkmarkCircleOutline,
  createOutline,
  shareSocialOutline,
  trashOutline,
} from 'ionicons/icons'

import { useLocaleStore } from '@/stores/locale'
import type { Project } from '@/types/api'
import ProgressRing from '@/components/ui/ProgressRing.vue'

const props = withDefaults(defineProps<{
  project: Project
  busy: boolean
  sharing?: boolean
}>(), {
  sharing: false,
})

const emit = defineEmits<{
  add: []
  edit: [stage: Project]
  remove: [stage: Project]
  complete: [stage: Project]
  reorder: [stageIds: string[]]
  share: [stage: Project]
  open: [stage: Project]
}>()

const locale = useLocaleStore()
const t = locale.translate
const readOnly = computed(() => props.project.status === 'завершен')
const sharedProject = computed(() => props.project.name === 'Общий проект')
const fractionDigits = computed(() => (props.project.unit === 'symbols' ? 0 : 2))

function stageProgress(stage: Project): number {
  return Math.min(100, Math.max(0, stage.progress || 0))
}

function canComplete(stage: Project): boolean {
  return stage.status !== 'завершен'
    && !stage.infinite
    && stage.goal !== null
    && stage.total >= stage.goal
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
  if (target < 0 || target >= props.project.stages.length) return
  const ids = props.project.stages.map((stage) => stage.id)
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

    <ol v-if="project.stages.length" class="stage-list">
      <li v-for="(stage, index) in project.stages" :key="stage.id" class="stage-card">
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
            </div>
            <ProgressRing
              :value="stageProgress(stage)"
              :infinite="stage.infinite"
              :label="`${t('Прогресс этапа')} ${stage.name}: ${stage.infinite ? t('Без лимита') : `${locale.formatNumber(stageProgress(stage), 1)}%`}`"
            />
          </div>
        </button>

        <div class="stage-actions" :aria-label="`${t('Действия этапа')}: ${stage.name}`">
            <button
              class="stage-icon-button"
              type="button"
              :aria-label="t('Поднять этап «{name}»', { name: stage.name })"
              :disabled="busy || readOnly || index === 0"
              @click="move(index, -1)"
            >
              <IonIcon :icon="arrowUpOutline" aria-hidden="true" />
            </button>
            <button
              class="stage-icon-button"
              type="button"
              :aria-label="t('Опустить этап «{name}»', { name: stage.name })"
              :disabled="busy || readOnly || index === project.stages.length - 1"
              @click="move(index, 1)"
            >
              <IonIcon :icon="arrowDownOutline" aria-hidden="true" />
            </button>
            <button
              class="stage-action-button"
              type="button"
              :title="stage.infinite ? t('Для проекта без цели нельзя создать картинку прогресса') : undefined"
              :disabled="busy || sharing || sharedProject || stage.infinite"
              @click="emit('share', stage)"
            >
              <IonIcon :icon="shareSocialOutline" aria-hidden="true" />
              {{ t('Поделиться') }}
            </button>
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
    </ol>

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
.stage-actions { display: flex; flex-wrap: wrap; gap: var(--nf-space-2); margin-top: var(--nf-space-4); }
.stage-icon-button,
.stage-action-button { display: inline-flex; gap: var(--nf-space-1); align-items: center; justify-content: center; min-height: 2.75rem; padding: 0.55rem 0.75rem; border: 1px solid var(--nf-color-border); border-radius: var(--nf-radius-sm); background: var(--nf-color-surface-raised); color: var(--nf-color-text); font-size: 0.8rem; font-weight: 700; cursor: pointer; }
.stage-icon-button { width: 2.75rem; padding: 0; }
.stage-icon-button:disabled,
.stage-action-button:disabled { opacity: 0.45; cursor: not-allowed; }
.stage-action-button--danger { color: var(--nf-color-danger); }
.stages-empty { display: grid; justify-items: start; gap: var(--nf-space-3); padding: var(--nf-space-5); border: 1px dashed var(--nf-color-border); border-radius: var(--nf-radius-md); color: var(--nf-color-text-muted); }
.stages-empty p { margin: 0; }

@media (max-width: 37.5rem) {
  .section-heading { align-items: stretch; flex-direction: column; }
  .stage-index { width: 2rem; height: 2rem; }
  .stage-actions { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .stage-icon-button { width: 100%; }
}
</style>
