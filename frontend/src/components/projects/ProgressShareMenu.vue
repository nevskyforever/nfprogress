<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { IonIcon } from '@ionic/vue'
import { chevronDownOutline, copyOutline, downloadOutline, shareSocialOutline } from 'ionicons/icons'

import { useLocaleStore } from '@/stores/locale'

const props = withDefaults(defineProps<{
  label: string
  disabled?: boolean
  busy?: boolean
  buttonClass?: string
  title?: string
}>(), {
  disabled: false,
  busy: false,
  buttonClass: 'nf-button nf-button--secondary',
  title: undefined,
})

const emit = defineEmits<{
  copy: []
  save: []
}>()

const locale = useLocaleStore()
const t = locale.translate
const root = ref<HTMLElement | null>(null)
const open = ref(false)

function close(): void {
  open.value = false
}

function toggle(): void {
  if (!props.disabled && !props.busy) open.value = !open.value
}

function copy(): void {
  close()
  emit('copy')
}

function save(): void {
  close()
  emit('save')
}

function onDocumentPointerDown(event: PointerEvent): void {
  if (!root.value?.contains(event.target as Node)) close()
}

function onDocumentKeyDown(event: KeyboardEvent): void {
  if (event.key === 'Escape') close()
}

watch(() => props.disabled || props.busy, (unavailable) => {
  if (unavailable) close()
})

onMounted(() => {
  document.addEventListener('pointerdown', onDocumentPointerDown)
  document.addEventListener('keydown', onDocumentKeyDown)
})

onBeforeUnmount(() => {
  document.removeEventListener('pointerdown', onDocumentPointerDown)
  document.removeEventListener('keydown', onDocumentKeyDown)
})
</script>

<template>
  <div ref="root" class="progress-share-menu">
    <button
      :class="buttonClass"
      type="button"
      :aria-label="label"
      aria-haspopup="menu"
      :aria-expanded="open"
      :aria-busy="busy"
      :title="title"
      :disabled="disabled || busy"
      @click="toggle"
    >
      <IonIcon :icon="shareSocialOutline" aria-hidden="true" />
      <span>{{ t('Поделиться') }}</span>
      <IonIcon class="progress-share-menu__chevron" :icon="chevronDownOutline" aria-hidden="true" />
    </button>

    <div v-if="open" class="progress-share-menu__list" role="menu" :aria-label="label">
      <button
        class="progress-share-menu__item"
        type="button"
        role="menuitem"
        :aria-label="t('Скопировать картинку прогресса')"
        :title="t('Скопировать картинку прогресса')"
        @click="copy"
      >
        <IonIcon :icon="copyOutline" aria-hidden="true" />
        <span class="visually-hidden">{{ t('Скопировать картинку прогресса') }}</span>
      </button>
      <button
        class="progress-share-menu__item"
        type="button"
        role="menuitem"
        :aria-label="t('Сохранить картинку прогресса')"
        :title="t('Сохранить картинку прогресса')"
        @click="save"
      >
        <IonIcon :icon="downloadOutline" aria-hidden="true" />
        <span class="visually-hidden">{{ t('Сохранить картинку прогресса') }}</span>
      </button>
    </div>
  </div>
</template>

<style scoped>
.progress-share-menu { position: relative; display: inline-flex; }
.progress-share-menu__chevron { margin-left: -0.2rem; font-size: 1rem; }
.progress-share-menu__list { position: absolute; z-index: 8; top: calc(100% + var(--nf-space-2)); right: 0; display: flex; gap: var(--nf-space-2); padding: var(--nf-space-2); border: 1px solid var(--nf-color-border); border-radius: var(--nf-radius-sm); background: var(--nf-color-surface); box-shadow: var(--nf-shadow-card); }
.progress-share-menu__item { display: grid; width: 2.75rem; height: 2.75rem; padding: 0; place-items: center; border: 0; border-radius: var(--nf-radius-sm); background: transparent; color: var(--nf-color-text-muted); cursor: pointer; }
.progress-share-menu__item:hover { background: var(--nf-color-primary-soft); color: var(--nf-color-primary); }
</style>
