<script setup lang="ts">
import { nextTick, ref, watch } from 'vue'

import { useLocaleStore } from '@/stores/locale'

const props = withDefaults(defineProps<{
  modelValue?: string | null
  disabled?: boolean
}>(), { modelValue: null, disabled: false })

const emit = defineEmits<{ 'update:modelValue': [value: string | null] }>()

const locale = useLocaleStore()
const t = locale.translate
const fileInput = ref<HTMLInputElement | null>(null)
const preview = ref<HTMLCanvasElement | null>(null)
const source = ref<HTMLImageElement | null>(null)
const zoom = ref(1)
const horizontal = ref(0)
const vertical = ref(0)
const error = ref('')
const lastEmitted = ref<string | null>(null)
let suppressCropUpdate = false

function draw(canvas: HTMLCanvasElement, width: number, height: number): void {
  const image = source.value
  if (!image) return
  canvas.width = width
  canvas.height = height
  const context = canvas.getContext('2d')
  if (!context) return
  const baseScale = Math.max(width / image.naturalWidth, height / image.naturalHeight)
  const imageWidth = image.naturalWidth * baseScale * zoom.value
  const imageHeight = image.naturalHeight * baseScale * zoom.value
  const offsetX = Math.max(0, imageWidth - width) * horizontal.value / 200
  const offsetY = Math.max(0, imageHeight - height) * vertical.value / 200
  context.clearRect(0, 0, width, height)
  context.drawImage(image, (width - imageWidth) / 2 + offsetX, (height - imageHeight) / 2 + offsetY, imageWidth, imageHeight)
}

function redraw(): void {
  if (preview.value && source.value) draw(preview.value, 240, 360)
}

function exportCover(): void {
  if (!source.value) return
  const canvas = document.createElement('canvas')
  draw(canvas, 600, 900)
  const value = canvas.toDataURL('image/jpeg', 0.86)
  lastEmitted.value = value
  emit('update:modelValue', value)
}

function updateCrop(): void {
  redraw()
  exportCover()
}

function centerImage(): void {
  zoom.value = 1
  horizontal.value = 0
  vertical.value = 0
  updateCrop()
}

function removeCover(): void {
  source.value = null
  error.value = ''
  if (fileInput.value) fileInput.value.value = ''
  lastEmitted.value = null
  emit('update:modelValue', null)
}

function loadImage(dataUrl: string, emitCroppedImage: boolean): void {
  const image = new Image()
  image.onload = async () => {
    suppressCropUpdate = true
    source.value = image
    zoom.value = 1
    horizontal.value = 0
    vertical.value = 0
    await nextTick()
    redraw()
    suppressCropUpdate = false
    if (emitCroppedImage) exportCover()
  }
  image.onerror = () => { error.value = t('Не удалось открыть изображение.') }
  image.src = dataUrl
}

function chooseFile(event: Event): void {
  const file = (event.target as HTMLInputElement).files?.[0]
  if (!file) return
  error.value = ''
  if (!file.type.startsWith('image/')) {
    error.value = t('Выберите файл изображения.')
    return
  }
  if (file.size > 20 * 1024 * 1024) {
    error.value = t('Изображение должно быть не больше 20 МБ.')
    return
  }
  const reader = new FileReader()
  reader.onload = () => {
    if (typeof reader.result === 'string') loadImage(reader.result, true)
  }
  reader.onerror = () => { error.value = t('Не удалось прочитать изображение.') }
  reader.readAsDataURL(file)
}

watch(() => props.modelValue, (value) => {
  if (value === lastEmitted.value) return
  if (value && value !== source.value?.src) loadImage(value, false)
  if (!value && source.value) source.value = null
}, { immediate: true })
watch([zoom, horizontal, vertical], () => {
  if (!suppressCropUpdate) updateCrop()
})
</script>

<template>
  <section class="cover-editor form-field--wide" :aria-label="t('Обложка проекта')">
    <div class="cover-editor__heading">
      <div>
        <strong>{{ t('Обложка проекта') }}</strong>
        <small>{{ t('Книжный формат 2:3. Выберите изображение и настройте кадр.') }}</small>
      </div>
      <button v-if="source" class="cover-editor__remove" type="button" :disabled="disabled" @click="removeCover">
        {{ t('Удалить') }}
      </button>
    </div>
    <div class="cover-editor__body">
      <canvas v-if="source" ref="preview" class="cover-editor__preview" width="240" height="360" :aria-label="t('Предпросмотр обложки')" role="img" />
      <div v-else class="cover-editor__placeholder" aria-hidden="true">▤</div>
      <div class="cover-editor__controls">
        <label class="nf-button nf-button--secondary cover-editor__choose">
          <input ref="fileInput" type="file" accept="image/jpeg,image/png,image/webp" :disabled="disabled" @change="chooseFile" />
          {{ source ? t('Заменить изображение') : t('Выбрать изображение') }}
        </label>
        <template v-if="source">
          <label>{{ t('Масштаб') }}
            <input v-model.number="zoom" type="range" min="1" max="3" step="0.01" :disabled="disabled" />
          </label>
          <label>{{ t('По горизонтали') }}
            <input v-model.number="horizontal" type="range" min="-100" max="100" step="1" :disabled="disabled" />
          </label>
          <label>{{ t('По вертикали') }}
            <input v-model.number="vertical" type="range" min="-100" max="100" step="1" :disabled="disabled" />
          </label>
          <button class="cover-editor__center" type="button" :disabled="disabled" @click="centerImage">{{ t('Отцентрировать') }}</button>
        </template>
        <p v-if="error" class="cover-editor__error" role="alert">{{ error }}</p>
      </div>
    </div>
  </section>
</template>

<style scoped>
.cover-editor { display: grid; gap: var(--nf-space-3); padding: var(--nf-space-4); border: 1px solid var(--nf-color-border); border-radius: var(--nf-radius-sm); background: var(--nf-color-surface-raised); }
.cover-editor__heading { display: flex; gap: var(--nf-space-3); align-items: start; justify-content: space-between; }
.cover-editor__heading strong, .cover-editor__heading small { display: block; }
.cover-editor__heading small { margin-top: var(--nf-space-1); color: var(--nf-color-text-muted); font-weight: 500; }
.cover-editor__body { display: flex; gap: var(--nf-space-4); align-items: center; }
.cover-editor__preview, .cover-editor__placeholder { width: 7.5rem; aspect-ratio: 2 / 3; border-radius: var(--nf-radius-sm); box-shadow: var(--nf-shadow-card); }
.cover-editor__preview { background: var(--nf-color-surface-muted); object-fit: cover; }
.cover-editor__placeholder { display: grid; place-items: center; border: 1px dashed var(--nf-color-border); color: var(--nf-color-text-muted); font-size: 2rem; }
.cover-editor__controls { display: grid; gap: var(--nf-space-2); min-width: 0; flex: 1; }
.cover-editor__controls label:not(.cover-editor__choose) { display: grid; gap: 0.15rem; color: var(--nf-color-text-muted); font-size: 0.78rem; font-weight: 700; }
.cover-editor__choose { justify-self: start; cursor: pointer; }
.cover-editor__choose input { position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0 0 0 0); clip-path: inset(50%); white-space: nowrap; }
.cover-editor__remove, .cover-editor__center { padding: 0; border: 0; background: transparent; color: var(--nf-color-primary); cursor: pointer; font: inherit; font-weight: 700; text-align: left; }
.cover-editor__remove { color: var(--nf-color-danger); }
.cover-editor__error { margin: 0; color: var(--nf-color-danger); font-size: 0.8rem; }
@media (max-width: 30rem) { .cover-editor__body { align-items: start; } .cover-editor__preview, .cover-editor__placeholder { width: 6rem; } }
</style>
