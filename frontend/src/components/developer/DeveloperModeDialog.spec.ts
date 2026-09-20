import { createPinia } from 'pinia'
import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { gameApi } from '@/api/game'
import { gameStateFixture } from '@/test/gameFixtures'
import DeveloperModeDialog from './DeveloperModeDialog.vue'

vi.mock('@/api/game', () => ({
  gameApi: {
    developerState: vi.fn(),
    developerStreakState: vi.fn(),
    requestProfileTransfer: vi.fn(),
    takeProfileTransferResult: vi.fn(),
  },
}))

vi.mock('@/platform/runtime', () => ({
  currentPlatform: () => 'tauri',
}))

describe('DeveloperModeDialog test data controls', () => {
  beforeEach(() => {
    vi.mocked(gameApi.developerState).mockResolvedValue({
      state: gameStateFixture(),
      test_date_enabled: false,
      test_datetime: null,
    })
    vi.mocked(gameApi.developerStreakState).mockResolvedValue({
      logical_day: '2026-09-19',
      targets: [{
        id: 'global', type: 'global', name: 'Глобальный', status: 'Active',
        length: 149, max_length: 149, last_effective_day: '2026-09-18',
      }],
    })
    vi.mocked(gameApi.requestProfileTransfer).mockReset()
    vi.mocked(gameApi.takeProfileTransferResult).mockReset()
    vi.mocked(gameApi.takeProfileTransferResult).mockResolvedValue(null)
    vi.mocked(gameApi.requestProfileTransfer).mockResolvedValue({
      message: 'Запрос сохранён. Перезапустите приложение.',
      restart_required: true,
    })
  })

  function mountDialog() {
    return mount(DeveloperModeDialog, {
      props: { open: true },
      global: {
        plugins: [createPinia()],
        stubs: {
          IonContent: { template: '<div><slot /></div>' },
          IonHeader: { template: '<header><slot /></header>' },
          IonIcon: true,
          IonModal: { template: '<div><slot /></div>' },
          IonSpinner: true,
        },
      },
    })
  }

  it('requires explicit confirmation before scheduling real to test refresh', async () => {
    const confirmation = vi.spyOn(window, 'confirm').mockReturnValue(false)
    const wrapper = mountDialog()
    await flushPromises()
    const refresh = wrapper.findAll('button')
      .find((button) => button.text().includes('Обновить тестовые данные из реальных'))

    await refresh?.trigger('click')
    expect(confirmation).toHaveBeenCalledOnce()
    expect(gameApi.requestProfileTransfer).not.toHaveBeenCalled()

    confirmation.mockReturnValue(true)
    await refresh?.trigger('click')
    await flushPromises()
    expect(gameApi.requestProfileTransfer).toHaveBeenCalledWith('real_to_test')
    expect(wrapper.text()).toContain('Перезапустите приложение')
  })

  it('uses a separate danger confirmation for test to real replacement', async () => {
    const confirmation = vi.spyOn(window, 'confirm').mockReturnValue(true)
    const wrapper = mountDialog()
    await flushPromises()
    const replaceReal = wrapper.findAll('button')
      .find((button) => button.text().includes('Заменить реальные данные тестовыми'))

    await replaceReal?.trigger('click')
    await flushPromises()

    expect(confirmation.mock.calls[0]?.[0]).toContain('Реальные данные будут заменены тестовыми')
    expect(gameApi.requestProfileTransfer).toHaveBeenCalledWith('test_to_real')
  })

  it('shows the completed transfer result after restart', async () => {
    vi.mocked(gameApi.takeProfileTransferResult).mockResolvedValue({
      status: 'complete',
      direction: 'real_to_test',
      backup: '/tmp/backup/nfprogress.db',
    })

    const wrapper = mountDialog()
    await flushPromises()

    expect(wrapper.text()).toContain('Замена данных успешно завершена')
  })
})
