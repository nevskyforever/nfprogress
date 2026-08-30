import { createPinia } from 'pinia'
import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'

import FolderDialog from './FolderDialog.vue'

const ionicStubs = {
  IonModal: { template: '<div><slot /></div>' },
  IonHeader: { template: '<header><slot /></header>' },
  IonContent: { template: '<main><slot /></main>' },
  IonIcon: true,
}

describe('FolderDialog', () => {
  it('submits a trimmed folder name', async () => {
    const wrapper = mount(FolderDialog, {
      props: { open: true },
      global: { plugins: [createPinia()], stubs: ionicStubs },
    })

    await wrapper.get('#folder-name').setValue('  Черновики  ')
    await wrapper.get('form').trigger('submit')

    expect(wrapper.emitted('submit')?.[0]).toEqual(['Черновики'])
  })

  it('shows a validation error for an empty name', async () => {
    const wrapper = mount(FolderDialog, {
      props: { open: true },
      global: { plugins: [createPinia()], stubs: ionicStubs },
    })

    await wrapper.get('form').trigger('submit')

    expect(wrapper.emitted('submit')).toBeUndefined()
    expect(wrapper.get('[role="alert"]').text()).toContain('Введите название папки')
  })
})
