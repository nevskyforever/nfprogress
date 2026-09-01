import { createPinia } from 'pinia'
import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { gameApi } from '@/api/game'
import { settingsApi } from '@/api/settings'
import { useNotificationsStore } from '@/stores/notifications'
import { gameStateFixture } from '@/test/gameFixtures'
import type { SettingsResponse } from '@/types/content'

import GamePage from './GamePage.vue'

vi.mock('@/api/game', () => ({
  gameApi: {
    state: vi.fn(),
    applyStreakFreeze: vi.fn(),
  },
}))

vi.mock('@/api/settings', () => ({
  settingsApi: {
    get: vi.fn(),
    update: vi.fn(),
  },
}))

const settingsFixture: SettingsResponse = {
  values: { inventory_filter: 'Зелья' },
  platform: 'web',
  capabilities: {
    local_file_sync: false,
    background_file_sync: false,
    native_updates: false,
    remote_api: true,
  },
  editable_keys: ['inventory_filter'],
}

describe('GamePage', () => {
  beforeEach(() => {
    vi.mocked(gameApi.state).mockReset()
    vi.mocked(gameApi.applyStreakFreeze).mockReset()
    vi.mocked(settingsApi.get).mockReset()
    vi.mocked(settingsApi.update).mockReset()
    vi.mocked(gameApi.state).mockResolvedValue(gameStateFixture())
    vi.mocked(settingsApi.get).mockResolvedValue(settingsFixture)
    vi.mocked(gameApi.applyStreakFreeze).mockResolvedValue({
      ok: true,
      message: 'Заморозка применена.',
      messages: ['Заморозка применена.'],
      result: null,
      state: gameStateFixture({
        streak_freezes: {
          ...gameStateFixture().streak_freezes,
          inventory_count: 1,
          global_available: false,
        },
      }),
    })
  })

  it('loads real state and applies an authoritative command response without a redundant reload', async () => {
    const pinia = createPinia()
    vi.mocked(gameApi.state).mockResolvedValue(gameStateFixture({
      notifications: {
        unread: [{
          id: 'streak-event',
          text: 'Стрик сохранён.',
          tag: 'streak',
          created_at: '2026-08-15T12:00:00',
          status: 'new',
        }],
        read: [],
        unread_count: 1,
      },
    }))
    const wrapper = mount(GamePage, {
      global: {
        plugins: [pinia],
        stubs: { IonIcon: true },
      },
    })
    await flushPromises()

    expect(gameApi.state).toHaveBeenCalledTimes(1)
    expect(settingsApi.get).toHaveBeenCalledTimes(1)
    expect(useNotificationsStore(pinia).gameHistory.unread_count).toBe(1)
    expect(wrapper.text()).toContain('Игровой режим')
    expect(wrapper.text()).toContain('Дом у моря')

    const freezeButton = wrapper
      .findAll('button')
      .find((button) => button.text().includes('Применить заморозку'))
    expect(freezeButton).toBeDefined()
    await freezeButton?.trigger('click')
    await flushPromises()

    expect(gameApi.applyStreakFreeze).toHaveBeenCalledWith('global', undefined)
    expect(gameApi.state).toHaveBeenCalledTimes(1)
    expect(useNotificationsStore(pinia).notifications.at(-1)?.message)
      .toBe('Заморозка применена.')
  })

  it('shows every message returned by a game command', async () => {
    vi.mocked(gameApi.applyStreakFreeze).mockResolvedValue({
      ok: true,
      message: 'Первое событие.',
      messages: ['Первое событие.', 'Второе событие.'],
      result: null,
      state: gameStateFixture(),
    })
    const pinia = createPinia()
    const wrapper = mount(GamePage, {
      global: { plugins: [pinia], stubs: { IonIcon: true } },
    })
    await flushPromises()

    const freezeButton = wrapper
      .findAll('button')
      .find((button) => button.text().includes('Применить заморозку'))
    await freezeButton?.trigger('click')
    await flushPromises()

    const messages = useNotificationsStore(pinia).notifications.map(({ message }) => message)
    expect(messages).toEqual(expect.arrayContaining(['Первое событие.', 'Второе событие.']))
    wrapper.unmount()
  })

  it('shows active bank products beside coins instead of inflation', async () => {
    vi.mocked(gameApi.state).mockResolvedValue(gameStateFixture({
      bank: {
        ...gameStateFixture().bank,
        credit: {
          principal: 500,
          interest_rate: 3,
          interest: 15,
          total: 515,
          remaining: 400,
          daily_payment: 50,
          status: 'Активен',
          opened_at: null,
          return_date: null,
          paid_amount: 115,
          overdue_days: 0,
        },
        deposit: {
          principal: 700,
          interest_rate: 2,
          interest: 14,
          total: 714,
          available_interest: 14,
          allow_interest_withdrawal: true,
          status: 'Активен',
          opened_at: null,
          return_date: null,
        },
      },
    }))
    const wrapper = mount(GamePage, {
      global: { plugins: [createPinia()], stubs: { IonIcon: true } },
    })
    await flushPromises()

    const overview = wrapper.get('.overview')
    expect(overview.text()).toContain('Кредит: 400')
    expect(overview.text()).toContain('Вклад: 714')
    expect(overview.text()).not.toContain('Инфляция')
    wrapper.unmount()
  })

  it('summarizes stacked buffs and keeps the detailed lists scrollable', async () => {
    vi.mocked(gameApi.state).mockResolvedValue(gameStateFixture({
      buffs: {
        server_time: '2026-08-15T12:00:00',
        positive: [
          {
            name: 'Бонус опыта',
            description: 'Бонус',
            type: 'positive',
            target: 'exp',
            value: 0.02,
            stacks: 2,
            duration_minutes: null,
            started_at: null,
            expires_at: null,
            remaining_seconds: null,
            source: null,
            stackable: true,
          },
        ],
        negative: [
          {
            name: 'Штраф опыта',
            description: 'Штраф',
            type: 'negative',
            target: 'exp',
            value: 0.01,
            stacks: 3,
            duration_minutes: null,
            started_at: null,
            expires_at: null,
            remaining_seconds: null,
            source: null,
            stackable: true,
          },
        ],
      },
    }))
    const wrapper = mount(GamePage, {
      global: { plugins: [createPinia()], stubs: { IonIcon: true } },
    })
    await flushPromises()

    expect(wrapper.findAll('.buff-summary-card')).toHaveLength(2)
    expect(wrapper.get('.buff-summary-card--positive').text()).toContain('+0.04')
    expect(wrapper.get('.buff-summary-card--negative').text()).toContain('−0.03')
    expect(wrapper.findAll('.buff-panel .buff-list')).toHaveLength(2)
    wrapper.unmount()
  })

  it('opens purchase confirmation for an item bought from the inventory', async () => {
    vi.mocked(gameApi.state).mockResolvedValue(gameStateFixture({
      inventory: {
        categories: [{
          key: 'Зелья',
          name: 'Зелья',
          items: [{
            id: 'Зелья:Зелье воскрешения',
            key: 'Зелье воскрешения',
            category: 'Зелья',
            name: 'Зелье воскрешения',
            description: 'Полностью восстанавливает здоровье',
            price: 100,
            count: 1,
            sellable: true,
            usable: true,
            buy: true,
            can_buy: true,
          }],
        }],
      },
    }))
    const wrapper = mount(GamePage, {
      global: {
        plugins: [createPinia()],
        stubs: {
          IonIcon: true,
          PurchaseConfirmDialog: {
            props: ['item', 'count'],
            template: '<div v-if="item" class="purchase-confirm-stub">{{ item.name }} ×{{ count }}</div>',
          },
        },
      },
    })
    await flushPromises()

    const inventoryTab = wrapper.findAll('[role="tab"]')
      .find((button) => button.text() === 'Инвентарь')
    await inventoryTab?.trigger('click')

    const buyButton = wrapper.findAll('.item-card button')
      .find((button) => button.text() === 'Купить')
    await buyButton?.trigger('click')

    expect(wrapper.get('.purchase-confirm-stub').text())
      .toContain('Зелье воскрешения ×1')
    wrapper.unmount()
  })
})
