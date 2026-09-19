import type { Editor } from '@tiptap/core'

export const EDITOR_FONT_FAMILIES = ['Arial', 'Georgia', 'Times New Roman', 'Courier New'] as const
export const EDITOR_FONT_SIZES = [9, 10, 11, 12, 14, 16, 18, 20, 22, 24, 26, 28, 32, 36, 48, 72] as const
export const EDITOR_LINE_HEIGHTS = ['1', '1.15', '1.5', '2'] as const
export const DEFAULT_FONT_FAMILY = 'Arial'
export const DEFAULT_FONT_SIZE = '12pt'
export const DEFAULT_LINE_HEIGHT = '1.5'
export const EDITOR_TEXT_COLORS = ['#000000', '#374151', '#dc2626', '#ea580c', '#16a34a', '#2563eb', '#7c3aed'] as const
export const EDITOR_HIGHLIGHT_COLORS = ['#ffff00', '#bbf7d0', '#bae6fd', '#fecaca', '#fed7aa', '#ddd6fe'] as const

export type EditorBlock = 'paragraph' | `heading-${1 | 2 | 3 | 4 | 5 | 6}`
export type EditorAlignment = 'left' | 'center' | 'right' | 'justify'

export function activeChoice<T extends string>(choices: readonly T[], predicate: (choice: T) => boolean): T | '' {
  const active = choices.filter(predicate)
  return active.length === 1 ? (active[0] ?? '') : ''
}

function attributeOrDefault(value: unknown, defaultValue: string): string {
  return typeof value === 'string' && value.length > 0 ? value : defaultValue
}

function selectedTextStyleAttribute(editor: Editor, attribute: string, defaultValue: string): string {
  const { selection } = editor.state
  if (selection.empty) {
    return attributeOrDefault(editor.getAttributes('textStyle')[attribute], defaultValue)
  }

  const values = new Set<string>()
  editor.state.doc.nodesBetween(selection.from, selection.to, (node) => {
    if (!node.isText || !node.text?.length) return
    const textStyle = node.marks.find((mark) => mark.type.name === 'textStyle')
    values.add(attributeOrDefault(textStyle?.attrs[attribute], defaultValue))
  })
  if (values.size === 0) {
    return attributeOrDefault(editor.getAttributes('textStyle')[attribute], defaultValue)
  }
  return values.size === 1 ? (values.values().next().value ?? defaultValue) : ''
}

export function currentFontFamily(editor: Editor): string {
  return selectedTextStyleAttribute(editor, 'fontFamily', DEFAULT_FONT_FAMILY)
}

export function currentFontSize(editor: Editor): string {
  return selectedTextStyleAttribute(editor, 'fontSize', DEFAULT_FONT_SIZE)
}

export function currentLineHeight(editor: Editor): string {
  const { selection } = editor.state
  if (selection.empty) {
    const attrs = editor.isActive('heading')
      ? editor.getAttributes('heading')
      : editor.getAttributes('paragraph')
    return attributeOrDefault(attrs.lineHeight, DEFAULT_LINE_HEIGHT)
  }

  const values = new Set<string>()
  editor.state.doc.nodesBetween(selection.from, selection.to, (node) => {
    if (node.type.name !== 'paragraph' && node.type.name !== 'heading') return
    values.add(attributeOrDefault(node.attrs.lineHeight, DEFAULT_LINE_HEIGHT))
  })
  if (values.size === 0) return DEFAULT_LINE_HEIGHT
  return values.size === 1 ? (values.values().next().value ?? DEFAULT_LINE_HEIGHT) : ''
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
