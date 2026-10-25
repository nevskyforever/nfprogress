import { createPinia } from 'pinia'
import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, expect, it, vi } from 'vitest'
import { useLocaleStore } from '@/stores/locale'
import { CryptoError } from '@/crypto'

const fixture = vi.hoisted(() => ({
  status: 'logged_out' as 'logged_out' | 'authenticated' | 'unlocked' | 'locked',
  username: null as string | null,
  login: vi.fn(), unlock: vi.fn(), lock: vi.fn(), logout: vi.fn(), dispose: vi.fn(),
}))

vi.mock('@/platform/web/cloudAccountSession', () => ({
  BrowserCloudAccountSession: class {
    get status() { return fixture.status }
    get username() { return fixture.username }
    async login(username: string, password: string) {
      fixture.login(username, password)
      fixture.username = username
      fixture.status = 'authenticated'
    }
    async unlock(password: string) {
      fixture.unlock(password)
      if (password === 'wrong') throw new CryptoError('decrypt_failed')
      fixture.status = 'unlocked'
    }
    async lock() { fixture.lock(); fixture.status = 'locked' }
    async logout() { fixture.logout(); fixture.status = 'logged_out'; fixture.username = null }
    async dispose() { fixture.dispose() }
  },
}))

import BrowserCloudAccountCard from './BrowserCloudAccountCard.vue'

beforeEach(() => {
  fixture.status = 'logged_out'
  fixture.username = null
  for (const name of ['login', 'unlock', 'lock', 'logout', 'dispose'] as const) fixture[name].mockClear()
})

it('shows the bounded Web account, unlock, lock and logout flow without Note actions', async () => {
  const pinia = createPinia()
  useLocaleStore(pinia).language = 'ru'
  const wrapper = mount(BrowserCloudAccountCard, { global: { plugins: [pinia] } })
  expect(wrapper.text()).toContain('Синхронизация отключена')
  expect(wrapper.get('[data-status]').attributes('data-status')).toBe('logged_out')
  await wrapper.get('input[autocomplete="username"]').setValue('one')
  await wrapper.get('input[autocomplete="current-password"]').setValue('account-pass')
  await wrapper.get('form').trigger('submit')
  await flushPromises()
  expect(fixture.login).toHaveBeenCalledWith('one', 'account-pass')
  expect(wrapper.get('[data-status]').attributes('data-status')).toBe('authenticated')
  await wrapper.get('input[autocomplete="off"]').setValue('wrong')
  await wrapper.get('form').trigger('submit')
  await flushPromises()
  expect(wrapper.get('[role="alert"]').text()).toContain('Проверьте пароль шифрования')
  expect(wrapper.get('[data-status]').attributes('data-status')).toBe('authenticated')
  await wrapper.get('input[autocomplete="off"]').setValue('correct')
  await wrapper.get('form').trigger('submit')
  await flushPromises()
  expect(wrapper.get('[data-status]').attributes('data-status')).toBe('unlocked')
  expect(wrapper.text()).toContain('Ключ шифрования разблокирован')
  expect(wrapper.find('button[data-note-action]').exists()).toBe(false)
  await wrapper.findAll('button')[0]!.trigger('click')
  await flushPromises()
  expect(fixture.lock).toHaveBeenCalledOnce()
  expect(wrapper.get('[data-status]').attributes('data-status')).toBe('locked')
  await wrapper.findAll('button')[1]!.trigger('click')
  await flushPromises()
  expect(fixture.logout).toHaveBeenCalledOnce()
  expect(wrapper.get('[data-status]').attributes('data-status')).toBe('logged_out')
  wrapper.unmount()
  expect(fixture.dispose).toHaveBeenCalledOnce()
})
