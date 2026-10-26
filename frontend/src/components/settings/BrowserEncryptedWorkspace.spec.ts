import { createPinia } from 'pinia'
import { flushPromises, mount } from '@vue/test-utils'
import { describe, expect, it, vi } from 'vitest'

import { BrowserPersistenceError } from '@/platform/web/persistence'
import type { BrowserCloudAccountSession } from '@/platform/web/cloudAccountSession'
import BrowserEncryptedWorkspace from './BrowserEncryptedWorkspace.vue'

const scope = {
  canonicalUserId: '11111111-1111-4111-8111-111111111111',
  accountId: '22222222-2222-4222-8222-222222222222',
  deviceId: '33333333-3333-4333-8333-333333333333',
}

function sessionFixture(options: { locked?: boolean } = {}) {
  let project: Record<string, unknown> | null = null
  const source = {
    createProject: vi.fn(async (_scope: unknown, input: Record<string, unknown>) => { project = structuredClone(input); return 1 }),
    listProjects: vi.fn(async () => project ? [structuredClone(project)] : []),
    readSnapshot: vi.fn(async (_scope: unknown, projectId: string) => {
      if (!project) throw new BrowserPersistenceError('missing_local_source')
      if (project.id !== projectId) throw new BrowserPersistenceError('account_mismatch')
      return { token: {} }
    }),
    withDecryptedSnapshot: vi.fn(async (_scope: unknown, _token: unknown, consume: (data: unknown) => unknown) =>
      consume({ project: structuredClone(project), notes: [], source_revision: 1 })),
  }
  const stages = { list: vi.fn(async () => []), create: vi.fn(), rename: vi.fn(), remove: vi.fn(), reorder: vi.fn() }
  return {
    source,
    session: {
      localNoteRepository: () => {
        if (options.locked) throw new BrowserPersistenceError('closed')
        return { scope, source, stages }
      },
    } as unknown as BrowserCloudAccountSession,
  }
}

function mountWorkspace(session: BrowserCloudAccountSession) {
  return mount(BrowserEncryptedWorkspace, {
    props: { session },
    global: { plugins: [createPinia()], stubs: { IonIcon: true, NoteCard: true, NoteEditorDialog: true } },
  })
}

describe('BrowserEncryptedWorkspace', () => {
  it('creates only its separate C21 local project and reloads it from the encrypted source', async () => {
    const fixture = sessionFixture()
    const wrapper = mountWorkspace(fixture.session)
    await flushPromises()
    await wrapper.get('input[maxlength="200"]').setValue('Local test project')
    await wrapper.get('form').trigger('submit')
    await flushPromises()
    expect(fixture.source.createProject).toHaveBeenCalledWith(scope, expect.objectContaining({
      id: expect.any(String),
      name: 'Local test project',
      payload: {},
    }))
    expect(wrapper.get('.encrypted-workspace__projects').text()).toBe('Local test project')
    expect(wrapper.get('[data-testid="encrypted-local-workspace"]').text()).toContain('Не синхронизируется')
    wrapper.unmount()
  })

  it('fails closed while locked and never enables a legacy repository fallback', async () => {
    const fixture = sessionFixture({ locked: true })
    const wrapper = mountWorkspace(fixture.session)
    await flushPromises()
    expect(wrapper.get('[role="alert"]').text()).toContain('Хранилище заблокировано')
    expect(wrapper.find('button[type="submit"]').exists()).toBe(false)
    expect(wrapper.text()).not.toContain('Новая заметка')
    expect(fixture.source.createProject).not.toHaveBeenCalled()
    wrapper.unmount()
  })
})
