import { createPinia } from 'pinia'
import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { gameApi } from '@/api/game'
import { gameStateFixture } from '@/test/gameFixtures'
import { useNotificationsStore } from '@/stores/notifications'
import { diagnostics } from '@/diagnostics/service'
import DeveloperModeDialog from './DeveloperModeDialog.vue'

vi.mock('@/api/game', () => ({
  gameApi: {
    developerState: vi.fn(),
    developerRestoreStreak: vi.fn(),
    developerCreateStreakSeries: vi.fn(),
    developerStreakState: vi.fn(),
    requestProfileTransfer: vi.fn(),
    takeProfileTransferResult: vi.fn(),
  },
}))

vi.mock('@tauri-apps/api/core', () => ({invoke:vi.fn().mockResolvedValue(undefined)}))

vi.mock('@/platform/runtime', () => ({
  currentPlatform: () => 'tauri',
}))

describe('DeveloperModeDialog test data controls', () => {
  beforeEach(() => {
    vi.mocked(gameApi.developerRestoreStreak).mockReset()
    vi.mocked(gameApi.developerRestoreStreak).mockResolvedValue({ok:true,state:gameStateFixture(),message:'Стрик изменён.',messages:[],result:null})
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
    expect(useNotificationsStore().notifications.at(-1)?.message).toContain('Замена данных запланирована')
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
    expect(useNotificationsStore().notifications.at(-1)?.kind).toBe('success')
  })

  it('notifies about an errored transfer result after restart', async () => {
    vi.mocked(gameApi.takeProfileTransferResult).mockResolvedValue({
      status: 'error', error: 'проверка снимка не пройдена',
    })

    mountDialog()
    await flushPromises()

    expect(useNotificationsStore().notifications.at(-1)?.kind).toBe('error')
    expect(useNotificationsStore().notifications.at(-1)?.message).toContain('проверка снимка не пройдена')
  })
  it('records correlated successful restoration and keeps cancellation explicit', async () => {
    const record = vi.spyOn(diagnostics,'record')
    const confirmation = vi.spyOn(window,'confirm').mockReturnValue(false)
    const wrapper=mountDialog();await flushPromises()
    const button=wrapper.findAll('button').find(b=>b.text().includes('Восстановить стрик'))!
    await button.trigger('click');await flushPromises()
    expect(gameApi.developerRestoreStreak).not.toHaveBeenCalled()
    expect(record.mock.calls.some(c=>c[2]==='cancelled')).toBe(true)
    record.mockClear();confirmation.mockReturnValue(true)
    await button.trigger('click');await flushPromises()
    await vi.waitFor(() => expect(record.mock.calls.filter(c=>c[1]==='restore_streak')).toHaveLength(3))
    const calls=record.mock.calls.filter(c=>c[1]==='restore_streak')
    expect(calls.map(c=>c[2])).toEqual(['requested','started','succeeded'])
    const id=calls[1]![3]!
    expect(gameApi.developerRestoreStreak).toHaveBeenCalledWith({type:'global'},id)
    expect(calls[2]![3]).toBe(id)
    record.mockRestore();wrapper.unmount()
  })
  it('records stable failure and explains restoration without rendering private errors', async () => {
    const record=vi.spyOn(diagnostics,'record');vi.spyOn(window,'confirm').mockReturnValue(true)
    vi.mocked(gameApi.developerRestoreStreak).mockRejectedValue({code:'Validation',message:'SECRET_GAME_USER_CONTENT',token:'SECRET_TOKEN'})
    const wrapper=mountDialog();await flushPromises()
    await wrapper.findAll('button').find(b=>b.text().includes('Восстановить стрик'))!.trigger('click');await flushPromises()
    expect(wrapper.find('[role="alert"]').text()).toContain('Не удалось восстановить серию')
    expect(wrapper.find('[role="alert"] details').text()).toContain('Validation')
    expect(wrapper.find('[role="alert"] details').attributes('open')).toBeUndefined()
    expect(wrapper.text()).not.toContain('SECRET')
    await vi.waitFor(() => expect(record.mock.calls.filter(c=>c[1]==='restore_streak')).toHaveLength(3))
    const calls=record.mock.calls.filter(c=>c[1]==='restore_streak')
    expect(calls.map(c=>c[2])).toEqual(['requested','started','failed'])
    expect(calls.at(-1)?.[4]).toEqual({error_code:'Validation',error_class:'Error'})
    expect(JSON.stringify(calls)).not.toContain('SECRET');record.mockRestore();wrapper.unmount()
  })

})
