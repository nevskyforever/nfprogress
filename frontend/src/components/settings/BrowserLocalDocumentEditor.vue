<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, toRaw } from 'vue'
import NFDocumentEditor from '@/components/documents/editor/NFDocumentEditor.vue'
import NFEditorStatusControls from '@/components/documents/editor/NFEditorStatusControls.vue'
import type { BrowserCloudAccountSession } from '@/platform/web/cloudAccountSession'
import type { LocalDocument } from '@/platform/web/localDocuments'
import { BrowserPersistenceError } from '@/platform/web/persistence'
import { useLocaleStore } from '@/stores/locale'
import type { SupportedLanguage } from '@/types/api'
import type { TiptapDocument } from '@/types/documents'

const copy: Record<SupportedLanguage, { save: string; saved: string; pending: string; saving: string; failed: string; loading: string; close: string; discard: string; stay: string; error: string; openError: string; conflict: string; invalid: string }> = {
  ru: { save: 'Сохранить текст', saved: 'Сохранено', pending: 'Есть несохранённые изменения', saving: 'Сохранение', failed: 'Ошибка сохранения', loading: 'Открываем зашифрованный текст…', close: 'Вернуться к проекту', discard: 'Отменить изменения', stay: 'Сначала сохраните или отмените изменения.', error: 'Не удалось сохранить текст. Изменения остались в редакторе.', openError: 'Не удалось открыть зашифрованный текст. Данные не изменены.', conflict: 'Текст изменился в другом сеансе. Текущие изменения остались в редакторе.', invalid: 'Формат или размер текста не поддерживается. Изменения остались в редакторе.' },
  en: { save: 'Save text', saved: 'Saved', pending: 'Unsaved changes', saving: 'Saving', failed: 'Save failed', loading: 'Opening encrypted text…', close: 'Back to project', discard: 'Discard changes', stay: 'Save or discard changes first.', error: 'Could not save the text. Your changes remain in the editor.', openError: 'Could not open the encrypted text. Your data is unchanged.', conflict: 'The text changed in another session. Your changes remain in the editor.', invalid: 'This text format or size is unsupported. Your changes remain in the editor.' },
  es: { save: 'Guardar texto', saved: 'Guardado', pending: 'Cambios sin guardar', saving: 'Guardando', failed: 'Error al guardar', loading: 'Abriendo texto cifrado…', close: 'Volver al proyecto', discard: 'Descartar cambios', stay: 'Guarda o descarta los cambios primero.', error: 'No se pudo guardar el texto. Los cambios siguen en el editor.', openError: 'No se pudo abrir el texto cifrado. Los datos no han cambiado.', conflict: 'El texto cambió en otra sesión. Tus cambios siguen en el editor.', invalid: 'El formato o tamaño del texto no es compatible. Los cambios siguen en el editor.' },
  de: { save: 'Text speichern', saved: 'Gespeichert', pending: 'Ungespeicherte Änderungen', saving: 'Speichern', failed: 'Speichern fehlgeschlagen', loading: 'Verschlüsselten Text öffnen…', close: 'Zurück zum Projekt', discard: 'Änderungen verwerfen', stay: 'Bitte zuerst speichern oder Änderungen verwerfen.', error: 'Der Text konnte nicht gespeichert werden. Die Änderungen bleiben im Editor.', openError: 'Der verschlüsselte Text konnte nicht geöffnet werden. Die Daten bleiben unverändert.', conflict: 'Der Text wurde in einer anderen Sitzung geändert. Die Änderungen bleiben im Editor.', invalid: 'Textformat oder Größe wird nicht unterstützt. Die Änderungen bleiben im Editor.' },
  fr: { save: 'Enregistrer le texte', saved: 'Enregistré', pending: 'Modifications non enregistrées', saving: 'Enregistrement', failed: 'Échec de l’enregistrement', loading: 'Ouverture du texte chiffré…', close: 'Retour au projet', discard: 'Annuler les modifications', stay: 'Enregistrez ou annulez les modifications avant de continuer.', error: 'Impossible d’enregistrer le texte. Les modifications restent dans l’éditeur.', openError: 'Impossible d’ouvrir le texte chiffré. Les données restent inchangées.', conflict: 'Le texte a changé dans une autre session. Vos modifications restent dans l’éditeur.', invalid: 'Le format ou la taille du texte n’est pas pris en charge. Les modifications restent dans l’éditeur.' },
  pt_BR: { save: 'Salvar texto', saved: 'Salvo', pending: 'Alterações não salvas', saving: 'Salvando', failed: 'Falha ao salvar', loading: 'Abrindo texto criptografado…', close: 'Voltar ao projeto', discard: 'Descartar alterações', stay: 'Salve ou descarte as alterações primeiro.', error: 'Não foi possível salvar o texto. As alterações permanecem no editor.', openError: 'Não foi possível abrir o texto criptografado. Os dados não foram alterados.', conflict: 'O texto mudou em outra sessão. As alterações permanecem no editor.', invalid: 'O formato ou tamanho do texto não é compatível. As alterações permanecem no editor.' },
}

const props = defineProps<{ session: BrowserCloudAccountSession; projectId: string; stageId: string | null; label: string }>()
const emit = defineEmits<{ close: [] }>()
const locale = useLocaleStore()
const words = computed(() => copy[locale.language])
const document = ref<LocalDocument | null>(null)
const draft = ref<TiptapDocument | null>(null)
const status = ref<'saved' | 'pending' | 'saving' | 'error'>('saved')
const message = ref<string | null>(null)
const loading = ref(true)
const zoom = ref(100)
const typewriterMode = ref(false)
let changeNumber = 0
let active = true
let saving = false

function changed(content: TiptapDocument): void {
  draft.value = structuredClone(toRaw(content))
  changeNumber++
  if (!saving) status.value = document.value && JSON.stringify(content) === JSON.stringify(document.value.content) ? 'saved' : 'pending'
  message.value = null
}

function canLeave(): boolean {
  if (loading.value || status.value === 'saving' || status.value === 'pending' || status.value === 'error') {
    message.value = words.value.stay
    return false
  }
  return true
}

function close(): void { if (canLeave()) emit('close') }
function discard(): void {
  if (status.value === 'saving') return
  status.value = 'saved'
  message.value = null
  emit('close')
}

async function save(): Promise<void> {
  if (!document.value || !draft.value || saving || status.value === 'saved') return
  const revision = document.value.revision
  const sequence = changeNumber
  const content = structuredClone(toRaw(draft.value))
  saving = true
  status.value = 'saving'
  message.value = null
  try {
    const repository = props.session.localNoteRepository()
    const saved = await repository.documents.save(repository.scope, props.projectId, props.stageId, revision, content)
    if (!active) return
    document.value = saved
    status.value = changeNumber === sequence || JSON.stringify(draft.value) === JSON.stringify(saved.content) ? 'saved' : 'pending'
  } catch (reason) {
    if (!active) return
    status.value = 'error'
    message.value = reason instanceof BrowserPersistenceError && reason.code === 'stale_source' ? words.value.conflict
      : reason instanceof BrowserPersistenceError && ['invalid_local_source', 'source_limit'].includes(reason.code) ? words.value.invalid : words.value.error
  } finally { saving = false }
}

onMounted(async () => {
  try {
    const repository = props.session.localNoteRepository()
    const opened = await repository.documents.open(repository.scope, props.projectId, props.stageId)
    if (!active) return
    document.value = opened
    draft.value = structuredClone(opened.content)
  } catch { if (active) message.value = words.value.openError }
  finally { if (active) loading.value = false }
})
onBeforeUnmount(() => { active = false; draft.value = null; document.value = null })
defineExpose({ canLeave })
</script>

<template>
  <section class="local-document" data-testid="encrypted-document-editor" :aria-label="label">
    <header class="local-document__header">
      <h4>{{ label }}</h4>
      <div class="local-document__actions">
        <button class="nf-button nf-button--secondary" type="button" @click="close">{{ words.close }}</button>
        <button v-if="status !== 'saved'" class="nf-button nf-button--secondary" type="button" :disabled="status === 'saving'" @click="discard">{{ words.discard }}</button>
        <button class="nf-button" type="button" :disabled="loading || status === 'saving' || status === 'saved'" @click="save">{{ words.save }}</button>
      </div>
    </header>
    <p v-if="loading" role="status">{{ words.loading }}</p>
    <template v-else-if="document && draft">
      <p role="status" data-testid="encrypted-document-save-status">{{ words[status === 'error' ? 'failed' : status] }}</p>
      <p v-if="message" role="alert">{{ message }}</p>
      <NFDocumentEditor :key="document.id" :initial-content="document.content" :translate="locale.translate" :zoom="zoom" :typewriter-mode="typewriterMode" @update="changed" />
      <NFEditorStatusControls :zoom="zoom" :typewriter-mode="typewriterMode" :translate="locale.translate" @zoom="zoom = $event" @toggle-typewriter="typewriterMode = !typewriterMode" />
    </template>
    <p v-else-if="message" role="alert">{{ message }}</p>
  </section>
</template>

<style scoped>
.local-document { display: flex; flex-direction: column; min-height: 38rem; border: 1px solid var(--nf-color-border); }
.local-document__header { display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between; gap: 1rem; padding: .75rem; }
.local-document__header h4 { margin: 0; }
.local-document__actions { display: flex; flex-wrap: wrap; gap: .5rem; }
.local-document > [role="status"], .local-document > [role="alert"] { margin: .3rem .75rem; }
.local-document > [role="alert"] { color: var(--nf-color-danger); }
.local-document :deep(.nf-document-editor) { min-height: 30rem; }
</style>
