import { flushPromises, mount } from '@vue/test-utils'
import { defineComponent, onMounted, type PropType } from 'vue'
import { describe, expect, it, vi } from 'vitest'

import type { DocumentScope } from '@/types/documents'
import DocumentEditor from './DocumentEditor.vue'

const mountedScopes = vi.hoisted(() => [] as DocumentScope[])

vi.mock('./DocumentEditorView.vue', () => ({
  default: defineComponent({
    props: {
      scope: { type: Object as PropType<DocumentScope>, required: true },
      title: { type: String, required: true },
    },
    setup(props) {
      onMounted(() => mountedScopes.push({ ...props.scope }))
      return () => null
    },
  }),
}))

describe('DocumentEditor', () => {
  it('recreates the editor when switching from a project document to a stage document', async () => {
    const wrapper = mount(DocumentEditor, {
      props: { scope: { projectId: 'project-id' }, title: 'Текст проекта' },
    })
    await flushPromises()

    await wrapper.setProps({
      scope: { projectId: 'project-id', stageId: 'stage-id' },
      title: 'Текст этапа',
    })
    await flushPromises()

    expect(mountedScopes).toEqual([
      { projectId: 'project-id' },
      { projectId: 'project-id', stageId: 'stage-id' },
    ])
  })
})
