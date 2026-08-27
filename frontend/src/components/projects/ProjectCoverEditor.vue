<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue'
import { IonContent, IonHeader, IonModal } from '@ionic/vue'

import { useLocaleStore } from '@/stores/locale'

const props = withDefaults(defineProps<{ modelValue?: string | null; disabled?: boolean }>(), {
  modelValue: null,
  disabled: false,
})
const emit = defineEmits<{ 'update:modelValue': [value: string | null] }>()
const locale = useLocaleStore()
const t = locale.translate
const fileInput = ref<HTMLInputElement | null>(null)
const canvas = ref<HTMLCanvasElement | null>(null)
const source = ref<HTMLImageElement | null>(null)
const cropOpen = ref(false)
const zoom = ref(1)
const horizontal = ref(0)
const vertical = ref(0)
const error = ref('')
const hasCover = computed(() => Boolean(props.modelValue))
let dragging: { x: number; y: number } | null = null

function imageGeometry(width: number, height: number) {
  const image = source.value
  if (!image) return null
  const scale = Math.max(width / image.naturalWidth, height / image.naturalHeight) * zoom.value
  const imageWidth = image.naturalWidth * scale
  const imageHeight = image.naturalHeight * scale
  return { image, imageWidth, imageHeight, overflowX: Math.max(0, imageWidth - width), overflowY: Math.max(0, imageHeight - height) }
}

function draw(target: HTMLCanvasElement, width: number, height: number): void {
  const geometry = imageGeometry(width, height)
  if (!geometry) return
  target.width = width
  target.height = height
  const context = target.getContext('2d')
  if (!context) return
  const x = (width - geometry.imageWidth) / 2 + geometry.overflowX * horizontal.value / 200
  const y = (height - geometry.imageHeight) / 2 + geometry.overflowY * vertical.value / 200
  context.clearRect(0, 0, width, height)
  context.drawImage(geometry.image, x, y, geometry.imageWidth, geometry.imageHeight)
}

function redraw(): void {
  if (canvas.value && source.value) draw(canvas.value, 360, 540)
}

function resetCrop(): void {
  zoom.value = 1
  horizontal.value = 0
  vertical.value = 0
  redraw()
}

function compactDataUrl(): string | null {
  if (!source.value) return null
  let width = 600
  let height = 900
  for (let attempt = 0; attempt < 5; attempt += 1) {
    const target = document.createElement('canvas')
    draw(target, width, height)
    for (let quality = 0.84; quality >= 0.48; quality -= 0.09) {
      const value = target.toDataURL('image/jpeg', quality)
      if (value.length <= 1_350_000) return value
    }
    width = Math.round(width * 0.8)
    height = Math.round(height * 0.8)
  }
  return null
}

function saveCrop(): void {
  const value = compactDataUrl()
  if (!value) {
    error.value = t('Не удалось подготовить обложку. Выберите другое изображение.')
    return
  }
  emit('update:modelValue', value)
  cropOpen.value = false
}

function openExistingCover(): void {
  if (!props.modelValue) return
  loadImage(props.modelValue)
}

function loadImage(dataUrl: string): void {
  const image = new Image()
  image.onload = async () => {
    source.value = image
    zoom.value = 1
    horizontal.value = 0
    vertical.value = 0
    cropOpen.value = true
    await nextTick()
    redraw()
  }
  image.onerror = () => { error.value = t('Не удалось открыть изображение.') }
  image.src = dataUrl
}

function chooseFile(event: Event): void {
  const file = (event.target as HTMLInputElement).files?.[0]
  if (!file) return
  error.value = ''
  if (!file.type.startsWith('image/')) { error.value = t('Выберите файл изображения.'); return }
  if (file.size > 20 * 1024 * 1024) { error.value = t('Изображение должно быть не больше 20 МБ.'); return }
  const reader = new FileReader()
  reader.onload = () => { if (typeof reader.result === 'string') loadImage(reader.result) }
  reader.onerror = () => { error.value = t('Не удалось прочитать изображение.') }
  reader.readAsDataURL(file)
}

function startDrag(event: PointerEvent): void {
  if (!canvas.value || props.disabled) return
  dragging = { x: event.clientX, y: event.clientY }
  canvas.value.setPointerCapture(event.pointerId)
}

function moveDrag(event: PointerEvent): void {
  if (!dragging) return
  const geometry = imageGeometry(360, 540)
  if (!geometry) return
  if (geometry.overflowX) horizontal.value = Math.max(-100, Math.min(100, horizontal.value + (event.clientX - dragging.x) * 200 / geometry.overflowX))
  if (geometry.overflowY) vertical.value = Math.max(-100, Math.min(100, vertical.value + (event.clientY - dragging.y) * 200 / geometry.overflowY))
  dragging = { x: event.clientX, y: event.clientY }
  redraw()
}

function stopDrag(): void { dragging = null }
function removeCover(): void { emit('update:modelValue', null); error.value = ''; if (fileInput.value) fileInput.value.value = '' }

watch([zoom, horizontal, vertical], redraw)
</script>

<template>
  <section class="cover-editor form-field--wide" :aria-label="t('Обложка проекта')">
    <div class="cover-editor__heading"><div><strong>{{ t('Обложка проекта') }}</strong><small>{{ t('Добавьте книжную обложку для карточки проекта.') }}</small></div><button v-if="hasCover" type="button" class="cover-editor__remove" :disabled="disabled" @click="removeCover">{{ t('Удалить') }}</button></div>
    <div class="cover-editor__summary">
      <img v-if="modelValue" :src="modelValue" alt="" class="cover-editor__thumbnail" />
      <div v-else class="cover-editor__empty" aria-hidden="true">▤</div>
      <div><label class="nf-button nf-button--secondary cover-editor__choose"><input ref="fileInput" type="file" accept="image/jpeg,image/png,image/webp" :disabled="disabled" @change="chooseFile" />{{ hasCover ? t('Заменить изображение') : t('Выбрать изображение') }}</label><button v-if="hasCover" type="button" class="cover-editor__adjust" :disabled="disabled" @click="openExistingCover">{{ t('Кадрировать и переместить') }}</button><p v-if="error" role="alert">{{ error }}</p></div>
    </div>
  </section>

  <IonModal :is-open="cropOpen" css-class="cover-crop-modal" :backdrop-dismiss="!disabled" @did-dismiss="cropOpen = false">
    <IonHeader class="cover-crop-modal__header ion-no-border"><div><p>{{ t('Обложка проекта') }}</p><h2>{{ t('Настройте кадр') }}</h2></div></IonHeader>
    <IonContent class="cover-crop-modal__content"><div class="cover-cropper"><canvas ref="canvas" class="cover-cropper__canvas" width="360" height="540" role="img" :aria-label="t('Предпросмотр обложки: перетаскивайте изображение для кадрирования')" @pointerdown="startDrag" @pointermove="moveDrag" @pointerup="stopDrag" @pointercancel="stopDrag" /><label>{{ t('Масштаб') }}<input v-model.number="zoom" type="range" min="1" max="3" step="0.01" :disabled="disabled" /></label><p>{{ t('Перетаскивайте изображение в рамке, чтобы выбрать нужный фрагмент.') }}</p><div class="cover-cropper__actions"><button type="button" class="nf-button nf-button--secondary" :disabled="disabled" @click="resetCrop">{{ t('Отцентрировать') }}</button><button type="button" class="nf-button nf-button--secondary" :disabled="disabled" @click="cropOpen = false">{{ t('Отмена') }}</button><button type="button" class="nf-button" :disabled="disabled" @click="saveCrop">{{ t('Готово') }}</button></div></div></IonContent>
  </IonModal>
</template>

<style scoped>
.cover-editor { display: grid; gap: var(--nf-space-3); padding: var(--nf-space-4); border: 1px solid var(--nf-color-border); border-radius: var(--nf-radius-sm); background: var(--nf-color-surface-raised); }.cover-editor__heading,.cover-editor__summary { display: flex; gap: var(--nf-space-3); align-items: center; justify-content: space-between; }.cover-editor__heading strong,.cover-editor__heading small { display: block; }.cover-editor__heading small,.cover-editor__summary p { margin: var(--nf-space-1) 0 0; color: var(--nf-color-text-muted); font-weight: 500; }.cover-editor__thumbnail,.cover-editor__empty { width: 4.5rem; aspect-ratio: 2 / 3; border-radius: var(--nf-radius-sm); object-fit: cover; }.cover-editor__empty { display: grid; place-items: center; border: 1px dashed var(--nf-color-border); color: var(--nf-color-text-muted); }.cover-editor__summary > div:last-child { display: grid; gap: var(--nf-space-2); justify-items: start; }.cover-editor__choose { cursor: pointer; }.cover-editor__choose input { position: absolute; width: 1px; height: 1px; overflow: hidden; clip-path: inset(50%); }.cover-editor__remove,.cover-editor__adjust { padding: 0; border: 0; background: transparent; color: var(--nf-color-primary); cursor: pointer; font: inherit; font-weight: 700; }.cover-editor__remove,.cover-editor__summary p { color: var(--nf-color-danger); }
</style>

<style>
.cover-crop-modal { --width: min(32rem, calc(100vw - 2rem)); --height: min(52rem, calc(100dvh - 2rem)); --border-radius: var(--nf-radius-lg); --background: var(--nf-color-surface); }.cover-crop-modal__header { padding: var(--nf-space-5); background: var(--nf-color-surface); }.cover-crop-modal__header p { margin: 0 0 var(--nf-space-1); color: var(--nf-color-primary); font-size: .75rem; font-weight: 800; letter-spacing: .1em; text-transform: uppercase; }.cover-crop-modal__header h2 { margin: 0; font-family: var(--nf-font-serif); }.cover-crop-modal__content { --background: var(--nf-color-surface); --padding-start: var(--nf-space-5); --padding-end: var(--nf-space-5); }.cover-cropper { display: grid; gap: var(--nf-space-4); justify-items: center; padding-bottom: var(--nf-space-5); }.cover-cropper__canvas { width: min(100%, 20rem); aspect-ratio: 2 / 3; border-radius: var(--nf-radius-sm); background: var(--nf-color-surface-muted); box-shadow: var(--nf-shadow-card); cursor: grab; touch-action: none; }.cover-cropper__canvas:active { cursor: grabbing; }.cover-cropper label { display: grid; width: min(100%, 20rem); gap: var(--nf-space-2); font-weight: 700; }.cover-cropper p { margin: 0; color: var(--nf-color-text-muted); text-align: center; }.cover-cropper__actions { display: flex; flex-wrap: wrap; gap: var(--nf-space-2); justify-content: center; }.cover-cropper__actions .nf-button:last-child { margin-left: auto; }
</style>
