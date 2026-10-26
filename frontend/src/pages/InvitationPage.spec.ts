import { createPinia } from 'pinia'
import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, expect, it, vi } from 'vitest'
import { nextTick } from 'vue'
import { ApiError } from '@/api/client'
import { useLocaleStore } from '@/stores/locale'

const api = vi.hoisted(() => ({ documents: vi.fn(), accept: vi.fn() }))
vi.mock('@/api/invitations', () => ({ invitationApi: api }))
import InvitationPage from './InvitationPage.vue'

function document(id: string, title: string, content: string, revision = '1') {
  return {
    document_id: id,
    document_type: id.includes('beta') ? 'beta_terms' : 'privacy_policy',
    revision,
    content_checksum: revision.repeat(64).slice(0, 64),
    language: 'ru',
    title,
    content,
    mandatory: true,
    requires_explicit_acceptance: true,
    accepted: false,
  }
}

const current = {
  documents: [
    document('wotra.beta_terms', 'Закрытое тестирование WORTA', 'Возможны ошибки, проблемы с синхронизацией, повреждение или потеря данных.'),
    document('wotra.privacy_policy', 'Политика конфиденциальности', 'Проверяемый текст политики.'),
  ],
  missing_required_document_ids: ['wotra.beta_terms', 'wotra.privacy_policy'],
}

function ruPinia() {
  const pinia = createPinia()
  useLocaleStore(pinia).language = 'ru'
  return pinia
}

beforeEach(() => {
  api.documents.mockReset().mockResolvedValue(current)
  api.accept.mockReset().mockResolvedValue({ code: 'invitation_accepted', username: 'Writer' })
  Object.defineProperty(window, 'localStorage', {
    configurable: true,
    value: { getItem: vi.fn(), setItem: vi.fn(), removeItem: vi.fn(), clear: vi.fn() },
  })
  window.history.replaceState({}, '', '/invite#token=iv1.synthetic.secret')
})

it('shows every required document before activation and keeps the token out of storage', async () => {
  const pinia = ruPinia()
  const setItem = vi.spyOn(window.localStorage, 'setItem')
  const wrapper = mount(InvitationPage, { global: { plugins: [pinia] } })
  await flushPromises()
  expect(window.location.hash).toBe('')
  expect(api.documents).toHaveBeenCalledWith('iv1.synthetic.secret', 'ru')
  expect(wrapper.text()).toContain('Закрытое тестирование WORTA')
  expect(wrapper.text()).toContain('повреждение или потеря данных')
  expect(wrapper.text()).toContain('Политика конфиденциальности')
  const checkboxes = wrapper.findAll('input[type="checkbox"]')
  expect(checkboxes).toHaveLength(2)
  expect(wrapper.get('button[type="submit"]').attributes('disabled')).toBeDefined()
  await checkboxes[0]!.setValue(true)
  expect(wrapper.get('button[type="submit"]').attributes('disabled')).toBeDefined()
  await checkboxes[1]!.setValue(true)
  expect(wrapper.get('button[type="submit"]').attributes('disabled')).toBeUndefined()
  expect(setItem).not.toHaveBeenCalled()
  setItem.mockRestore()
  wrapper.unmount()
})

it('clears password fields and sends exact server versions only after confirmations', async () => {
  const pinia = ruPinia()
  const wrapper = mount(InvitationPage, { global: { plugins: [pinia] } })
  await flushPromises()
  for (const checkbox of wrapper.findAll('input[type="checkbox"]')) await checkbox.setValue(true)
  const inputs = wrapper.findAll('input[type="password"]')
  await inputs[0]!.setValue('synthetic long password')
  await inputs[1]!.setValue('synthetic long password')
  await wrapper.get('form').trigger('submit')
  expect((inputs[0]!.element as HTMLInputElement).value).toBe('')
  expect((inputs[1]!.element as HTMLInputElement).value).toBe('')
  await flushPromises()
  expect(api.accept).toHaveBeenCalledWith(
    'iv1.synthetic.secret', 'synthetic long password', 'ru',
    current.documents.map(({ document_id, revision, content_checksum, language }) => ({
      document_id, revision, content_checksum, language,
    })),
  )
  expect(wrapper.text()).toContain('Аккаунт готов')
  expect(wrapper.find('form').exists()).toBe(false)
  wrapper.unmount()
})

it('reloads a changed revision and requires a new confirmation', async () => {
  const changed = {
    documents: [document('wotra.beta_terms', 'Закрытое тестирование WORTA', 'Новый текст.', '2')],
    missing_required_document_ids: ['wotra.beta_terms'],
  }
  api.accept.mockRejectedValueOnce(new ApiError(409, 'legal_document_version_changed', 'changed'))
  api.documents.mockResolvedValueOnce(current).mockResolvedValueOnce(changed)
  const wrapper = mount(InvitationPage, { global: { plugins: [ruPinia()] } })
  await flushPromises()
  for (const checkbox of wrapper.findAll('input[type="checkbox"]')) await checkbox.setValue(true)
  const inputs = wrapper.findAll('input[type="password"]')
  await inputs[0]!.setValue('synthetic long password')
  await inputs[1]!.setValue('synthetic long password')
  await wrapper.get('form').trigger('submit')
  await flushPromises()
  expect(api.documents).toHaveBeenCalledTimes(2)
  expect(wrapper.text()).toContain('Новый текст')
  expect(wrapper.text()).toContain('подтвердите его заново')
  expect((wrapper.get('input[type="checkbox"]').element as HTMLInputElement).checked).toBe(false)
  expect(wrapper.get('button[type="submit"]').attributes('disabled')).toBeDefined()
  wrapper.unmount()
})

it('keeps an in-memory invitation available for retry after a network failure', async () => {
  api.accept.mockRejectedValueOnce(new ApiError(0, 'network_error', 'offline'))
    .mockResolvedValueOnce({ code: 'invitation_accepted', username: 'Writer' })
  const wrapper = mount(InvitationPage, { global: { plugins: [ruPinia()] } })
  await flushPromises()
  for (const checkbox of wrapper.findAll('input[type="checkbox"]')) await checkbox.setValue(true)
  let inputs = wrapper.findAll('input[type="password"]')
  await inputs[0]!.setValue('synthetic long password')
  await inputs[1]!.setValue('synthetic long password')
  await wrapper.get('form').trigger('submit')
  await flushPromises()
  expect(wrapper.get('[role="alert"]').text()).toContain('Данные не изменены')
  inputs = wrapper.findAll('input[type="password"]')
  await inputs[0]!.setValue('synthetic long password')
  await inputs[1]!.setValue('synthetic long password')
  await wrapper.get('form').trigger('submit')
  await flushPromises()
  expect(api.accept).toHaveBeenCalledTimes(2)
  expect(wrapper.text()).toContain('Аккаунт готов')
  wrapper.unmount()
})

it('refuses a missing invitation token', async () => {
  window.history.replaceState({}, '', '/invite')
  const wrapper = mount(InvitationPage, { global: { plugins: [ruPinia()] } })
  await nextTick()
  expect(wrapper.find('form').exists()).toBe(false)
  expect(wrapper.find('[role="alert"]').exists()).toBe(true)
  expect(api.documents).not.toHaveBeenCalled()
  expect(api.accept).not.toHaveBeenCalled()
  wrapper.unmount()
})
