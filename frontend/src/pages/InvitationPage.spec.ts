import { createPinia } from 'pinia'
import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, expect, it, vi } from 'vitest'
import { nextTick } from 'vue'
import { useLocaleStore } from '@/stores/locale'

const accept = vi.hoisted(() => vi.fn())
vi.mock('@/api/invitations', () => ({ invitationApi: { accept } }))
import InvitationPage from './InvitationPage.vue'

beforeEach(() => {
  accept.mockReset().mockResolvedValue({ code: 'invitation_accepted', username: 'Writer' })
  window.history.replaceState({}, '', '/invite#token=iv1.synthetic.secret')
})

it('clears the fragment and password fields before accepting a private invitation', async () => {
  const pinia = createPinia()
  useLocaleStore(pinia).language = 'ru'
  const wrapper = mount(InvitationPage, { global: { plugins: [pinia] } })
  await nextTick()
  expect(window.location.hash).toBe('')
  const inputs = wrapper.findAll('input[type="password"]')
  await inputs[0]!.setValue('synthetic long password')
  await inputs[1]!.setValue('synthetic long password')
  await wrapper.get('form').trigger('submit')
  expect((inputs[0]!.element as HTMLInputElement).value).toBe('')
  expect((inputs[1]!.element as HTMLInputElement).value).toBe('')
  await flushPromises()
  expect(accept).toHaveBeenCalledWith('iv1.synthetic.secret', 'synthetic long password')
  expect(wrapper.text()).toContain('Аккаунт готов')
  expect(wrapper.find('form').exists()).toBe(false)
  wrapper.unmount()
})

it('refuses a missing invitation token', async () => {
  window.history.replaceState({}, '', '/invite')
  const wrapper = mount(InvitationPage, { global: { plugins: [createPinia()] } })
  await nextTick()
  expect(wrapper.find('form').exists()).toBe(false)
  expect(wrapper.find('[role="alert"]').exists()).toBe(true)
  expect(accept).not.toHaveBeenCalled()
  wrapper.unmount()
})
