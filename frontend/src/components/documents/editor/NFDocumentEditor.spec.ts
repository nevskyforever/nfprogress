import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import type { Editor } from '@tiptap/core'
import type { TiptapDocument } from '@/types/documents'
import NFDocumentEditor from './NFDocumentEditor.vue'

const formattedDocument: TiptapDocument = {
  type: 'doc',
  content: [{
    type: 'paragraph',
    attrs: { textAlign: 'center', lineHeight: '1.5' },
    content: [{
      type: 'text',
      text: 'Существующий текст',
      marks: [
        { type: 'bold' },
        { type: 'textStyle', attrs: { fontFamily: 'Georgia', fontSize: '18pt', color: '#336699' } },
      ],
    }],
  }],
}

type EditorExpose = {
  getEditor: () => Editor | null
  getJSON: () => TiptapDocument
  getScrollContainer: () => HTMLElement | null
  setContent: (content: TiptapDocument, emitUpdate?: boolean) => void
}

describe('NFDocumentEditor core', () => {
  it('loads existing Tiptap JSON without changing its supported schema', () => {
    const wrapper = mount(NFDocumentEditor, { props: { content: formattedDocument } })
    const api = wrapper.vm as unknown as EditorExpose

    const json = api.getJSON()
    const paragraph = json.content?.[0] as { attrs?: Record<string, unknown>; content?: Array<{ marks?: Array<{ type?: string; attrs?: Record<string, unknown> }> }> }
    expect(paragraph.attrs).toMatchObject({ textAlign: 'center', lineHeight: '1.5' })
    expect(paragraph.content?.[0]?.marks).toEqual(expect.arrayContaining([
      expect.objectContaining({ type: 'bold' }),
      expect.objectContaining({ type: 'textStyle', attrs: expect.objectContaining({ fontFamily: 'Georgia', fontSize: '18pt', color: '#336699' }) }),
    ]))
    expect(api.getScrollContainer()).toBe(wrapper.get('.nf-document-editor__viewport').element)
  })

  it('emits the current JSON when the document changes', () => {
    const wrapper = mount(NFDocumentEditor, { props: { content: { type: 'doc', content: [{ type: 'paragraph' }] } } })
    const api = wrapper.vm as unknown as EditorExpose
    const next: TiptapDocument = { type: 'doc', content: [{ type: 'paragraph', content: [{ type: 'text', text: 'Новый текст' }] }] }

    api.setContent(next, true)

    expect(wrapper.emitted('update')?.at(-1)?.[0]).toMatchObject(next)
  })

  it('reflects the selection in the toolbar and applies formatting commands', async () => {
    const wrapper = mount(NFDocumentEditor, { props: { content: formattedDocument } })
    const api = wrapper.vm as unknown as EditorExpose
    const editor = api.getEditor()
    expect(editor).not.toBeNull()

    editor!.commands.setTextSelection({ from: 1, to: 5 })
    await wrapper.vm.$nextTick()

    expect((wrapper.find('select[aria-label="Шрифт"]').element as HTMLSelectElement).value).toBe('Georgia')
    expect((wrapper.find('select[aria-label="Размер текста"]').element as HTMLSelectElement).value).toBe('18pt')
    expect(wrapper.find('button[aria-label="Полужирный"]').attributes('aria-pressed')).toBe('true')

    await wrapper.find('button[aria-label="Курсив"]').trigger('click')
    await wrapper.find('select[aria-label="Межстрочный интервал"]').setValue('2')
    await wrapper.find('button[aria-label="По правому краю"]').trigger('click')

    const json = api.getJSON()
    const paragraph = json.content?.[0] as { attrs?: Record<string, unknown>; content?: Array<{ marks?: Array<{ type?: string }> }> }
    expect(paragraph.attrs).toMatchObject({ textAlign: 'right', lineHeight: '2' })
    expect(paragraph.content?.[0]?.marks).toEqual(expect.arrayContaining([expect.objectContaining({ type: 'italic' })]))
  })
})
