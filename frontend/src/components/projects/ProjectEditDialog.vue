<script setup lang="ts">
import { nextTick, reactive, ref, watch } from 'vue'
import { IonContent, IonHeader, IonIcon, IonModal, IonSpinner } from '@ionic/vue'
import { closeOutline } from 'ionicons/icons'

import { useLocaleStore } from '@/stores/locale'
import type { Project, ProjectUpdate, UnitCode } from '@/types/api'

const props = withDefaults(
  defineProps<{
    open: boolean
    project: Project
    submitting?: boolean
    apiError?: string | null
  }>(),
  { submitting: false, apiError: null },
)

const emit = defineEmits<{
  close: []
  submit: [payload: ProjectUpdate]
}>()

const locale = useLocaleStore()
const t = locale.translate
const validationErrors = ref<string[]>([])
const errorSummary = ref<HTMLElement | null>(null)
const form = reactive({
  name: '',
  unit: 'symbols' as UnitCode,
  goal: '',
  deadline: '',
  personalGoal: '',
  infinite: false,
  streakEnabled: false,
  autoFreeze: true,
  combineStageMindmaps: false,
})

function fill(): void {
  const project = props.project
  form.name = project.name
  form.unit = project.unit
  form.goal = project.goal === null ? '' : String(project.goal)
  form.deadline = project.deadline?.slice(0, 10) ?? ''
  form.personalGoal = String(project.personal_goal)
  form.infinite = project.infinite
  form.streakEnabled = project.streak_enabled
  form.autoFreeze = project.auto_freeze
  form.combineStageMindmaps = project.combine_stage_mindmaps
  validationErrors.value = []
}

function numberFrom(value: string): number {
  return Number(value.replace(',', '.'))
}

async function submit(): Promise<void> {
  const errors: string[] = []
  const name = form.name.trim()
  const goal = numberFrom(form.goal)
  const personalGoal = numberFrom(form.personalGoal)
  if (!name) errors.push(t('Введите название проекта.'))
  if (!props.project.stages.length && !form.infinite && (!Number.isFinite(goal) || goal <= 0)) {
    errors.push(t('Цель должна быть больше нуля.'))
  }
  if (!Number.isFinite(personalGoal) || personalGoal < 0) {
    errors.push(t('Цель на день не может быть отрицательной.'))
  }
  validationErrors.value = errors
  if (errors.length) {
    await nextTick()
    errorSummary.value?.focus()
    return
  }

  const payload: ProjectUpdate = {
    name,
    unit: form.unit,
    deadline: form.deadline || null,
    personal_goal: personalGoal,
    streak_enabled: form.streakEnabled,
    auto_freeze: form.autoFreeze,
    combine_stage_mindmaps: props.project.stages.length
      ? form.combineStageMindmaps
      : false,
    recalculate_plan: true,
  }
  if (!props.project.stages.length) {
    payload.infinite = form.infinite
    if (!form.infinite) payload.goal = goal
  }
  emit('submit', payload)
}

function requestClose(): void {
  if (!props.submitting) emit('close')
}

watch(
  () => props.open,
  (open) => {
    if (open) fill()
  },
  { immediate: true },
)
</script>

<template>
  <IonModal
    :is-open="open"
    css-class="workspace-dialog-modal"
    :backdrop-dismiss="!submitting"
    :keyboard-close="!submitting"
    @did-dismiss="requestClose"
  >
    <IonHeader class="workspace-dialog-header ion-no-border">
      <div>
        <p>{{ t('Параметры проекта') }}</p>
        <h2>{{ t('Редактировать проект') }}</h2>
      </div>
      <button
        class="workspace-dialog-close"
        type="button"
        :aria-label="t('Закрыть')"
        :disabled="submitting"
        @click="requestClose"
      >
        <IonIcon :icon="closeOutline" aria-hidden="true" />
      </button>
    </IonHeader>

    <IonContent class="workspace-dialog-content">
      <form class="workspace-form" novalidate @submit.prevent="submit">
        <div
          v-if="validationErrors.length"
          ref="errorSummary"
          class="workspace-form-error"
          role="alert"
          tabindex="-1"
        >
          <strong>{{ t('Проверьте форму') }}</strong>
          <ul><li v-for="error in validationErrors" :key="error">{{ error }}</li></ul>
        </div>
        <div v-if="apiError" class="workspace-form-error" role="alert">
          <strong>{{ t('Не удалось сохранить проект') }}</strong>
          <p>{{ apiError }}</p>
        </div>

        <label class="workspace-field workspace-field--wide" for="edit-project-name">
          <span>{{ t('Название') }}</span>
          <input id="edit-project-name" v-model="form.name" maxlength="300" autocomplete="off" />
        </label>
        <label class="workspace-field" for="edit-project-unit">
          <span>{{ t('Единица прогресса') }}</span>
          <select id="edit-project-unit" v-model="form.unit">
            <option value="symbols">{{ t('Символы') }}</option>
            <option value="A4">{{ t('Листы A4') }}</option>
            <option value="author_list">{{ t('Авторские листы') }}</option>
            <option value="ficbook_pages">{{ t('Страницы Ficbook') }}</option>
          </select>
        </label>
        <label class="workspace-field" for="edit-project-deadline">
          <span>{{ t('Срок') }}</span>
          <input id="edit-project-deadline" v-model="form.deadline" type="date" />
        </label>
        <label v-if="!project.stages.length" class="workspace-field" for="edit-project-goal">
          <span>{{ t('Общая цель') }}</span>
          <input
            id="edit-project-goal"
            v-model="form.goal"
            type="number"
            min="0"
            step="any"
            inputmode="decimal"
            :disabled="form.infinite"
          />
        </label>
        <label class="workspace-field" for="edit-project-personal-goal">
          <span>{{ t('Цель на день') }}</span>
          <input
            id="edit-project-personal-goal"
            v-model="form.personalGoal"
            type="number"
            min="0"
            step="any"
            inputmode="decimal"
          />
        </label>

        <div class="workspace-options workspace-field--wide">
          <label v-if="!project.stages.length" class="workspace-check">
            <input v-model="form.infinite" type="checkbox" />
            <span><strong>{{ t('Проект без конечной цели') }}</strong></span>
          </label>
          <label class="workspace-check">
            <input v-model="form.streakEnabled" type="checkbox" />
            <span><strong>{{ t('Отслеживать серию') }}</strong></span>
          </label>
          <label v-if="form.streakEnabled" class="workspace-check">
            <input v-model="form.autoFreeze" type="checkbox" />
            <span><strong>{{ t('Использовать заморозку автоматически') }}</strong></span>
          </label>
          <label v-if="project.stages.length" class="workspace-check">
            <input v-model="form.combineStageMindmaps" type="checkbox" />
            <span>
              <strong>{{ t('Объединять карты этапов') }}</strong>
              <small>{{ t('Показывать карты этапов как единую карту проекта') }}</small>
            </span>
          </label>
        </div>

        <footer class="workspace-form-actions workspace-field--wide">
          <button class="nf-button nf-button--secondary" type="button" :disabled="submitting" @click="requestClose">
            {{ t('Отмена') }}
          </button>
          <button class="nf-button" type="submit" :disabled="submitting">
            <IonSpinner v-if="submitting" name="crescent" aria-hidden="true" />
            {{ submitting ? t('Сохраняем…') : t('Сохранить') }}
          </button>
        </footer>
      </form>
    </IonContent>
  </IonModal>
</template>

<style>
.workspace-dialog-modal {
  --width: min(44rem, calc(100vw - 2rem));
  --height: min(46rem, calc(100dvh - 2rem));
  --border-radius: var(--nf-radius-lg);
  --background: var(--nf-color-surface);
}

.workspace-dialog-modal::part(content) {
  border: 1px solid var(--nf-color-border);
  box-shadow: 0 28px 80px rgb(20 30 27 / 25%);
}

.workspace-dialog-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  padding: var(--nf-space-5);
  background: var(--nf-color-surface);
}

.workspace-dialog-header p {
  margin: 0 0 var(--nf-space-1);
  color: var(--nf-color-primary);
  font-size: 0.75rem;
  font-weight: 800;
  letter-spacing: 0.1em;
  text-transform: uppercase;
}

.workspace-dialog-header h2 {
  margin: 0;
  color: var(--nf-color-text);
  font-family: var(--nf-font-serif);
  font-size: clamp(1.55rem, 5vw, 2rem);
}

.workspace-dialog-close {
  display: grid;
  width: 2.75rem;
  height: 2.75rem;
  padding: 0;
  place-items: center;
  border: 0;
  border-radius: var(--nf-radius-pill);
  background: var(--nf-color-surface-muted);
  color: var(--nf-color-text);
  cursor: pointer;
}

.workspace-dialog-content {
  --background: var(--nf-color-surface);
  --padding-start: var(--nf-space-5);
  --padding-end: var(--nf-space-5);
  --padding-bottom: calc(var(--nf-space-5) + env(safe-area-inset-bottom));
}

.workspace-form {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: var(--nf-space-4);
  padding-bottom: var(--nf-space-5);
}

.workspace-field {
  display: grid;
  gap: var(--nf-space-2);
  min-width: 0;
  color: var(--nf-color-text);
  font-size: 0.9rem;
  font-weight: 700;
}

.workspace-field--wide,
.workspace-form-error {
  grid-column: 1 / -1;
}

.workspace-field input,
.workspace-field select {
  width: 100%;
  min-height: 3rem;
  padding: 0.65rem 0.8rem;
  border: 1px solid var(--nf-color-border);
  border-radius: var(--nf-radius-sm);
  background: var(--nf-color-surface-raised);
  color: var(--nf-color-text);
}

.workspace-field input:disabled {
  background: var(--nf-color-surface-muted);
  opacity: 0.65;
}

.workspace-form-error {
  padding: var(--nf-space-4);
  border-left: 0.3rem solid var(--nf-color-danger);
  border-radius: var(--nf-radius-sm);
  background: color-mix(in srgb, var(--nf-color-danger) 10%, var(--nf-color-surface));
  color: var(--nf-color-text);
}

.workspace-form-error p,
.workspace-form-error ul { margin: var(--nf-space-2) 0 0; }

.workspace-options { display: grid; gap: var(--nf-space-2); }

.workspace-check {
  display: grid;
  grid-template-columns: 1.4rem 1fr;
  gap: var(--nf-space-3);
  align-items: start;
  min-height: 3rem;
  padding: var(--nf-space-3);
  border: 1px solid var(--nf-color-border);
  border-radius: var(--nf-radius-sm);
  background: var(--nf-color-surface-raised);
  cursor: pointer;
}

.workspace-check input {
  width: 1.25rem;
  height: 1.25rem;
  margin: 0.15rem 0 0;
  accent-color: var(--nf-color-primary);
}

.workspace-check strong,
.workspace-check small { display: block; }
.workspace-check small { margin-top: var(--nf-space-1); color: var(--nf-color-text-muted); }

.workspace-form-actions {
  display: flex;
  gap: var(--nf-space-3);
  justify-content: flex-end;
}

@media (max-width: 37.5rem) {
  .workspace-dialog-modal { --width: 100%; --height: 100%; --border-radius: 0; }
  .workspace-form { grid-template-columns: 1fr; }
  .workspace-field--wide,
  .workspace-form-error { grid-column: auto; }
  .workspace-form-actions { position: sticky; bottom: 0; padding: var(--nf-space-3) 0; background: var(--nf-color-surface); }
  .workspace-form-actions .nf-button { flex: 1; }
}
</style>
