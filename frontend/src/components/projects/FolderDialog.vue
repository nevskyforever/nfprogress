<script setup lang="ts">
import { nextTick, ref, watch } from 'vue'
import { IonContent, IonHeader, IonIcon, IonModal } from '@ionic/vue'
import { closeOutline } from 'ionicons/icons'

import { useLocaleStore } from '@/stores/locale'

const props = withDefaults(defineProps<{
  open: boolean
  initialName?: string
  submitting?: boolean
}>(), {
  initialName: '',
  submitting: false,
})

const emit = defineEmits<{
  close: []
  submit: [name: string]
}>()

const locale = useLocaleStore()
const t = locale.translate
const name = ref('')
const error = ref('')
const input = ref<HTMLInputElement | null>(null)

function requestClose(): void {
  if (!props.submitting) emit('close')
}

function submit(): void {
  const value = name.value.trim()
  if (!value) {
    error.value = t('Введите название папки.')
    input.value?.focus()
    return
  }
  emit('submit', value)
}

watch(() => props.open, async (open) => {
  if (!open) return
  name.value = props.initialName
  error.value = ''
  await nextTick()
  input.value?.focus()
})
</script>

<template>
  <IonModal
    :is-open="open"
    css-class="folder-dialog-modal"
    :backdrop-dismiss="!submitting"
    :keyboard-close="!submitting"
    @did-dismiss="requestClose"
  >
    <IonHeader class="dialog-header ion-no-border">
      <div>
        <p>{{ t('Новая папка') }}</p>
        <h2>{{ initialName ? t('Переименовать') : t('Создать') }}</h2>
      </div>
      <button class="dialog-close" type="button" :aria-label="t('Закрыть')" :disabled="submitting" @click="requestClose">
        <IonIcon :icon="closeOutline" aria-hidden="true" />
      </button>
    </IonHeader>

    <IonContent class="dialog-content">
      <form class="folder-dialog-form" @submit.prevent="submit">
        <p v-if="error" class="form-error-summary" role="alert">{{ error }}</p>
        <label class="form-field" for="folder-name">
          <span>{{ t('Название') }}</span>
          <input id="folder-name" ref="input" v-model="name" maxlength="120" autocomplete="off" :disabled="submitting" />
        </label>
        <footer class="form-actions">
          <button class="nf-button nf-button--secondary" type="button" :disabled="submitting" @click="requestClose">{{ t('Отмена') }}</button>
          <button class="nf-button" type="submit" :disabled="submitting">{{ initialName ? t('Сохранить') : t('Создать') }}</button>
        </footer>
      </form>
    </IonContent>
  </IonModal>
</template>

<style>
.folder-dialog-modal {
  --width: min(30rem, calc(100vw - 2rem));
  --height: auto;
  --border-radius: var(--nf-radius-lg);
  --background: var(--nf-color-surface);
}

.folder-dialog-modal::part(content) {
  border: 1px solid var(--nf-color-border);
  box-shadow: 0 28px 80px rgb(20 30 27 / 25%);
}

.folder-dialog-form {
  display: grid;
  gap: var(--nf-space-4);
  padding-bottom: var(--nf-space-5);
}

.folder-dialog-form .form-actions {
  display: flex;
  justify-content: flex-end;
  gap: var(--nf-space-3);
}
</style>
