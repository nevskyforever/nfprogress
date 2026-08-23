<script setup lang="ts">
import { nextTick, reactive, ref, watch } from 'vue'
import { IonContent, IonHeader, IonIcon, IonModal, IonSpinner } from '@ionic/vue'
import { addOutline, closeOutline, trashOutline } from 'ionicons/icons'

import { useLocaleStore } from '@/stores/locale'
import { NOTE_COLORS } from './noteColors'
import type { NoteChecklistItem, ProjectNote, ProjectNotePatch } from '@/types/notes'

const props = withDefaults(
  defineProps<{
    open: boolean
    note: ProjectNote | null
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
  submit: [noteId: string, patch: ProjectNotePatch]
}>()

const locale = useLocaleStore()
const t = locale.translate
const contentEditor = ref<HTMLElement | null>(null)
const form = reactive({
  title: '',
  content: '',
  tags: '',
  color: 'default',
  checklist: [] as NoteChecklistItem[],
})

function reset(): void {
  const note = props.note
  form.title = note?.title ?? ''
  form.content = note?.content ?? ''
  form.tags = note?.tags.join(', ') ?? ''
  form.color = note?.color ?? 'default'
  form.checklist = note?.checklist.map((item) => ({ ...item })) ?? []
  void nextTick(() => {
    const editor = contentEditor.value
    if (!editor) return
    if (note?.source_type === 'mindmap') editor.textContent = form.content
    else editor.innerHTML = form.content
    editor.focus()
  })
}

function contentChanged(event: Event): void {
  const target = event.currentTarget as HTMLElement
  form.content = props.note?.source_type === 'mindmap' ? target.innerText : target.innerHTML
}

function addChecklistItem(): void {
  form.checklist.push({ id: crypto.randomUUID(), text: '', checked: false })
}

function removeChecklistItem(index: number): void {
  form.checklist.splice(index, 1)
}

function normalizedTags(): string[] {
  return form.tags
    .split(/[,\n]/)
    .map((tag) => tag.trim().replace(/^#/, '').trim())
    .filter(Boolean)
}

function submit(): void {
  if (!props.note || props.submitting) return
  const patch: ProjectNotePatch = {
    title: form.title,
    content: form.content,
    tags: normalizedTags(),
    color: form.color,
  }
  if (props.note.source_type === 'project') {
    patch.checklist = form.checklist.filter((item) => item.text.trim())
  }
  emit('submit', props.note.id, patch)
}

function requestClose(): void {
  if (!props.submitting) emit('close')
}

watch([() => props.open, () => props.note?.id], ([open]) => {
  if (open) reset()
})
</script>

<template>
  <IonModal
    :is-open="open"
    css-class="note-editor-modal"
    :backdrop-dismiss="!submitting"
    :keyboard-close="!submitting"
    @did-dismiss="requestClose"
  >
    <IonHeader class="note-dialog__header ion-no-border">
      <div>
        <p>{{ note?.source_type === 'mindmap' ? t('Заметка карты') : t('Карточка проекта') }}</p>
        <h2 id="note-editor-title">{{ t('Редактирование заметки') }}</h2>
      </div>
      <button
        class="note-dialog__close"
        type="button"
        :aria-label="t('Закрыть')"
        :disabled="submitting"
        @click="requestClose"
      >
        <IonIcon :icon="closeOutline" aria-hidden="true" />
      </button>
    </IonHeader>

    <IonContent class="note-dialog__content">
      <form class="note-form" @submit.prevent="submit">
        <div v-if="apiError" class="note-form__error" role="alert">{{ apiError }}</div>

        <label class="note-field" for="note-title">
          <span>{{ t('Название') }}</span>
          <input
            id="note-title"
            v-model="form.title"
            name="title"
            maxlength="500"
            autocomplete="off"
          />
        </label>

        <div class="note-field">
          <span id="note-content-label">{{ t('Текст заметки') }}</span>
          <div
            ref="contentEditor"
            class="note-content-editor"
            :contenteditable="!submitting"
            role="textbox"
            aria-multiline="true"
            aria-labelledby="note-content-label"
            @input="contentChanged"
          />
          <small v-if="note?.source_type === 'mindmap'">
            {{ t('Текст синхронизируется с плавающей заметкой на карте.') }}
          </small>
        </div>

        <label class="note-field" for="note-tags">
          <span>{{ t('Теги') }}</span>
          <input
            id="note-tags"
            v-model="form.tags"
            name="tags"
            autocomplete="off"
            :placeholder="t('Например: персонажи, глава 2')"
          />
          <small>{{ t('Разделяйте теги запятыми.') }}</small>
        </label>

        <label class="note-field" for="note-color">
          <span>{{ t('Цвет карточки') }}</span>
          <select id="note-color" v-model="form.color" name="color">
            <option v-for="color in NOTE_COLORS" :key="color.value" :value="color.value">
              {{ t(color.label) }}
            </option>
          </select>
        </label>

        <fieldset v-if="note?.source_type === 'project'" class="checklist-editor">
          <legend>{{ t('Чек-лист') }}</legend>
          <div v-for="(item, index) in form.checklist" :key="item.id" class="checklist-row">
            <input
              v-model="item.checked"
              type="checkbox"
              :aria-label="t('Отметить пункт выполненным')"
            />
            <input
              v-model="item.text"
              type="text"
              maxlength="2000"
              :aria-label="t('Текст пункта')"
            />
            <button
              class="note-dialog__icon-button"
              type="button"
              :aria-label="t('Удалить пункт')"
              @click="removeChecklistItem(index)"
            >
              <IonIcon :icon="trashOutline" aria-hidden="true" />
            </button>
          </div>
          <button class="nf-button nf-button--quiet" type="button" @click="addChecklistItem">
            <IonIcon :icon="addOutline" aria-hidden="true" />
            {{ t('Добавить пункт') }}
          </button>
        </fieldset>

        <div class="note-form__actions">
          <button class="nf-button nf-button--secondary" type="button" @click="requestClose">
            {{ t('Отмена') }}
          </button>
          <button class="nf-button" type="submit" :disabled="submitting || !note">
            <IonSpinner v-if="submitting" name="crescent" aria-hidden="true" />
            {{ submitting ? t('Сохраняем…') : t('Сохранить') }}
          </button>
        </div>
      </form>
    </IonContent>
  </IonModal>
</template>

<style scoped>
.note-dialog__header {
  display: flex;
  gap: var(--nf-space-4);
  align-items: flex-start;
  justify-content: space-between;
  padding: var(--nf-space-5) var(--nf-space-5) var(--nf-space-3);
  background: var(--nf-color-surface);
  color: var(--nf-color-text);
}

.note-dialog__header p,
.note-dialog__header h2 {
  margin: 0;
}

.note-dialog__header p {
  color: var(--nf-color-primary);
  font-size: 0.75rem;
  font-weight: 800;
  text-transform: uppercase;
}

.note-dialog__header h2 {
  margin-top: var(--nf-space-1);
  font-family: var(--nf-font-serif);
  font-size: 1.8rem;
}

.note-dialog__close,
.note-dialog__icon-button {
  display: inline-grid;
  width: 2.75rem;
  min-width: 2.75rem;
  height: 2.75rem;
  padding: 0;
  place-items: center;
  border: 0;
  border-radius: var(--nf-radius-sm);
  background: transparent;
  color: var(--nf-color-text-muted);
  cursor: pointer;
}

.note-dialog__content {
  --background: var(--nf-color-surface);
}

.note-form {
  display: grid;
  gap: var(--nf-space-5);
  padding: var(--nf-space-4) var(--nf-space-5)
    calc(var(--nf-space-6) + env(safe-area-inset-bottom));
}

.note-field {
  display: grid;
  gap: var(--nf-space-2);
  color: var(--nf-color-text);
  font-weight: 700;
}

.note-field input,
.note-field select,
.note-content-editor,
.checklist-row input[type='text'] {
  width: 100%;
  min-height: 2.75rem;
  padding: 0.7rem 0.8rem;
  border: 1px solid var(--nf-color-border);
  border-radius: var(--nf-radius-sm);
  background: var(--nf-color-surface-raised);
  color: var(--nf-color-text);
  font-weight: 400;
}

.note-content-editor {
  min-height: 12rem;
  line-height: 1.55;
  overflow-wrap: anywhere;
}

.note-field small {
  color: var(--nf-color-text-muted);
  font-size: 0.78rem;
  font-weight: 400;
}

.checklist-editor {
  display: grid;
  gap: var(--nf-space-3);
  margin: 0;
  padding: var(--nf-space-4);
  border: 1px solid var(--nf-color-border);
  border-radius: var(--nf-radius-md);
}

.checklist-editor legend {
  padding: 0 var(--nf-space-2);
  font-weight: 700;
}

.checklist-row {
  display: grid;
  grid-template-columns: 1.5rem minmax(0, 1fr) 2.75rem;
  gap: var(--nf-space-2);
  align-items: center;
}

.checklist-row input[type='checkbox'] {
  width: 1.25rem;
  height: 1.25rem;
}

.note-form__error {
  padding: var(--nf-space-3);
  border-radius: var(--nf-radius-sm);
  background: color-mix(in srgb, var(--nf-color-danger) 12%, transparent);
  color: var(--nf-color-danger);
}

.note-form__actions {
  display: flex;
  gap: var(--nf-space-3);
  justify-content: flex-end;
  padding-top: var(--nf-space-3);
}

@media (min-width: 48rem) {
  :global(.note-editor-modal) {
    --width: min(48rem, calc(100vw - 3rem));
    --height: min(50rem, calc(100dvh - 3rem));
    --border-radius: var(--nf-radius-lg);
  }
}
</style>
