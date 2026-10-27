// @vitest-environment jsdom
import { afterEach, describe, expect, it } from 'vitest'
import { Editor } from '@tiptap/core'
import { validatePortableDocument, validateTiptap } from '@/cloud/documentCodec'
import { createDocumentEditorExtensions } from '@/components/documents/editor/editorExtensions'

const editors: Editor[] = []
afterEach(() => { editors.splice(0).forEach(editor => editor.destroy()) })

function editor(content: Record<string, unknown>): Editor {
  const instance = new Editor({ extensions: createDocumentEditorExtensions(), content })
  editors.push(instance)
  return instance
}

describe('encrypted local document format boundary', () => {
  it('round-trips the shared WORTA Tiptap editor formatting through the existing document codec', () => {
    const original = editor({ type: 'doc', content: [
      { type: 'heading', attrs: { level: 2, textAlign: 'center', lineHeight: '1.5' }, content: [
        { type: 'text', text: 'Chapter', marks: [{ type: 'bold' }, { type: 'italic' },
          { type: 'textStyle', attrs: { color: '#123456', fontFamily: 'Arial', fontSize: '16pt' } }] },
      ] },
      { type: 'paragraph', attrs: { textAlign: 'justify', lineHeight: '2' }, content: [
        { type: 'text', text: 'A formatted paragraph', marks: [{ type: 'underline' }, { type: 'highlight', attrs: { color: '#ffff00' } }] },
      ] },
      { type: 'bulletList', content: [{ type: 'listItem', content: [{ type: 'paragraph', content: [{ type: 'text', text: 'List item' }] }] }] },
      { type: 'blockquote', content: [{ type: 'paragraph', content: [{ type: 'text', text: 'Quote' }] }] },
      { type: 'horizontalRule' },
    ] })
    const content = original.getJSON()
    expect(() => validateTiptap(content)).not.toThrow()
    validatePortableDocument({ id: 'document-id', project_id: 'project-id', stage_id: 'stage-id', title: 'Private title',
      content_json: content, content_format: 'tiptap-json/v1', created_at: '2026-10-27T00:00:00.000000Z', extensions: {} })
    expect(editor(content).getJSON()).toEqual(content)
  })

  it('accepts the initial empty editor document and rejects unsupported or oversized content', () => {
    expect(() => validateTiptap(editor({ type: 'doc', content: [{ type: 'paragraph' }] }).getJSON())).not.toThrow()
    expect(() => validateTiptap({ type: 'doc', content: [{ type: 'table' }] })).toThrow('document_unsupported_structure')
    expect(() => validateTiptap({ type: 'doc', content: [{ type: 'paragraph', content: [{ type: 'text', text: 'x'.repeat(1_100_000) }] }] })).toThrow('document_resource_limit')
  })
})
