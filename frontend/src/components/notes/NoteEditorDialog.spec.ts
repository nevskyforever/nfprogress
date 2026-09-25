import { createPinia } from 'pinia'
import { flushPromises, mount } from '@vue/test-utils'
import { defineComponent, h, ref } from 'vue'
import { describe, expect, it } from 'vitest'

import { noteFixture } from '@/test/noteFixtures'

import NoteEditorDialog from './NoteEditorDialog.vue'

let presentDeferredModal: (() => void) | undefined
let mountDeferredModalContent: (() => void) | undefined

const DeferredIonModal = defineComponent({
  name: 'IonModal',
  props: { isOpen: Boolean },
  emits: ['didPresent', 'didDismiss'],
  setup(_props, { emit, slots }) {
    const presented = ref(false)
    mountDeferredModalContent = () => {
      presented.value = true
    }
    presentDeferredModal = () => {
      emit('didPresent')
    }
    return () => h('div', presented.value ? slots.default?.() : [])
  },
})

function mountDialog(content: string) {
  return mount(NoteEditorDialog, {
    props: { open: true, note: noteFixture({ content }) },
    global: {
      plugins: [createPinia()],
      stubs: {
        IonModal: DeferredIonModal,
        IonContent: { template: '<div><slot /></div>' },
        IonHeader: { template: '<div><slot /></div>' },
        IonIcon: true,
        IonSpinner: true,
      },
    },
  })
}

describe('NoteEditorDialog', () => {
  it('hydrates existing HTML only after the Ionic modal content is presented', async () => {
    const html = '<p>Полный <strong>текст заметки</strong></p>'
    const wrapper = mountDialog(html)

    expect(wrapper.find('.note-content-editor').exists()).toBe(false)
    mountDeferredModalContent?.()
    await flushPromises()
    expect(wrapper.get('.note-content-editor').element.innerHTML).toBe('')
    expect(wrapper.get('button[type="submit"]').attributes('disabled')).toBeDefined()

    presentDeferredModal?.()
    await flushPromises()

    expect(wrapper.get('.note-content-editor').element.innerHTML).toBe(html)
    expect(wrapper.get('button[type="submit"]').attributes('disabled')).toBeUndefined()
  })

  it('does not submit before hydration and preserves content on reopen', async () => {
    const html = '<p>Содержимое после синхронизации</p>'
    const wrapper = mountDialog(html)

    mountDeferredModalContent?.()
    await flushPromises()
    await wrapper.find('form').trigger('submit')
    expect(wrapper.emitted('submit')).toBeUndefined()

    presentDeferredModal?.()
    await flushPromises()
    await wrapper.setProps({ open: false })
    await wrapper.setProps({ open: true })
    await flushPromises()

    expect(wrapper.get('.note-content-editor').element.innerHTML).toBe(html)
    await wrapper.find('form').trigger('submit')
    expect(wrapper.emitted('submit')?.[0]?.[1]).toMatchObject({ content: html })
  })

  it('reports a completed dismiss separately from a close request', async () => {
    const wrapper = mountDialog('<p>Текст</p>')
    mountDeferredModalContent?.()
    await flushPromises()
    presentDeferredModal?.()
    await flushPromises()

    wrapper.findComponent(DeferredIonModal).vm.$emit('didDismiss')
    await flushPromises()

    expect(wrapper.emitted('close')).toHaveLength(1)
    expect(wrapper.emitted('dismissed')).toHaveLength(1)
    expect(wrapper.get('button[type="submit"]').attributes('disabled')).toBeDefined()
  })
})
