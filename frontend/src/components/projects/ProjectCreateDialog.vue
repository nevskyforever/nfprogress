<script setup lang="ts">
import { nextTick, reactive, ref, watch } from 'vue'
import { IonContent, IonHeader, IonIcon, IonModal, IonSpinner } from '@ionic/vue'
import { closeOutline } from 'ionicons/icons'

import { useLocaleStore } from '@/stores/locale'
import type { ProjectCreate, UnitCode } from '@/types/api'
import { automaticDailyGoal, automaticDeadline } from '@/utils/projectPlanning'

const props = withDefaults(
  defineProps<{
    open: boolean
    submitting?: boolean
    apiError?: string | null
  }>(),
  {
    submitting: false,
    apiError: null,
  },
)

const emit = defineEmits<{
  close: []
  submit: [payload: ProjectCreate]
}>()

const locale = useLocaleStore()
const t = locale.translate
const validationErrors = ref<string[]>([])
const errorSummary = ref<HTMLElement | null>(null)

const form = reactive({
  name: '',
  unit: 'symbols' as UnitCode,
  goal: '50000',
  total: '0',
  deadline: '',
  personalGoal: '0',
  infinite: false,
  stagesEnabled: false,
  streakEnabled: false,
  autoFreeze: true,
})

function reset(): void {
  form.name = ''
  form.unit = 'symbols'
  form.goal = '50000'
  form.total = '0'
  form.deadline = ''
  form.personalGoal = '0'
  form.infinite = false
  form.stagesEnabled = false
  form.streakEnabled = false
  form.autoFreeze = true
  validationErrors.value = []
}

function numberFrom(value: string | number): number {
  return Number(String(value).replace(',', '.'))
}

function updateDailyGoal(): void {
  if (form.infinite) return
  const dailyGoal = automaticDailyGoal(
    numberFrom(form.goal), numberFrom(form.total), form.deadline, form.unit,
  )
  if (dailyGoal !== null) form.personalGoal = String(dailyGoal)
}

function updateDeadline(): void {
  if (form.infinite) return
  const deadline = automaticDeadline(
    numberFrom(form.goal), numberFrom(form.total), numberFrom(form.personalGoal),
  )
  if (deadline !== null) form.deadline = deadline
}

function updatePlanFromAmount(): void {
  if (numberFrom(form.personalGoal) > 0) updateDeadline()
  else updateDailyGoal()
}

async function submit(): Promise<void> {
  const errors: string[] = []
  const name = form.name.trim()
  const goal = numberFrom(form.goal)
  const total = numberFrom(form.total)
  const personalGoal = numberFrom(form.personalGoal)

  if (!name) errors.push(t('Введите название проекта.'))
  if (!form.infinite && (!Number.isFinite(goal) || goal <= 0)) {
    errors.push(t('Цель должна быть больше нуля.'))
  }
  if (!Number.isFinite(total) || total < 0) {
    errors.push(t('Текущее значение не может быть отрицательным.'))
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

  const payload: ProjectCreate = {
    name,
    unit: form.unit,
    infinite: form.infinite,
    total,
    deadline: form.deadline || null,
    personal_goal: personalGoal,
    streak_enabled: form.streakEnabled,
    auto_freeze: form.autoFreeze,
    stages_enabled: form.stagesEnabled,
    stages: [],
    combine_stage_mindmaps: false,
  }
  if (!form.infinite) payload.goal = goal
  emit('submit', payload)
}

function requestClose(): void {
  if (!props.submitting) emit('close')
}

watch(
  () => props.open,
  (open) => {
    if (open) reset()
  },
)
</script>

<template>
  <IonModal
    :is-open="open"
    css-class="project-create-modal"
    :backdrop-dismiss="!submitting"
    :keyboard-close="!submitting"
    @did-dismiss="requestClose"
  >
    <IonHeader class="dialog-header ion-no-border">
      <div>
        <p>{{ t('Новый проект') }}</p>
        <h2 id="create-project-title">{{ t('Начните новую историю') }}</h2>
      </div>
      <button
        class="dialog-close"
        type="button"
        :aria-label="t('Закрыть')"
        :disabled="submitting"
        @click="requestClose"
      >
        <IonIcon :icon="closeOutline" aria-hidden="true" />
      </button>
    </IonHeader>

    <IonContent class="dialog-content">
      <form class="project-form" novalidate @submit.prevent="submit">
        <div
          v-if="validationErrors.length"
          ref="errorSummary"
          class="form-error-summary"
          role="alert"
          tabindex="-1"
        >
          <strong>{{ t('Проверьте форму') }}</strong>
          <ul>
            <li v-for="error in validationErrors" :key="error">{{ error }}</li>
          </ul>
        </div>

        <div v-if="apiError" class="form-error-summary" role="alert">
          <strong>{{ t('Не удалось создать проект') }}</strong>
          <p>{{ apiError }}</p>
        </div>

        <label class="form-field form-field--wide" for="project-name">
          <span>{{ t('Название') }}</span>
          <input
            id="project-name"
            v-model="form.name"
            name="name"
            autocomplete="off"
            maxlength="200"
            :placeholder="t('Например, «Дом у моря»')"
            autofocus
          />
        </label>

        <label class="form-field" for="project-unit">
          <span>{{ t('Единица прогресса') }}</span>
          <select id="project-unit" v-model="form.unit" name="unit">
            <option value="symbols">{{ t('Символы') }}</option>
            <option value="A4">{{ t('Листы A4') }}</option>
            <option value="author_list">{{ t('Авторские листы') }}</option>
            <option value="ficbook_pages">{{ t('Страницы Ficbook') }}</option>
          </select>
        </label>

        <label class="form-field" for="project-deadline">
          <span>{{ t('Срок') }} <small>{{ t('необязательно') }}</small></span>
          <input id="project-deadline" v-model="form.deadline" name="deadline" type="date" @input="updateDailyGoal" />
        </label>

        <label class="form-field" for="project-total">
          <span>{{ t('Уже написано') }}</span>
          <input
            id="project-total"
            v-model="form.total"
            name="total"
            type="number"
            inputmode="decimal"
            min="0"
            step="any"
            @input="updatePlanFromAmount"
          />
        </label>

        <label class="form-field" for="project-goal">
          <span>{{ t('Общая цель') }}</span>
          <input
            id="project-goal"
            v-model="form.goal"
            name="goal"
            type="number"
            inputmode="decimal"
            min="0"
            step="any"
            :disabled="form.infinite"
            @input="updatePlanFromAmount"
          />
        </label>

        <label class="form-field" for="project-personal-goal">
          <span>{{ t('Цель на день') }}</span>
          <input
            id="project-personal-goal"
            v-model="form.personalGoal"
            name="personal_goal"
            type="number"
            inputmode="decimal"
            min="0"
            step="any"
            @input="updateDeadline"
          />
        </label>

        <div class="form-options form-field--wide">
          <label class="check-field">
            <input v-model="form.infinite" name="infinite" type="checkbox" />
            <span>
              <strong>{{ t('Проект без конечной цели') }}</strong>
              <small>{{ t('Для дневников, сериалов и постоянной практики') }}</small>
            </span>
          </label>
          <label class="check-field">
            <input v-model="form.stagesEnabled" name="stages_enabled" type="checkbox" />
            <span>
              <strong>{{ t('Проект с этапами') }}</strong>
              <small>{{ t('Текущая цель и прогресс перейдут в первый этап') }}</small>
            </span>
          </label>
          <label class="check-field">
            <input v-model="form.streakEnabled" name="streak_enabled" type="checkbox" />
            <span>
              <strong>{{ t('Отслеживать серию') }}</strong>
              <small>{{ t('Поддерживать ежедневный ритм работы') }}</small>
            </span>
          </label>
          <label v-if="form.streakEnabled" class="check-field check-field--nested">
            <input v-model="form.autoFreeze" name="auto_freeze" type="checkbox" />
            <span>
              <strong>{{ t('Использовать заморозку автоматически') }}</strong>
              <small>{{ t('Если дневная цель не выполнена') }}</small>
            </span>
          </label>
        </div>

        <footer class="form-actions form-field--wide">
          <button
            class="nf-button nf-button--secondary"
            type="button"
            :disabled="submitting"
            @click="requestClose"
          >
            {{ t('Отмена') }}
          </button>
          <button class="nf-button" type="submit" :disabled="submitting">
            <IonSpinner v-if="submitting" name="crescent" aria-hidden="true" />
            <span>{{ submitting ? t('Создаём…') : t('Создать проект') }}</span>
          </button>
        </footer>
      </form>
    </IonContent>
  </IonModal>
</template>

<style>
.project-create-modal {
  --width: min(44rem, calc(100vw - 2rem));
  --height: min(47rem, calc(100dvh - 2rem));
  --border-radius: var(--nf-radius-lg);
  --background: var(--nf-color-surface);
}

.project-create-modal::part(content) {
  border: 1px solid var(--nf-color-border);
  box-shadow: 0 28px 80px rgb(20 30 27 / 25%);
}

.dialog-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  padding: var(--nf-space-5) var(--nf-space-5) var(--nf-space-4);
  background: var(--nf-color-surface);
}

.dialog-header p {
  margin: 0 0 var(--nf-space-1);
  color: var(--nf-color-primary);
  font-size: 0.75rem;
  font-weight: 800;
  letter-spacing: 0.1em;
  text-transform: uppercase;
}

.dialog-header h2 {
  margin: 0;
  color: var(--nf-color-text);
  font-family: var(--nf-font-serif);
  font-size: clamp(1.55rem, 5vw, 2rem);
}

.dialog-close {
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

.dialog-close ion-icon {
  font-size: 1.4rem;
}

.dialog-content {
  --background: var(--nf-color-surface);
  --padding-start: var(--nf-space-5);
  --padding-end: var(--nf-space-5);
  --padding-bottom: calc(var(--nf-space-5) + env(safe-area-inset-bottom));
}

.project-form {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: var(--nf-space-4);
  padding-bottom: var(--nf-space-5);
}

.form-field {
  display: grid;
  gap: var(--nf-space-2);
  min-width: 0;
  color: var(--nf-color-text);
  font-size: 0.9rem;
  font-weight: 700;
}

.form-field--wide,
.form-error-summary {
  grid-column: 1 / -1;
}

.form-field small {
  color: var(--nf-color-text-muted);
  font-size: 0.72rem;
  font-weight: 500;
}

.form-field input,
.form-field select {
  width: 100%;
  min-height: 3rem;
  padding: 0.65rem 0.8rem;
  border: 1px solid var(--nf-color-border);
  border-radius: var(--nf-radius-sm);
  background: var(--nf-color-surface-raised);
  color: var(--nf-color-text);
}

.form-field input:disabled {
  background: var(--nf-color-surface-muted);
  opacity: 0.65;
}

.form-field input:hover:not(:disabled),
.form-field select:hover {
  border-color: var(--nf-color-primary);
}

.form-error-summary {
  padding: var(--nf-space-4);
  border-left: 0.3rem solid var(--nf-color-danger);
  border-radius: var(--nf-radius-sm);
  background: color-mix(in srgb, var(--nf-color-danger) 10%, var(--nf-color-surface));
  color: var(--nf-color-text);
}

.form-error-summary p,
.form-error-summary ul {
  margin: var(--nf-space-2) 0 0;
}

.form-options {
  display: grid;
  gap: var(--nf-space-2);
  padding: var(--nf-space-2) 0;
}

.check-field {
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

.check-field input {
  width: 1.25rem;
  height: 1.25rem;
  margin: 0.15rem 0 0;
  accent-color: var(--nf-color-primary);
}

.check-field strong,
.check-field small {
  display: block;
}

.check-field strong {
  color: var(--nf-color-text);
  font-size: 0.9rem;
}

.check-field small {
  margin-top: var(--nf-space-1);
  color: var(--nf-color-text-muted);
  line-height: 1.35;
}

.check-field--nested {
  margin-left: var(--nf-space-5);
}

.form-actions {
  display: flex;
  gap: var(--nf-space-3);
  justify-content: flex-end;
  padding-top: var(--nf-space-2);
}

.form-actions .nf-button ion-spinner {
  width: 1rem;
  height: 1rem;
}

@media (max-width: 37.5rem) {
  .project-create-modal {
    --width: 100%;
    --height: 100%;
    --border-radius: 0;
  }

  .project-form {
    grid-template-columns: 1fr;
  }

  .form-field--wide,
  .form-error-summary {
    grid-column: auto;
  }

  .form-actions {
    position: sticky;
    bottom: 0;
    padding: var(--nf-space-3) 0;
    background: var(--nf-color-surface);
  }

  .form-actions .nf-button {
    flex: 1;
  }
}
</style>
