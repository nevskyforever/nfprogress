import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'

import ScrivenerItemOptions from './ScrivenerItemOptions.vue'

describe('ScrivenerItemOptions', () => {
  it('renders the recursive Binder hierarchy with stable IDs and visual indentation', () => {
    const wrapper = mount({
      components: { ScrivenerItemOptions },
      template: `
        <select>
          <ScrivenerItemOptions :items="items" />
        </select>
      `,
      data: () => ({
        items: [
          {
            id: 'draft',
            title: 'Draft',
            children: [
              { id: 'chapter', title: 'Chapter 1', children: [] },
            ],
          },
        ],
      }),
    })

    const options = wrapper.findAll('option')
    expect(options.map((option) => option.attributes('value'))).toEqual(['draft', 'chapter'])
    expect(options[1]!.text()).toContain('↳ Chapter 1')
  })
})
