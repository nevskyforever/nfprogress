<script setup lang="ts">
import { nextTick, ref, watch } from 'vue'
import { EditorContent, useEditor } from '@tiptap/vue-3'
import type { Editor, JSONContent } from '@tiptap/core'
import type { TiptapDocument } from '@/types/documents'
import { createDocumentEditorExtensions } from './editorExtensions'
import NFEditorToolbar from './NFEditorToolbar.vue'

const props = defineProps<{
  content: TiptapDocument
  translate?: (source: string) => string
}>()
const emit = defineEmits<{
  update: [content: TiptapDocument]
  ready: [editor: Editor]
}>()
const viewport = ref<HTMLElement | null>(null)

const editor = useEditor({
  content: props.content,
  extensions: createDocumentEditorExtensions(),
  editorProps: {
    attributes: {
      class: 'nf-editor-content',
      'aria-label': 'Текст документа',
    },
  },
  onCreate: ({ editor }) => emit('ready', editor),
  onUpdate: ({ editor }) => emit('update', editor.getJSON() as TiptapDocument),
})

function sameContent(left: JSONContent, right: JSONContent): boolean {
  return JSON.stringify(left) === JSON.stringify(right)
}

watch(() => props.content, (next) => {
  if (!editor.value || sameContent(editor.value.getJSON(), next)) return
  editor.value.commands.setContent(next, { emitUpdate: false })
}, { deep: true })

function getEditor(): Editor | null {
  return editor.value ?? null
}

function getScrollContainer(): HTMLElement | null {
  return viewport.value
}

function focus(): void {
  editor.value?.commands.focus()
}

function getJSON(): TiptapDocument {
  return (editor.value?.getJSON() ?? props.content) as TiptapDocument
}

function setContent(content: TiptapDocument | string, emitUpdate = false): void {
  editor.value?.commands.setContent(content, { emitUpdate })
}

function getSelection(): number | null {
  return editor.value?.state.selection.from ?? null
}

async function setSelection(position: number): Promise<void> {
  if (!editor.value) return
  editor.value.commands.setTextSelection(Math.min(position, editor.value.state.doc.content.size))
  await nextTick()
}

defineExpose({ focus, getEditor, getJSON, getScrollContainer, getSelection, setContent, setSelection })
</script>

<template>
  <section class="nf-document-editor">
    <NFEditorToolbar v-if="editor" :editor="editor" :translate="translate" />
    <div ref="viewport" class="nf-document-editor__viewport">
      <div class="nf-document-editor__page">
        <EditorContent v-if="editor" :editor="editor" class="nf-document-editor__content" />
      </div>
    </div>
  </section>
</template>

<style scoped>
.nf-document-editor {
  display: flex;
  flex-direction: column;
  min-width: 0;
  min-height: 0;
  flex: 1;
  background: var(--nf-color-canvas);
}

.nf-document-editor__viewport {
  box-sizing: border-box;
  width: 100%;
  min-width: 0;
  padding: var(--nf-space-5);
  overflow: auto;
  scrollbar-gutter: stable;
}

.nf-document-editor__page {
  box-sizing: border-box;
  width: min(850px, 100%);
  min-height: 100%;
  margin: 0 auto;
  padding: 5rem 5.5rem;
  color: var(--nf-color-text);
  background: color-mix(in srgb, var(--nf-color-surface) 82%, white);
  box-shadow: var(--nf-shadow-card);
}

.nf-document-editor__content :deep(.nf-editor-content) {
  box-sizing: border-box;
  width: 100%;
  min-height: 0;
  color: inherit;
  font-family: Arial, sans-serif;
  font-size: 12pt;
  line-height: 1.5;
  background: transparent;
  outline: none;
  white-space: pre-wrap;
}

.nf-document-editor__content :deep(.nf-editor-content > :first-child) { margin-top: 0; }
.nf-document-editor__content :deep(.nf-editor-content > :last-child) { margin-bottom: 0; }

@media (max-width: 44rem) {
  .nf-document-editor__viewport { padding: var(--nf-space-2); }
  .nf-document-editor__page {
    padding: 2rem 1.25rem;
    box-shadow: none;
  }
}
</style>
