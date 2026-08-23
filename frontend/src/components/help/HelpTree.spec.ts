import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'

import HelpTree from './HelpTree.vue'

describe('HelpTree', () => {
  it('keeps canonical keys while selecting a localized nested article', async () => {
    const child = {
      key: 'project-create',
      title: 'Create a project',
      content: '<html><body><p>Guide</p></body></html>',
      children: [],
    }
    const wrapper = mount(HelpTree, {
      props: {
        sections: [
          {
            key: 'projects',
            title: 'Projects',
            content: '<html><body><p>Overview</p></body></html>',
            children: [child],
          },
        ],
        selectedKey: 'projects',
      },
    })

    expect(wrapper.get('button[aria-current="page"]').text()).toBe('Projects')
    await wrapper.findAll('button')[1]!.trigger('click')
    expect(wrapper.emitted('select')?.[0]?.[0]).toEqual(child)
  })
})
