<script setup lang="ts">
const props = defineProps<{
  zoom: number
  typewriterMode: boolean
  translate?: (source: string) => string
}>()
const emit = defineEmits<{
  toggleTypewriter: []
  zoom: [value: number]
}>()
const t = (source: string) => props.translate?.(source) ?? source
const typewriterTitle = () => t(props.typewriterMode
  ? 'Выключить режим печатной машинки'
  : 'Включить режим печатной машинки')
</script>

<template>
  <div class="nf-editor-status-controls document-editor-view__view-controls">
    <button
      type="button"
      class="nf-editor-status-controls__typewriter document-editor-view__typewriter-toggle"
      :class="{ 'is-active': typewriterMode, 'document-editor-view__typewriter-toggle--active': typewriterMode }"
      :title="typewriterTitle()"
      :aria-label="typewriterTitle()"
      :aria-pressed="typewriterMode"
      @click="emit('toggleTypewriter')"
    >
      <svg class="document-editor-view__typewriter-icon" viewBox="0 0 24 24" aria-hidden="true" focusable="false">
        <path d="M7 8.5V4h10v4.5" />
        <path d="M5.5 8.5h13a3 3 0 0 1 3 3V16h-3v4H5.5v-4h-3v-4.5a3 3 0 0 1 3-3Z" />
        <path d="M6.5 13h11M7.5 16.5h9" />
        <circle cx="8" cy="18.5" r=".65" />
        <circle cx="11" cy="18.5" r=".65" />
        <circle cx="14" cy="18.5" r=".65" />
        <circle cx="17" cy="18.5" r=".65" />
      </svg>
    </button>
    <div class="nf-editor-status-controls__zoom document-editor-view__zoom" role="group" :aria-label="t('Масштаб документа')">
      <button type="button" :title="t('Уменьшить масштаб')" :aria-label="t('Уменьшить масштаб')" :disabled="zoom <= 70" @click="emit('zoom', zoom - 10)">−</button>
      <button type="button" :title="t('Сбросить масштаб')" :aria-label="t('Сбросить масштаб')" @click="emit('zoom', 100)">{{ zoom }}%</button>
      <button type="button" :title="t('Увеличить масштаб')" :aria-label="t('Увеличить масштаб')" :disabled="zoom >= 500" @click="emit('zoom', zoom + 10)">+</button>
    </div>
  </div>
</template>

<style scoped>
.nf-editor-status-controls { display: inline-flex; flex: 0 0 auto; align-items: center; gap: .4rem; }
.nf-editor-status-controls__typewriter { display: inline-grid; place-items: center; box-sizing: border-box; width: 2rem; height: 1.8rem; padding: 0; color: var(--nf-color-text); cursor: pointer; background: transparent; border: 1px solid var(--nf-color-border); border-radius: var(--nf-radius-sm); }
.nf-editor-status-controls__typewriter:hover,
.nf-editor-status-controls__typewriter:focus-visible { background: color-mix(in srgb, var(--nf-color-primary) 12%, transparent); outline: none; }
.nf-editor-status-controls__typewriter.is-active { color: var(--nf-color-primary); background: color-mix(in srgb, var(--nf-color-primary) 16%, transparent); border-color: var(--nf-color-primary); }
.nf-editor-status-controls__typewriter svg { width: 1.1rem; height: 1.1rem; fill: none; stroke: currentColor; stroke-linecap: round; stroke-linejoin: round; stroke-width: 1.6; }
.nf-editor-status-controls__zoom { display: inline-flex; align-items: center; overflow: hidden; border: 1px solid var(--nf-color-border); border-radius: var(--nf-radius-sm); }
.nf-editor-status-controls__zoom button { min-width: 2rem; min-height: 1.8rem; padding: 0 .45rem; color: var(--nf-color-text); font: inherit; font-size: .8rem; font-weight: 700; cursor: pointer; background: transparent; border: 0; }
.nf-editor-status-controls__zoom button + button { border-left: 1px solid var(--nf-color-border); }
.nf-editor-status-controls__zoom button:hover:not(:disabled),
.nf-editor-status-controls__zoom button:focus-visible { background: color-mix(in srgb, var(--nf-color-primary) 12%, transparent); outline: none; }
.nf-editor-status-controls__zoom button:disabled { color: var(--nf-color-text-muted); cursor: not-allowed; opacity: .55; }
</style>
