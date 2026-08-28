import { createPinia } from 'pinia'
import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { integrationsApi } from '@/api/integrations'
import { projectFixture } from '@/test/fixtures'

import WordUploadCard from './WordUploadCard.vue'

vi.mock('@/api/integrations', () => ({
  integrationsApi: {
    countWord: vi.fn(),
    importWord: vi.fn(),
  },
}))

describe('WordUploadCard', () => {
  beforeEach(() => {
    vi.mocked(integrationsApi.countWord).mockReset()
    vi.mocked(integrationsApi.importWord).mockReset()
  })

  it('counts only the explicitly selected docx through the real API boundary', async () => {
    vi.mocked(integrationsApi.countWord).mockResolvedValue({ symbols: 12_345 })
    const wrapper = mount(WordUploadCard, {
      global: {
        plugins: [createPinia()],
        stubs: { IonIcon: true, IonSpinner: true },
      },
    })
    const input = wrapper.get('input[type="file"]')
    const file = new File(['payload'], 'chapter.docx')
    Object.defineProperty(input.element, 'files', { configurable: true, value: [file] })

    await input.trigger('change')
    await flushPromises()

    expect(integrationsApi.countWord).toHaveBeenCalledWith(file)
    expect(wrapper.get('[role="status"]').text().replace(/\D/g, '')).toBe('12345')
  })

  it('rejects non-docx selections before upload', async () => {
    const wrapper = mount(WordUploadCard, {
      global: {
        plugins: [createPinia()],
        stubs: { IonIcon: true, IonSpinner: true },
      },
    })
    const input = wrapper.get('input[type="file"]')
    Object.defineProperty(input.element, 'files', {
      configurable: true,
      value: [new File(['payload'], 'chapter.txt')],
    })

    await input.trigger('change')

    expect(integrationsApi.countWord).not.toHaveBeenCalled()
    expect(wrapper.get('[role="alert"]').text()).toContain('.docx')
  })

  it('routes an import to the selected project through the authoritative endpoint', async () => {
    const project = projectFixture()
    const updated = projectFixture({ total: 12_345, progress: 24.69 })
    vi.mocked(integrationsApi.importWord).mockResolvedValue({
      changed: true,
      symbols: 12_345,
      project: updated,
      progress: null,
    })
    const wrapper = mount(WordUploadCard, {
      props: { projects: [project] },
      global: {
        plugins: [createPinia()],
        stubs: { IonIcon: true, IonSpinner: true },
      },
    })
    await wrapper.get('#word-import-project').setValue(project.id)
    await wrapper.get('.nf-button:not(.nf-button--secondary)').trigger('click')
    const input = wrapper.get('input[type="file"]')
    const file = new File(['payload'], 'chapter.docx')
    Object.defineProperty(input.element, 'files', { configurable: true, value: [file] })

    await input.trigger('change')
    await flushPromises()

    expect(integrationsApi.importWord).toHaveBeenCalledWith(project.id, file, null)
    expect(wrapper.emitted('imported')?.[0]?.[0]).toEqual(expect.objectContaining({
      project: updated,
      changed: true,
      symbols: 12_345,
      progress: null,
    }))
    expect(wrapper.emitted('imported')?.[0]?.[1]).toBeNull()
    expect(wrapper.get('[role="status"]').text()).toContain('Прогресс проекта обновлён')
  })
})
