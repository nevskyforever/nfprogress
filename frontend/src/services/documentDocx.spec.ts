import { describe, expect, it } from 'vitest'

import { exportDocx } from './documentDocx'

describe('documentDocx', () => {
  it('exports a Word document with Word-compatible text styling', async () => {
    const blob = await exportDocx({
      type: 'doc',
      content: [{
        type: 'paragraph',
        attrs: { textAlign: 'center', lineHeight: '1.5' },
        content: [{
          type: 'text',
          text: 'Форматированный текст',
          marks: [
            { type: 'textStyle', attrs: { fontFamily: 'Georgia', fontSize: '16pt', color: '#336699' } },
            { type: 'bold' }, { type: 'italic' }, { type: 'underline' }, { type: 'strike' },
            { type: 'subscript' }, { type: 'highlight', attrs: { color: '#ffff00' } },
          ],
        }],
      }, {
        type: 'orderedList',
        content: [{ type: 'listItem', content: [{ type: 'paragraph', content: [{ type: 'text', text: 'Пункт' }] }] }],
      }],
    })

    expect(blob.size).toBeGreaterThan(0)
  })
})
