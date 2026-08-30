<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, shallowRef } from 'vue'
import { Editor, EditorContent } from '@tiptap/vue-3'
import StarterKit from '@tiptap/starter-kit'
import Underline from '@tiptap/extension-underline'
import TaskList from '@tiptap/extension-task-list'
import TaskItem from '@tiptap/extension-task-item'
import Link from '@tiptap/extension-link'
import Image from '@tiptap/extension-image'
import { Table, TableRow, TableHeader, TableCell } from '@tiptap/extension-table'
import { documentsApi } from '@/api/documents'
import { pickDesktopWordFile } from '@/platform/files'
import { blobToBase64, exportDocx, importDocx } from '@/services/documentDocx'
import type { DocumentScope, ProjectDocument } from '@/types/documents'

const props = defineProps<{ scope: DocumentScope; title: string }>()
const editor = shallowRef<Editor>()
const documentState = ref<ProjectDocument | null>(null)
const loading = ref(true)
const search = ref('')
const status = ref('')
let saveTimer: number | undefined
let watchTimer: number | undefined

function currentContent() { return editor.value?.getJSON() as any }
function scheduleSave() { window.clearTimeout(saveTimer); saveTimer = window.setTimeout(() => void save(), 700) }
async function save() {
  if (!editor.value) return
  documentState.value = await documentsApi.save(props.scope, currentContent())
  status.value = 'Сохранено'
  if (documentState.value.docx_path) await writeLinkedWord()
}
async function writeLinkedWord() {
  if (!editor.value) return
  const blob = await exportDocx(currentContent())
  documentState.value = await documentsApi.writeDocx(props.scope, await blobToBase64(blob))
}
function download(blob: Blob, name: string) { const url = URL.createObjectURL(blob); const link = document.createElement('a'); link.href = url; link.download = name; link.click(); URL.revokeObjectURL(url) }
async function downloadWord() { if (editor.value) download(await exportDocx(currentContent()), `${props.title}.docx`) }
function selectImport() { const input = document.createElement('input'); input.type = 'file'; input.accept = '.docx'; input.onchange = async () => { const file = input.files?.[0]; if (!file || !editor.value) return; editor.value.commands.setContent(await importDocx(await file.arrayBuffer())); scheduleSave() }; input.click() }
async function linkWord() { const path = await pickDesktopWordFile('Связать с файлом Word', 'Word'); if (!path) return; documentState.value = await documentsApi.link(props.scope, path); await writeLinkedWord() }
async function checkExternal() {
  if (!documentState.value?.docx_path) return
  const external = await documentsApi.external(props.scope)
  if (!external.content_base64 || !external.hash || !editor.value) return
  const bytes = Uint8Array.from(atob(external.content_base64), (letter) => letter.charCodeAt(0))
  const imported = await importDocx(bytes.buffer)
  if (external.state === 'conflict') {
    const choice = window.prompt('Текст изменён и в NFProgress, и в Word: NFProgress / Word / обе', 'обе')?.toLowerCase()
    if (choice?.startsWith('n')) { await writeLinkedWord(); return }
    if (choice?.startsWith('о') || choice?.startsWith('b')) await downloadWord()
  }
  editor.value.commands.setContent(imported)
  documentState.value = await documentsApi.acceptWord(props.scope, currentContent(), external.hash)
  status.value = 'Импортировано изменение Word'
}
function findNext() { const term = search.value.trim(); if (!term || !editor.value) return; const text = editor.value.getText(); const index = text.toLowerCase().indexOf(term.toLowerCase()); if (index < 0) { status.value = 'Не найдено'; return }; editor.value.commands.setTextSelection({ from: index + 1, to: index + term.length + 1 }) }
function action(command: () => boolean) { command(); editor.value?.commands.focus() }
function addImage() { const source = window.prompt('URL или data URL изображения'); if (source) action(() => editor.value!.chain().focus().setImage({ src: source }).run()) }
function addLink() { const href = window.prompt('Адрес ссылки'); if (href) action(() => editor.value!.chain().focus().setLink({ href }).run()) }

onMounted(async () => {
  documentState.value = await documentsApi.get(props.scope)
  editor.value = new Editor({ content: documentState.value.content, extensions: [StarterKit, Underline, TaskList, TaskItem.configure({ nested: true }), Link.configure({ openOnClick: false }), Image, Table.configure({ resizable: true }), TableRow, TableHeader, TableCell], onUpdate: scheduleSave })
  loading.value = false
  watchTimer = window.setInterval(() => void checkExternal().catch(() => undefined), 5000)
})
onBeforeUnmount(() => { window.clearTimeout(saveTimer); window.clearInterval(watchTimer); void save(); editor.value?.destroy() })
</script>

<template>
  <section class="document-editor">
    <header><div><p class="eyebrow">Текст</p><h1>{{ title }}</h1></div><span>{{ status }}</span></header>
    <div v-if="loading">Открываем документ…</div>
    <template v-else>
      <div class="toolbar" aria-label="Форматирование текста">
        <button @click="action(() => editor!.chain().focus().toggleBold().run())"><b>B</b></button><button @click="action(() => editor!.chain().focus().toggleItalic().run())"><i>I</i></button><button @click="action(() => editor!.chain().focus().toggleUnderline().run())"><u>U</u></button><button @click="addLink">Ссылка</button><button @click="addImage">Изображение</button>
        <button @click="action(() => editor!.chain().focus().toggleHeading({ level: 2 }).run())">H2</button><button @click="action(() => editor!.chain().focus().toggleBulletList().run())">• Список</button><button @click="action(() => editor!.chain().focus().toggleTaskList().run())">☑</button><button @click="action(() => editor!.chain().focus().toggleBlockquote().run())">Цитата</button><button @click="action(() => editor!.chain().focus().insertTable({ rows: 3, cols: 3, withHeaderRow: true }).run())">Таблица</button>
        <button @click="action(() => editor!.chain().focus().undo().run())">↶</button><button @click="action(() => editor!.chain().focus().redo().run())">↷</button><button @click="selectImport">Импорт DOCX</button><button @click="downloadWord">Экспорт DOCX</button><button @click="linkWord">Связать с Word</button>
        <label>Поиск <input v-model="search" @keydown.enter.prevent="findNext"></label><button @click="findNext">Найти</button>
      </div>
      <EditorContent :editor="editor" class="editor-canvas" />
    </template>
  </section>
</template>

<style scoped>
.document-editor { width: min(100%, 72rem); margin: 0 auto; padding: var(--nf-space-6); color: var(--nf-color-text); }.document-editor header { display:flex; justify-content:space-between; gap:1rem; align-items:baseline }.document-editor h1,.eyebrow { margin:0 }.eyebrow { color:var(--nf-color-text-muted); font-size:.8rem; font-weight:700; text-transform:uppercase }.toolbar { display:flex; flex-wrap:wrap; gap:.4rem; margin:1rem 0; padding: .75rem; background:var(--nf-color-surface); border:1px solid var(--nf-color-border); border-radius:var(--nf-radius-md) }.toolbar button,.toolbar input { min-height:2rem; border:1px solid var(--nf-color-border); border-radius:.3rem; background:var(--nf-color-canvas); color:inherit; padding:.2rem .45rem }.toolbar label { display:flex; gap:.3rem; align-items:center }.editor-canvas { min-height:60vh; padding:clamp(1rem,3vw,3rem); border:1px solid var(--nf-color-border); border-radius:var(--nf-radius-md); background:var(--nf-color-surface); line-height:1.65 }.editor-canvas :deep(.ProseMirror) { min-height:52vh; outline:0 }.editor-canvas :deep(table) { width:100%; border-collapse:collapse }.editor-canvas :deep(td),.editor-canvas :deep(th) { border:1px solid var(--nf-color-border); padding:.5rem }.editor-canvas :deep(img) { max-width:100%; height:auto }.editor-canvas :deep(blockquote) { border-left:3px solid var(--nf-color-primary); margin-left:0; padding-left:1rem; color:var(--nf-color-text-muted) }
</style>
