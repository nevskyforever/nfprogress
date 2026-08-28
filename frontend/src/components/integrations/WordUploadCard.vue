<script setup lang="ts">
import { computed, ref } from 'vue'
import { IonIcon, IonSpinner } from '@ionic/vue'
import { cloudUploadOutline, documentTextOutline } from 'ionicons/icons'

import { apiErrorMessage } from '@/api/client'
import { integrationsApi } from '@/api/integrations'
import { useLocaleStore } from '@/stores/locale'
import type { Project } from '@/types/api'
import type { WordImportResult } from '@/types/integrations'

const props = withDefaults(
  defineProps<{
    projects?: Project[]
  }>(),
  { projects: () => [] },
)

const emit = defineEmits<{
  imported: [result: WordImportResult, stageId: string | null]
}>()

const locale = useLocaleStore()
const t = locale.translate
const fileInput = ref<HTMLInputElement | null>(null)
const selectedProjectId = ref('')
const selectedStageId = ref('')
const fileName = ref('')
const symbols = ref<number | null>(null)
const error = ref<string | null>(null)
const message = ref('')
const loading = ref(false)
const pendingAction = ref<'count' | 'import'>('count')

const selectedProject = computed(
  () => props.projects.find(({ id }) => id === selectedProjectId.value) ?? null,
)
const needsStage = computed(() => (selectedProject.value?.stages.length ?? 0) > 0)
const importTargetReady = computed(
  () => Boolean(selectedProject.value) && (!needsStage.value || Boolean(selectedStageId.value)),
)

function openPicker(action: 'count' | 'import'): void {
  pendingAction.value = action
  fileInput.value?.click()
}

function selectProject(): void {
  selectedStageId.value = ''
  error.value = null
  message.value = ''
}

async function countSelected(event: Event): Promise<void> {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  input.value = ''
  if (!file) return

  fileName.value = file.name
  symbols.value = null
  error.value = null
  message.value = ''
  if (!file.name.toLocaleLowerCase().endsWith('.docx')) {
    error.value = t('Выберите документ Word в формате .docx.')
    return
  }
  if (file.size > 100 * 1024 * 1024) {
    error.value = t('Документ превышает допустимый размер 100 МБ.')
    return
  }

  loading.value = true
  try {
    if (pendingAction.value === 'import' && selectedProject.value) {
      const result = await integrationsApi.importWord(
        selectedProject.value.id,
        file,
        selectedStageId.value || null,
      )
      symbols.value = result.symbols
      emit('imported', result, selectedStageId.value || null)
      message.value = result.changed
        ? t('Прогресс проекта обновлён по документу.')
        : t('Объём проекта уже совпадает с документом.')
    } else {
      symbols.value = (await integrationsApi.countWord(file)).symbols
      message.value = t('Подсчёт завершён без изменения проекта.')
    }
  } catch (countError) {
    error.value = t(apiErrorMessage(countError))
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <section class="word-upload-card" aria-labelledby="word-upload-title">
    <div class="word-upload-card__icon" aria-hidden="true">
      <IonIcon :icon="documentTextOutline" />
    </div>
    <div>
      <h2 id="word-upload-title">{{ t('Импорт Word') }}</h2>
      <p>
        {{
          t(
            'Выберите .docx явно. Приложение подсчитает символы и при импорте запишет новый общий объём по обычным правилам прогресса. Сам документ не сохраняется.',
          )
        }}
      </p>
      <div v-if="projects.length" class="word-upload-card__target">
        <label for="word-import-project">
          <span>{{ t('Проект') }}</span>
          <select
            id="word-import-project"
            v-model="selectedProjectId"
            :disabled="loading"
            @change="selectProject"
          >
            <option value="">{{ t('Выберите проект') }}</option>
            <option v-for="project in projects" :key="project.id" :value="project.id">
              {{ project.name }}
            </option>
          </select>
        </label>
        <label v-if="needsStage" for="word-import-stage">
          <span>{{ t('Этап') }}</span>
          <select id="word-import-stage" v-model="selectedStageId" :disabled="loading">
            <option value="">{{ t('Выберите этап') }}</option>
            <option v-for="stage in selectedProject?.stages ?? []" :key="stage.id" :value="stage.id">
              {{ stage.name }}
            </option>
          </select>
        </label>
      </div>
      <p v-else class="word-upload-card__file">
        {{ t('Для записи прогресса сначала создайте активный проект. Подсчёт без записи доступен ниже.') }}
      </p>
      <input
        ref="fileInput"
        class="visually-hidden"
        type="file"
        accept=".docx,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        @change="countSelected"
      />
      <div class="word-upload-card__actions">
        <button
          class="nf-button"
          type="button"
          :disabled="loading || !importTargetReady"
          @click="openPicker('import')"
        >
          <IonSpinner v-if="loading && pendingAction === 'import'" name="crescent" aria-hidden="true" />
          <IonIcon v-else :icon="cloudUploadOutline" aria-hidden="true" />
          {{ t('Импортировать в проект') }}
        </button>
        <button
          class="nf-button nf-button--secondary"
          type="button"
          :disabled="loading"
          @click="openPicker('count')"
        >
          <IonSpinner v-if="loading && pendingAction === 'count'" name="crescent" aria-hidden="true" />
          {{ t('Только подсчитать') }}
        </button>
      </div>
      <p v-if="fileName" class="word-upload-card__file">{{ fileName }}</p>
      <p v-if="symbols !== null" class="word-upload-card__result" role="status">
        {{ t('Символов в документе: {count}', { count: locale.formatNumber(symbols, 0) }) }}
        <span v-if="message">{{ message }}</span>
      </p>
      <p v-if="error" class="word-upload-card__error" role="alert">{{ error }}</p>
    </div>
  </section>
</template>

<style scoped>
.word-upload-card {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr);
  gap: var(--nf-space-4);
  padding: var(--nf-space-5);
  border: 1px solid var(--nf-color-border);
  border-radius: var(--nf-radius-md);
  background: var(--nf-color-surface);
}

.word-upload-card__icon {
  display: grid;
  width: 3rem;
  height: 3rem;
  place-items: center;
  border-radius: var(--nf-radius-sm);
  background: var(--nf-color-primary-soft);
  color: var(--nf-color-primary);
  font-size: 1.45rem;
}

h2 {
  margin: 0;
  color: var(--nf-color-text);
  font-family: var(--nf-font-serif);
  font-size: 1.3rem;
}

p {
  max-width: 50rem;
  margin: var(--nf-space-2) 0 var(--nf-space-4);
  color: var(--nf-color-text-muted);
  line-height: 1.5;
}

.word-upload-card__file,
.word-upload-card__result,
.word-upload-card__error {
  margin-bottom: 0;
  overflow-wrap: anywhere;
}

.word-upload-card__target {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: var(--nf-space-3);
  margin: var(--nf-space-4) 0;
}

.word-upload-card__target label {
  display: grid;
  gap: var(--nf-space-2);
  color: var(--nf-color-text-muted);
  font-size: 0.82rem;
  font-weight: 700;
}

.word-upload-card__target select {
  width: 100%;
  min-height: 2.8rem;
  padding: 0 var(--nf-space-3);
  border: 1px solid var(--nf-color-border);
  border-radius: var(--nf-radius-sm);
  background: var(--nf-color-surface-raised);
  color: var(--nf-color-text);
}

.word-upload-card__actions {
  display: flex;
  gap: var(--nf-space-3);
  align-items: center;
  flex-wrap: wrap;
}

.word-upload-card__result span {
  display: block;
  margin-top: var(--nf-space-1);
}

.word-upload-card__result {
  color: var(--nf-color-success);
  font-weight: 750;
}

.word-upload-card__error {
  color: var(--nf-color-danger);
}

@media (max-width: 35rem) {
  .word-upload-card {
    grid-template-columns: 1fr;
  }

  .word-upload-card__target {
    grid-template-columns: 1fr;
  }
}
</style>
