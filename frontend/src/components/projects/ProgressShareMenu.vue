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
  buttonClass: '',
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
      class="progress-share-menu__trigger"
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
.progress-share-menu__trigger {
  display: inline-grid;
  width: 2.75rem;
  height: 2.75rem;
  padding: 0;
  place-items: center;
  border: 1px solid var(--nf-color-border);
  border-radius: var(--nf-radius-sm);
  background: var(--nf-color-surface-raised);
  color: var(--nf-color-text-muted);
  cursor: pointer;
  transition: background-color 140ms ease, border-color 140ms ease, color 140ms ease;
}
.progress-share-menu__trigger > :first-child { font-size: 1.05rem; }
.progress-share-menu__trigger:hover:not(:disabled),
.progress-share-menu__trigger[aria-expanded="true"] {
  border-color: var(--nf-color-primary);
  background: var(--nf-color-primary-soft);
  color: var(--nf-color-primary);
}
.progress-share-menu__trigger:disabled { opacity: 0.45; cursor: not-allowed; }
.progress-share-menu__trigger:focus-visible,
.progress-share-menu__item:focus-visible { outline: 3px solid var(--nf-color-primary-soft); outline-offset: 2px; }
.progress-share-menu__chevron { position: absolute; right: 0.16rem; bottom: 0.16rem; padding: 0.02rem; border-radius: 50%; background: var(--nf-color-surface-raised); font-size: 0.56rem; }
.progress-share-menu__list {
  position: absolute;
  z-index: 8;
  top: calc(100% + var(--nf-space-2));
  right: 0;
  display: flex;
  gap: 0.2rem;
  padding: 0.3rem;
  border: 1px solid var(--nf-color-border);
  border-radius: calc(var(--nf-radius-sm) + 0.2rem);
  background: var(--nf-color-surface);
  box-shadow: var(--nf-shadow-card);
  animation: progress-share-menu-in 140ms ease-out;
}
.progress-share-menu__item { display: grid; width: 2.45rem; height: 2.45rem; padding: 0; place-items: center; border: 0; border-radius: var(--nf-radius-sm); background: transparent; color: var(--nf-color-text-muted); cursor: pointer; }
.progress-share-menu__item:hover { background: var(--nf-color-primary-soft); color: var(--nf-color-primary); }
@keyframes progress-share-menu-in { from { opacity: 0; transform: translateY(-0.2rem); } to { opacity: 1; transform: translateY(0); } }

@media (prefers-reduced-motion: reduce) {
  .progress-share-menu__trigger { transition: none; }
  .progress-share-menu__list { animation: none; }
}
</style>
