import type { Editor } from '@tiptap/core'

export const EDITOR_FONT_FAMILIES = ['Arial', 'Georgia', 'Times New Roman', 'Courier New'] as const
export const EDITOR_FONT_SIZES = [9, 10, 11, 12, 14, 16, 18, 20, 22, 24, 26, 28, 32, 36, 48, 72] as const
export const EDITOR_LINE_HEIGHTS = ['1', '1.15', '1.5', '2'] as const
export const EDITOR_TEXT_COLORS = ['#000000', '#374151', '#dc2626', '#ea580c', '#16a34a', '#2563eb', '#7c3aed'] as const
export const EDITOR_HIGHLIGHT_COLORS = ['#ffff00', '#bbf7d0', '#bae6fd', '#fecaca', '#fed7aa', '#ddd6fe'] as const

export type EditorBlock = 'paragraph' | `heading-${1 | 2 | 3 | 4 | 5 | 6}`
export type EditorAlignment = 'left' | 'center' | 'right' | 'justify'

export function activeChoice<T extends string>(choices: readonly T[], predicate: (choice: T) => boolean): T | '' {
  const active = choices.filter(predicate)
  return active.length === 1 ? (active[0] ?? '') : ''
}

export function currentFontFamily(editor: Editor): string {
  return activeChoice(EDITOR_FONT_FAMILIES, (fontFamily) => editor.isActive('textStyle', { fontFamily }))
}

export function currentFontSize(editor: Editor): string {
  return activeChoice(EDITOR_FONT_SIZES.map((size) => `${size}pt`), (fontSize) => editor.isActive('textStyle', { fontSize }))
}

export function currentLineHeight(editor: Editor): string {
  return activeChoice(EDITOR_LINE_HEIGHTS, (lineHeight) => (
    editor.isActive('paragraph', { lineHeight }) || editor.isActive('heading', { lineHeight })
  ))
}

export function currentBlock(editor: Editor): EditorBlock | '' {
  for (let level = 1; level <= 6; level += 1) {
    if (editor.isActive('heading', { level })) return `heading-${level}` as EditorBlock
  }
  return editor.isActive('paragraph') ? 'paragraph' : ''
}

export function setBlock(editor: Editor, block: EditorBlock): void {
  const chain = editor.chain().focus()
  if (block === 'paragraph') {
    chain.setParagraph().run()
    return
  }
  chain.setHeading({ level: Number(block.slice('heading-'.length)) as 1 | 2 | 3 | 4 | 5 | 6 }).run()
}

export function setDocumentLineHeight(editor: Editor, lineHeight: string): void {
  editor.chain().focus()
    .updateAttributes('paragraph', { lineHeight })
    .updateAttributes('heading', { lineHeight })
    .run()
}

export function clearFormatting(editor: Editor): void {
  editor.chain().focus().unsetAllMarks().clearNodes().run()
}
