import { createPinia } from 'pinia'
import { flushPromises, mount } from '@vue/test-utils'
import { defineComponent, h, ref } from 'vue'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { noteFixture } from '@/test/noteFixtures'

import NoteEditorDialog from './NoteEditorDialog.vue'

afterEach(() => vi.useRealTimers())

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

function mountDialog(content: string, contentFormat:'html'|'plain'='html') {
  return mount(NoteEditorDialog, {
    props: { open: true, note: noteFixture({ content,content_format:contentFormat }) },
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
  it('preserves plain text markup literally during hydration',async()=>{
    const text='<b>literal text</b>'
    const wrapper=mountDialog(text,'plain')
    mountDeferredModalContent?.();await flushPromises();presentDeferredModal?.()
    await flushPromises()
    expect(wrapper.get('.note-content-editor').element.textContent).toBe(text)
    expect(wrapper.find('.note-content-editor b').exists()).toBe(false)
    wrapper.unmount()
  })
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

  it('debounces encrypted-workspace autosave and emits the full note patch', async () => {
    vi.useFakeTimers()
    const wrapper = mount(NoteEditorDialog, {
      props: { open: true, note: noteFixture(), autosave: true },
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
    mountDeferredModalContent?.()
    await flushPromises()
    presentDeferredModal?.()
    await flushPromises()
    await wrapper.get('input[name="title"]').setValue('Autosaved title')
    const editor = wrapper.get('.note-content-editor')
    editor.element.innerHTML = '<p>Autosaved body</p>'
    await editor.trigger('input')
    await flushPromises()
    expect(wrapper.emitted('autosave')).toBeUndefined()
    await vi.advanceTimersByTimeAsync(700)
    await flushPromises()
    expect(wrapper.emitted('autosave')?.[0]).toEqual([
      'note-id',
      expect.objectContaining({ title: 'Autosaved title', content: '<p>Autosaved body</p>' }),
    ])
    expect(wrapper.emitted('autosaveStatus')?.map(([status]) => status)).toEqual(['pending', 'pending', 'saving'])
    wrapper.unmount()
  })

  it('keeps failed autosave edits open and retries before closing', async () => {
    vi.useFakeTimers()
    const wrapper = mount(NoteEditorDialog, {
      props: { open: true, note: noteFixture(), autosave: true },
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
    mountDeferredModalContent?.()
    await flushPromises()
    presentDeferredModal?.()
    await flushPromises()
    await wrapper.get('input[name="title"]').setValue('Retry this title')
    await vi.advanceTimersByTimeAsync(700)
    await flushPromises()
    expect(wrapper.emitted('autosave')).toHaveLength(1)

    await wrapper.setProps({ autosaveStatus: 'error' })
    expect(wrapper.get('.note-form__autosave').text()).toBe('Не удалось сохранить изменения.')
    await wrapper.get('button[aria-label="Закрыть"]').trigger('click')
    expect(wrapper.emitted('autosave')).toHaveLength(2)
    expect(wrapper.emitted('close')).toBeUndefined()
    wrapper.unmount()
  })
})
