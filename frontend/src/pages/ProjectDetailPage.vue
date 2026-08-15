<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { IonContent, IonIcon, IonPage } from '@ionic/vue'
import {
  alertCircleOutline,
  archiveOutline,
  arrowBackOutline,
  calendarClearOutline,
  checkmarkCircleOutline,
  createOutline,
  documentTextOutline,
  layersOutline,
  refreshOutline,
  trashOutline,
} from 'ionicons/icons'

import ProgressWorkspace from '@/components/projects/ProgressWorkspace.vue'
import ProjectEditDialog from '@/components/projects/ProjectEditDialog.vue'
import StageDialog from '@/components/projects/StageDialog.vue'
import StageWorkspace from '@/components/projects/StageWorkspace.vue'
import StatisticsWorkspace from '@/components/projects/StatisticsWorkspace.vue'
import StatePanel from '@/components/ui/StatePanel.vue'
import { useProjectPresentation } from '@/composables/useProjectPresentation'
import { useLocaleStore } from '@/stores/locale'
import { useProjectsStore } from '@/stores/projects'
import type {
  EntityUpdate,
  ProgressCreate,
  Project,
  ProjectUpdate,
  StageCreate,
} from '@/types/api'

const route = useRoute()
const router = useRouter()
const store = useProjectsStore()
const locale = useLocaleStore()
const t = locale.translate
const projectId = computed(() => String(route.params.projectId ?? ''))
const project = computed<Project>(() => store.currentProject as Project)
const presentation = useProjectPresentation(project)
const editDialogOpen = ref(false)
const stageDialogOpen = ref(false)
const editingStage = ref<Project | null>(null)
const selectedEntityId = ref('')
const actionSuccess = ref<string | null>(null)
const feedbackArea = ref<'global' | 'progress'>('global')

const canCompleteProject = computed(() => {
  if (!store.currentProject || project.value.status === 'завершен') return false
  return !project.value.infinite
    && project.value.goal !== null
    && project.value.total >= project.value.goal
})

function numberForProject(value: number): string {
  return locale.formatNumber(value, project.value.unit === 'symbols' ? 0 : 2)
}

function chooseAvailableEntity(): void {
  if (!store.currentProject) return
  if (!project.value.stages.length) {
    selectedEntityId.value = ''
    return
  }
  if (!project.value.stages.some((stage) => stage.id === selectedEntityId.value)) {
    selectedEntityId.value = project.value.stages.find((stage) => stage.status !== 'завершен')?.id
      ?? project.value.stages[0]?.id
      ?? ''
  }
}

async function loadProject(): Promise<void> {
  if (!projectId.value) return
  actionSuccess.value = null
  await store.loadOne(projectId.value)
  chooseAvailableEntity()
  refreshStatistics()
}

function refreshStatistics(): void {
  if (!store.currentProject) return
  void store.loadStatistics(project.value.id, selectedEntityId.value || undefined)
}

function openProjectEdit(): void {
  feedbackArea.value = 'global'
  store.clearDetailActionError()
  actionSuccess.value = null
  editDialogOpen.value = true
}

async function saveProject(payload: ProjectUpdate): Promise<void> {
  feedbackArea.value = 'global'
  const updated = await store.updateCurrent(project.value.id, payload)
  if (!updated) return
  editDialogOpen.value = false
  actionSuccess.value = t('Изменения проекта сохранены.')
  chooseAvailableEntity()
  refreshStatistics()
}

async function toggleArchive(): Promise<void> {
  feedbackArea.value = 'global'
  const archived = project.value.status !== 'в архиве'
  const updated = await store.setArchived(project.value.id, archived)
  if (!updated) return
  actionSuccess.value = archived ? t('Проект перемещён в архив.') : t('Проект снова активен.')
}

async function completeProject(): Promise<void> {
  feedbackArea.value = 'global'
  if (!window.confirm(t('Завершить проект «{name}»? После этого он будет доступен только для просмотра.', { name: project.value.name }))) return
  const updated = await store.completeCurrent(project.value.id)
  if (!updated) return
  actionSuccess.value = t('Проект завершён.')
  refreshStatistics()
}

async function deleteProject(): Promise<void> {
  feedbackArea.value = 'global'
  if (!window.confirm(t('Удалить проект «{name}» и все связанные данные? Это действие нельзя отменить.', { name: project.value.name }))) return
  if (await store.removeCurrent(project.value.id)) {
    await router.replace({ name: 'projects' })
  }
}

function openStageCreate(): void {
  feedbackArea.value = 'global'
  store.clearDetailActionError()
  actionSuccess.value = null
  editingStage.value = null
  stageDialogOpen.value = true
}

function openStageEdit(stage: Project): void {
  feedbackArea.value = 'global'
  store.clearDetailActionError()
  actionSuccess.value = null
  editingStage.value = stage
  stageDialogOpen.value = true
}

async function saveStage(payload: StageCreate | EntityUpdate): Promise<void> {
  feedbackArea.value = 'global'
  const updated = editingStage.value
    ? await store.updateStage(project.value.id, editingStage.value.id, payload as EntityUpdate)
    : await store.createStage(project.value.id, payload as StageCreate)
  if (!updated) return
  stageDialogOpen.value = false
  actionSuccess.value = editingStage.value ? t('Этап сохранён.') : t('Этап создан.')
  editingStage.value = null
  chooseAvailableEntity()
  refreshStatistics()
}

async function removeStage(stage: Project): Promise<void> {
  feedbackArea.value = 'global'
  const updated = await store.removeStage(project.value.id, stage.id)
  if (!updated) return
  actionSuccess.value = t('Этап удалён.')
  chooseAvailableEntity()
  refreshStatistics()
}

async function completeStage(stage: Project): Promise<void> {
  feedbackArea.value = 'global'
  const updated = await store.completeStage(project.value.id, stage.id)
  if (!updated) return
  actionSuccess.value = t('Этап завершён.')
  refreshStatistics()
}

async function reorderStages(stageIds: string[]): Promise<void> {
  feedbackArea.value = 'global'
  const updated = await store.reorderStages(project.value.id, stageIds)
  if (updated) actionSuccess.value = t('Порядок этапов сохранён.')
}

async function recordProgress(payload: ProgressCreate): Promise<void> {
  feedbackArea.value = 'progress'
  const result = await store.recordProgress(project.value.id, payload)
  if (!result) return
  const amount = locale.formatNumber(result.added_symbols, 0)
  actionSuccess.value = result.warning
    ? `${t('Прогресс записан')}: ${amount}. ${result.warning}`
    : `${t('Прогресс записан')}: ${amount}`
  refreshStatistics()
}

async function deleteProgress(entryId: string, stageId?: string): Promise<void> {
  feedbackArea.value = 'progress'
  const updated = await store.deleteProgress(project.value.id, entryId, stageId)
  if (!updated) return
  actionSuccess.value = t('Запись прогресса удалена, итог пересчитан.')
  refreshStatistics()
}

watch(projectId, () => { void loadProject() }, { immediate: true })
watch(selectedEntityId, () => {
  actionSuccess.value = null
  refreshStatistics()
})

onBeforeUnmount(() => store.cancelDetail())
</script>

<template>
  <IonPage>
    <IonContent :fullscreen="true" class="detail-content">
      <div class="detail-workspace">
        <RouterLink class="back-link" :to="{ name: 'projects' }">
          <IonIcon :icon="arrowBackOutline" aria-hidden="true" />
          {{ t('Все проекты') }}
        </RouterLink>

        <StatePanel
          v-if="store.detailLoading"
          :title="t('Открываем проект')"
          :message="t('Загружаем актуальные цели и этапы.')"
          loading
        />
        <StatePanel
          v-else-if="store.detailError"
          :title="t('Не удалось открыть проект')"
          :message="store.detailError"
          :icon="alertCircleOutline"
        >
          <button class="nf-button" type="button" @click="loadProject">{{ t('Повторить') }}</button>
        </StatePanel>

        <article v-else-if="store.currentProject" class="project-detail">
          <header class="detail-header">
            <div>
              <p class="detail-status">{{ presentation.statusLabel }}</p>
              <h1>{{ project.name }}</h1>
            </div>
            <div class="detail-progress-number">
              <strong v-if="!project.infinite">{{ presentation.progressLabel }}</strong>
              <strong v-else :aria-label="t('Проект без конечной цели')">∞</strong>
              <span>{{ t('общий прогресс') }}</span>
            </div>
          </header>

          <nav class="project-actions" :aria-label="t('Действия проекта')">
            <RouterLink
              class="nf-button nf-button--secondary"
              :to="{ name: 'project-notes', params: { projectId: project.id } }"
            >
              <IonIcon :icon="documentTextOutline" aria-hidden="true" />{{ t('Заметки и карта') }}
            </RouterLink>
            <button
              v-if="project.status !== 'завершен'"
              class="nf-button nf-button--secondary"
              type="button"
              :disabled="store.detailBusy"
              @click="openProjectEdit"
            >
              <IonIcon :icon="createOutline" aria-hidden="true" />{{ t('Изменить') }}
            </button>
            <button
              v-if="project.status !== 'завершен'"
              class="nf-button nf-button--secondary"
              type="button"
              :disabled="store.detailBusy"
              @click="toggleArchive"
            >
              <IonIcon :icon="project.status === 'в архиве' ? refreshOutline : archiveOutline" aria-hidden="true" />
              {{ project.status === 'в архиве' ? t('Вернуть в активные') : t('В архив') }}
            </button>
            <button
              v-if="project.status !== 'завершен'"
              class="nf-button"
              type="button"
              :title="!canCompleteProject ? t('Чтобы завершить проект, сначала достигните его цели.') : undefined"
              :disabled="store.detailBusy || !canCompleteProject"
              @click="completeProject"
            >
              <IonIcon :icon="checkmarkCircleOutline" aria-hidden="true" />{{ t('Завершить') }}
            </button>
            <button
              class="nf-button project-delete-button"
              type="button"
              :disabled="store.detailBusy"
              @click="deleteProject"
            >
              <IonIcon :icon="trashOutline" aria-hidden="true" />{{ t('Удалить проект') }}
            </button>
          </nav>

          <div v-if="feedbackArea === 'global'" class="action-announcements" aria-live="polite">
            <p v-if="store.detailActionError" class="action-error" role="alert">
              {{ store.detailActionError }}
            </p>
            <p v-else-if="actionSuccess" class="action-success">{{ actionSuccess }}</p>
          </div>

          <section class="progress-hero" :aria-label="t('Прогресс проекта')">
            <div><span>{{ t('Написано') }}</span><strong>{{ presentation.totalLabel }} {{ presentation.unitLabel }}</strong></div>
            <div><span>{{ t('Цель') }}</span><strong>{{ presentation.goalLabel }}</strong></div>
            <progress v-if="!project.infinite" :value="presentation.progress" max="100" :aria-label="`${t('Прогресс')}: ${presentation.progressLabel}`">
              {{ presentation.progressLabel }}
            </progress>
          </section>

          <section class="detail-facts" :aria-label="t('Сведения о проекте')">
            <div class="fact-card"><IonIcon :icon="calendarClearOutline" aria-hidden="true" /><span>{{ t('Срок') }}</span><strong>{{ locale.formatDate(project.deadline) }}</strong></div>
            <div class="fact-card"><IonIcon :icon="documentTextOutline" aria-hidden="true" /><span>{{ t('Записей прогресса') }}</span><strong>{{ locale.formatNumber(project.progress_entries.length, 0) }}</strong></div>
            <div class="fact-card"><IonIcon :icon="layersOutline" aria-hidden="true" /><span>{{ t('Цель на день') }}</span><strong>{{ numberForProject(project.personal_goal) }} {{ presentation.unitLabel }}</strong></div>
          </section>

          <StageWorkspace
            :project="project"
            :busy="store.detailBusy"
            @add="openStageCreate"
            @edit="openStageEdit"
            @remove="removeStage"
            @complete="completeStage"
            @reorder="reorderStages"
          />
          <ProgressWorkspace
            v-model="selectedEntityId"
            :project="project"
            :busy="store.detailBusy"
            :submitting="store.detailOperation === 'record-progress'"
            :error="feedbackArea === 'progress' ? store.detailActionError : null"
            :success="feedbackArea === 'progress' ? actionSuccess : null"
            @record="recordProgress"
            @remove="deleteProgress"
          />
          <StatisticsWorkspace
            :statistics="store.statistics"
            :loading="store.statisticsLoading"
            :error="store.statisticsError"
            @retry="refreshStatistics"
          />
        </article>
      </div>
    </IonContent>

    <ProjectEditDialog
      v-if="store.currentProject"
      :open="editDialogOpen"
      :project="project"
      :submitting="store.detailOperation === 'update-project'"
      :api-error="store.detailActionError"
      @close="editDialogOpen = false"
      @submit="saveProject"
    />
    <StageDialog
      v-if="store.currentProject"
      :open="stageDialogOpen"
      :project-unit="project.unit"
      :stage="editingStage"
      :submitting="Boolean(store.detailOperation?.includes('stage'))"
      :api-error="store.detailActionError"
      @close="stageDialogOpen = false"
      @submit="saveStage"
    />
  </IonPage>
</template>

<style scoped>
.detail-content { --background: var(--nf-color-canvas); }
.detail-workspace { width: min(100%, 76rem); min-height: 100%; margin: 0 auto; padding: calc(var(--nf-space-6) + env(safe-area-inset-top)) clamp(1rem, 4vw, 4rem) var(--nf-space-7); }
.back-link { display: inline-flex; gap: var(--nf-space-2); align-items: center; min-height: 2.75rem; margin-bottom: var(--nf-space-5); padding: 0 var(--nf-space-2); border-radius: var(--nf-radius-sm); color: var(--nf-color-primary); font-weight: 700; text-decoration: none; }
.detail-header { display: flex; gap: var(--nf-space-5); align-items: flex-start; justify-content: space-between; }
.detail-status { display: inline-flex; margin: 0 0 var(--nf-space-3); padding: 0.35rem 0.7rem; border-radius: var(--nf-radius-pill); background: var(--nf-color-primary-soft); color: var(--nf-color-primary); font-size: 0.75rem; font-weight: 800; }
.detail-header h1 { max-width: 50rem; margin: 0; overflow-wrap: anywhere; color: var(--nf-color-text); font-family: var(--nf-font-serif); font-size: clamp(2.2rem, 7vw, 4.5rem); letter-spacing: -0.045em; line-height: 1; }
.detail-progress-number { display: grid; min-width: 8rem; padding-top: var(--nf-space-4); text-align: right; }
.detail-progress-number strong { color: var(--nf-color-accent); font-family: var(--nf-font-serif); font-size: clamp(2rem, 5vw, 3.25rem); line-height: 1; }
.detail-progress-number span { margin-top: var(--nf-space-1); color: var(--nf-color-text-muted); font-size: 0.75rem; }
.project-actions { display: flex; flex-wrap: wrap; gap: var(--nf-space-2); margin-top: var(--nf-space-5); }
.project-delete-button { margin-left: auto; border-color: color-mix(in srgb, var(--nf-color-danger) 35%, transparent); background: transparent; color: var(--nf-color-danger); }
.project-delete-button:hover:not(:disabled) { background: color-mix(in srgb, var(--nf-color-danger) 10%, transparent); }
.action-announcements { min-height: 1.25rem; margin-top: var(--nf-space-3); }
.action-announcements p { margin: 0; padding: var(--nf-space-3); border-radius: var(--nf-radius-sm); font-size: 0.85rem; }
.action-error { background: color-mix(in srgb, var(--nf-color-danger) 10%, var(--nf-color-surface)); color: var(--nf-color-danger); }
.action-success { background: color-mix(in srgb, var(--nf-color-success) 10%, var(--nf-color-surface)); color: var(--nf-color-success); }
.progress-hero { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: var(--nf-space-5); margin-top: var(--nf-space-5); padding: var(--nf-space-5); border: 1px solid var(--nf-color-border); border-radius: var(--nf-radius-lg); background: var(--nf-color-surface); box-shadow: var(--nf-shadow-card); }
.progress-hero > div { display: grid; gap: var(--nf-space-1); }
.progress-hero span { color: var(--nf-color-text-muted); font-size: 0.78rem; font-weight: 700; text-transform: uppercase; }
.progress-hero strong { color: var(--nf-color-text); font-size: clamp(1.1rem, 2.5vw, 1.35rem); }
.progress-hero progress { grid-column: 1 / -1; width: 100%; height: 0.75rem; overflow: hidden; border: 0; border-radius: var(--nf-radius-pill); appearance: none; }
.progress-hero progress::-webkit-progress-bar { background: var(--nf-color-surface-muted); }
.progress-hero progress::-webkit-progress-value { background: var(--nf-color-primary); }
.progress-hero progress::-moz-progress-bar { background: var(--nf-color-primary); }
.detail-facts { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: var(--nf-space-3); margin-top: var(--nf-space-4); }
.fact-card { display: grid; grid-template-columns: auto 1fr; gap: var(--nf-space-1) var(--nf-space-3); padding: var(--nf-space-4); border: 1px solid var(--nf-color-border); border-radius: var(--nf-radius-md); background: var(--nf-color-surface); }
.fact-card ion-icon { grid-row: 1 / 3; align-self: center; color: var(--nf-color-accent); font-size: 1.35rem; }
.fact-card span { color: var(--nf-color-text-muted); font-size: 0.75rem; }
.fact-card strong { overflow: hidden; color: var(--nf-color-text); font-size: 0.92rem; text-overflow: ellipsis; white-space: nowrap; }

@media (max-width: 42rem) {
  .detail-header { display: grid; }
  .detail-progress-number { display: flex; gap: var(--nf-space-2); align-items: baseline; padding-top: 0; text-align: left; }
  .project-actions { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .project-delete-button { margin-left: 0; }
  .detail-facts { grid-template-columns: 1fr; }
}
@media (max-width: 25rem) {
  .project-actions { grid-template-columns: 1fr; }
}
</style>
