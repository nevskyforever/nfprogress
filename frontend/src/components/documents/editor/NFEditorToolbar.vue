<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import type { Editor } from '@tiptap/core'
import {
  AlignCenterOutlined,
  AlignLeftOutlined,
  AlignRightOutlined,
  BoldOutlined,
  ClearOutlined,
  FontColorsOutlined,
  HighlightOutlined,
  ItalicOutlined,
  MenuOutlined,
  MinusOutlined,
  OrderedListOutlined,
  RedoOutlined,
  StrikethroughOutlined,
  UnderlineOutlined,
  UndoOutlined,
  UnorderedListOutlined,
} from '@ant-design/icons-vue'
import {
  EDITOR_FONT_FAMILIES,
  EDITOR_FONT_SIZES,
  EDITOR_HIGHLIGHT_COLORS,
  EDITOR_LINE_HEIGHTS,
  EDITOR_TEXT_COLORS,
  clearFormatting,
  currentBlock,
  currentFontFamily,
  currentFontSize,
  currentLineHeight,
  setBlock,
  setDocumentLineHeight,
  type EditorAlignment,
  type EditorBlock,
} from './editorCommands'

const props = defineProps<{
  editor: Editor
  translate?: (source: string) => string
}>()

const revision = ref(0)
const t = (source: string) => props.translate?.(source) ?? source
const refresh = () => { revision.value += 1 }
const alignmentControls = [
  { value: 'left' as const, label: 'По левому краю', icon: AlignLeftOutlined },
  { value: 'center' as const, label: 'По центру', icon: AlignCenterOutlined },
  { value: 'right' as const, label: 'По правому краю', icon: AlignRightOutlined },
  { value: 'justify' as const, label: 'По ширине', icon: MenuOutlined },
]

onMounted(() => {
  props.editor.on('transaction', refresh)
  props.editor.on('selectionUpdate', refresh)
})
onBeforeUnmount(() => {
  props.editor.off('transaction', refresh)
  props.editor.off('selectionUpdate', refresh)
})

const fontFamily = computed(() => { void revision.value; return currentFontFamily(props.editor) })
const fontSize = computed(() => { void revision.value; return currentFontSize(props.editor) })
const lineHeight = computed(() => { void revision.value; return currentLineHeight(props.editor) })
const block = computed(() => { void revision.value; return currentBlock(props.editor) })
const textColor = computed(() => { void revision.value; return String(props.editor.getAttributes('textStyle').color ?? '#000000') })
const highlightColor = computed(() => { void revision.value; return String(props.editor.getAttributes('highlight').color ?? '#ffff00') })
const canUndo = computed(() => { void revision.value; return props.editor.can().undo() })
const canRedo = computed(() => { void revision.value; return props.editor.can().redo() })

function valueFrom(event: Event): string {
  return (event.target as HTMLInputElement | HTMLSelectElement).value
}
function setFontFamily(event: Event): void {
  props.editor.chain().focus().setFontFamily(valueFrom(event)).run()
}
function setFontSize(event: Event): void {
  props.editor.chain().focus().setFontSize(valueFrom(event)).run()
}
function setLineHeight(event: Event): void {
  setDocumentLineHeight(props.editor, valueFrom(event))
}
function setCurrentBlock(event: Event): void {
  const value = valueFrom(event)
  if (value) setBlock(props.editor, value as EditorBlock)
}
function setTextColor(event: Event): void {
  props.editor.chain().focus().setColor(valueFrom(event)).run()
}
function setHighlightColor(event: Event): void {
  props.editor.chain().focus().setHighlight({ color: valueFrom(event) }).run()
}
function setAlignment(alignment: EditorAlignment): void {
  props.editor.chain().focus().setTextAlign(alignment).run()
}
function isActive(name: string, attrs?: Record<string, unknown>): boolean {
  void revision.value
  return props.editor.isActive(name, attrs)
}
function isAlignmentActive(alignment: EditorAlignment): boolean {
  void revision.value
  return props.editor.isActive({ textAlign: alignment })
}
</script>

<template>
  <div class="nf-editor-toolbar" role="toolbar" :aria-label="t('Панель форматирования')">
    <div class="nf-editor-toolbar__group nf-editor-toolbar__group--selects">
      <label>
        <span class="nf-editor-toolbar__sr-only">{{ t('Шрифт') }}</span>
        <select :value="fontFamily" :title="t('Шрифт')" :aria-label="t('Шрифт')" @change="setFontFamily">
          <option value="" disabled>—</option>
          <option v-for="font in EDITOR_FONT_FAMILIES" :key="font" :value="font">{{ font }}</option>
        </select>
      </label>
      <label>
        <span class="nf-editor-toolbar__sr-only">{{ t('Размер текста') }}</span>
        <select :value="fontSize" :title="t('Размер текста')" :aria-label="t('Размер текста')" @change="setFontSize">
          <option value="" disabled>—</option>
          <option v-for="size in EDITOR_FONT_SIZES" :key="size" :value="`${size}pt`">{{ size }} pt</option>
        </select>
      </label>
      <label>
        <span class="nf-editor-toolbar__sr-only">{{ t('Межстрочный интервал') }}</span>
        <select :value="lineHeight" :title="t('Межстрочный интервал')" :aria-label="t('Межстрочный интервал')" @change="setLineHeight">
          <option value="" disabled>—</option>
          <option v-for="height in EDITOR_LINE_HEIGHTS" :key="height" :value="height">{{ height }}</option>
        </select>
      </label>
    </div>

    <div class="nf-editor-toolbar__group">
      <button type="button" :title="t('Отменить')" :aria-label="t('Отменить')" :disabled="!canUndo" @mousedown.prevent @click="editor.chain().focus().undo().run()"><UndoOutlined class="nf-editor-toolbar__icon" /></button>
      <button type="button" :title="t('Повторить')" :aria-label="t('Повторить')" :disabled="!canRedo" @mousedown.prevent @click="editor.chain().focus().redo().run()"><RedoOutlined class="nf-editor-toolbar__icon" /></button>
    </div>

    <div class="nf-editor-toolbar__group">
      <button type="button" :title="t('Полужирный')" :aria-label="t('Полужирный')" :aria-pressed="isActive('bold')" :class="{ 'is-active': isActive('bold') }" @mousedown.prevent @click="editor.chain().focus().toggleBold().run()"><BoldOutlined class="nf-editor-toolbar__icon" /></button>
      <button type="button" :title="t('Курсив')" :aria-label="t('Курсив')" :aria-pressed="isActive('italic')" :class="{ 'is-active': isActive('italic') }" @mousedown.prevent @click="editor.chain().focus().toggleItalic().run()"><ItalicOutlined class="nf-editor-toolbar__icon" /></button>
      <button type="button" :title="t('Подчёркнутый')" :aria-label="t('Подчёркнутый')" :aria-pressed="isActive('underline')" :class="{ 'is-active': isActive('underline') }" @mousedown.prevent @click="editor.chain().focus().toggleUnderline().run()"><UnderlineOutlined class="nf-editor-toolbar__icon" /></button>
      <button type="button" :title="t('Зачёркнутый')" :aria-label="t('Зачёркнутый')" :aria-pressed="isActive('strike')" :class="{ 'is-active': isActive('strike') }" @mousedown.prevent @click="editor.chain().focus().toggleStrike().run()"><StrikethroughOutlined class="nf-editor-toolbar__icon" /></button>
    </div>

    <div class="nf-editor-toolbar__group">
      <button type="button" :title="t('Нижний индекс')" :aria-label="t('Нижний индекс')" :aria-pressed="isActive('subscript')" :class="{ 'is-active': isActive('subscript') }" @mousedown.prevent @click="editor.chain().focus().toggleSubscript().run()">
        <svg class="nf-editor-toolbar__icon nf-editor-toolbar__icon--stroke" viewBox="0 0 24 24" aria-hidden="true"><path d="m4 6 8 12M12 6 4 18M15 16h4l-4 5h4" /></svg>
      </button>
      <button type="button" :title="t('Верхний индекс')" :aria-label="t('Верхний индекс')" :aria-pressed="isActive('superscript')" :class="{ 'is-active': isActive('superscript') }" @mousedown.prevent @click="editor.chain().focus().toggleSuperscript().run()">
        <svg class="nf-editor-toolbar__icon nf-editor-toolbar__icon--stroke" viewBox="0 0 24 24" aria-hidden="true"><path d="m4 6 8 12M12 6 4 18M15 3h4l-4 5h4" /></svg>
      </button>
    </div>

    <div class="nf-editor-toolbar__group nf-editor-toolbar__group--colors">
      <label class="nf-editor-toolbar__color" :title="t('Цвет текста')">
        <FontColorsOutlined class="nf-editor-toolbar__icon" />
        <input type="color" list="nf-editor-text-colors" :value="textColor" :aria-label="t('Цвет текста')" @input="setTextColor">
      </label>
      <datalist id="nf-editor-text-colors"><option v-for="color in EDITOR_TEXT_COLORS" :key="color" :value="color" /></datalist>
      <label class="nf-editor-toolbar__color" :title="t('Цвет выделения')">
        <HighlightOutlined class="nf-editor-toolbar__icon" />
        <input type="color" list="nf-editor-highlight-colors" :value="highlightColor" :aria-label="t('Цвет выделения')" @input="setHighlightColor">
      </label>
      <datalist id="nf-editor-highlight-colors"><option v-for="color in EDITOR_HIGHLIGHT_COLORS" :key="color" :value="color" /></datalist>
    </div>

    <div class="nf-editor-toolbar__group">
      <label>
        <span class="nf-editor-toolbar__sr-only">{{ t('Стиль абзаца') }}</span>
        <select :value="block" :title="t('Стиль абзаца')" :aria-label="t('Стиль абзаца')" @change="setCurrentBlock">
          <option value="" disabled>—</option>
          <option value="paragraph">{{ t('Абзац') }}</option>
          <option v-for="level in 6" :key="level" :value="`heading-${level}`">{{ t('Заголовок') }} {{ level }}</option>
        </select>
      </label>
      <button type="button" :title="t('Маркированный список')" :aria-label="t('Маркированный список')" :aria-pressed="isActive('bulletList')" :class="{ 'is-active': isActive('bulletList') }" @mousedown.prevent @click="editor.chain().focus().toggleBulletList().run()"><UnorderedListOutlined class="nf-editor-toolbar__icon" /></button>
      <button type="button" :title="t('Нумерованный список')" :aria-label="t('Нумерованный список')" :aria-pressed="isActive('orderedList')" :class="{ 'is-active': isActive('orderedList') }" @mousedown.prevent @click="editor.chain().focus().toggleOrderedList().run()"><OrderedListOutlined class="nf-editor-toolbar__icon" /></button>
    </div>

    <div class="nf-editor-toolbar__group">
      <button v-for="alignment in alignmentControls" :key="alignment.value" type="button" :title="t(alignment.label)" :aria-label="t(alignment.label)" :aria-pressed="isAlignmentActive(alignment.value)" :class="{ 'is-active': isAlignmentActive(alignment.value) }" @mousedown.prevent @click="setAlignment(alignment.value)"><component :is="alignment.icon" class="nf-editor-toolbar__icon" /></button>
    </div>

    <div class="nf-editor-toolbar__group">
      <button type="button" :title="t('Цитата')" :aria-label="t('Цитата')" :aria-pressed="isActive('blockquote')" :class="{ 'is-active': isActive('blockquote') }" @mousedown.prevent @click="editor.chain().focus().toggleBlockquote().run()">
        <svg class="nf-editor-toolbar__icon nf-editor-toolbar__icon--filled" viewBox="0 0 24 24" aria-hidden="true"><path d="M4 6h7v6H7.5c.1 2 .9 3.5 2.7 4.6L8.8 19C5.6 17.2 4 14.5 4 11V6Zm9 0h7v6h-3.5c.1 2 .9 3.5 2.7 4.6L17.8 19C14.6 17.2 13 14.5 13 11V6Z" /></svg>
      </button>
      <button type="button" :title="t('Горизонтальная линия')" :aria-label="t('Горизонтальная линия')" @mousedown.prevent @click="editor.chain().focus().setHorizontalRule().run()"><MinusOutlined class="nf-editor-toolbar__icon" /></button>
      <button type="button" :title="t('Очистить форматирование')" :aria-label="t('Очистить форматирование')" @mousedown.prevent @click="clearFormatting(editor)"><ClearOutlined class="nf-editor-toolbar__icon" /></button>
    </div>
  </div>
</template>

<style scoped>
.nf-editor-toolbar {
  display: flex;
  box-sizing: border-box;
  flex: 0 0 auto;
  align-items: center;
  min-width: 0;
  min-height: 2.9rem;
  padding: .3rem .45rem;
  overflow-x: auto;
  overflow-y: hidden;
  color: var(--nf-color-text);
  background: var(--nf-color-surface);
  border-bottom: 1px solid var(--nf-color-border);
  scrollbar-width: thin;
}
.nf-editor-toolbar__group { display: inline-flex; flex: 0 0 auto; align-items: center; gap: .16rem; padding: 0 .35rem; border-right: 1px solid var(--nf-color-border); }
.nf-editor-toolbar__group:last-child { border-right: 0; }
.nf-editor-toolbar button,
.nf-editor-toolbar select {
  box-sizing: border-box;
  height: 2rem;
  color: var(--nf-color-text);
  font: inherit;
  font-size: .78rem;
  background: transparent;
  border: 1px solid transparent;
  border-radius: var(--nf-radius-sm);
}
.nf-editor-toolbar button { display: inline-grid; width: 2rem; min-width: 2rem; padding: 0; place-items: center; line-height: 1; cursor: pointer; }
.nf-editor-toolbar select { max-width: 9rem; padding: 0 1.35rem 0 .4rem; border-color: var(--nf-color-border); }
.nf-editor-toolbar button:hover:not(:disabled),
.nf-editor-toolbar button:focus-visible,
.nf-editor-toolbar select:focus-visible { background: color-mix(in srgb, var(--nf-color-primary) 11%, transparent); border-color: var(--nf-color-primary); outline: none; }
.nf-editor-toolbar button.is-active { color: var(--nf-color-primary); background: color-mix(in srgb, var(--nf-color-primary) 16%, transparent); }
.nf-editor-toolbar button:disabled { cursor: not-allowed; opacity: .42; }
.nf-editor-toolbar__icon { display: inline-flex; width: 1.1rem; height: 1.1rem; align-items: center; justify-content: center; flex: 0 0 1.1rem; font-size: 1.1rem; }
.nf-editor-toolbar__icon--stroke { fill: none; stroke: currentColor; stroke-width: 1.8; stroke-linecap: round; stroke-linejoin: round; }
.nf-editor-toolbar__icon--filled { fill: currentColor; stroke: none; }
.nf-editor-toolbar__color { position: relative; display: grid; box-sizing: border-box; width: 2rem; height: 2rem; place-items: center; cursor: pointer; border: 1px solid transparent; border-radius: var(--nf-radius-sm); }
.nf-editor-toolbar__color:hover,
.nf-editor-toolbar__color:focus-within { background: color-mix(in srgb, var(--nf-color-primary) 11%, transparent); border-color: var(--nf-color-primary); }
.nf-editor-toolbar__color input { position: absolute; inset: auto .2rem .12rem; width: 1.6rem; height: .32rem; padding: 0; cursor: pointer; border: 0; }
.nf-editor-toolbar__sr-only { position: absolute; width: 1px; height: 1px; padding: 0; overflow: hidden; clip: rect(0, 0, 0, 0); white-space: nowrap; border: 0; }
@media (max-width: 44rem) {
  .nf-editor-toolbar { padding-inline: .2rem; }
  .nf-editor-toolbar__group { padding-inline: .2rem; }
}
</style>
