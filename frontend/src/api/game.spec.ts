import { afterEach, describe, expect, it, vi } from 'vitest'

import { gameApi } from './game'

afterEach(() => vi.unstubAllGlobals())

describe('gameApi', () => {
  it('sends canonical session, notification, streak-freeze, inventory and bank commands', async () => {
    const fetchMock = vi.fn().mockImplementation(() => Promise.resolve(
      new Response(JSON.stringify({ ok: true }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    ))
    vi.stubGlobal('fetch', fetchMock)

    await gameApi.startWritingSession({
      duration_minutes: 25,
      target_symbols: 1_000,
      intention: 'Продолжить черновик',
      mode: 'flow',
    })
    await gameApi.notifications()
    await gameApi.markNotificationRead('notice/id')
    await gameApi.markAllNotificationsRead()
    await gameApi.applyStreakFreeze('project', 'project/id')
    await gameApi.useItem({ category: 'Предметы', item_id: 'Медаль качества', count: 1 })
    await gameApi.partiallyRepayBankCredit(125)

    const requests = fetchMock.mock.calls.map(([url, options]) => {
      const body = (options as RequestInit).body
      return {
        url: String(url),
        method: (options as RequestInit).method,
        body: typeof body === 'string'
          ? JSON.parse(body) as Record<string, unknown>
          : null,
      }
    })
    expect(requests).toEqual([
      {
        url: '/api/game/writing-sessions/start',
        method: 'POST',
        body: {
          duration_minutes: 25,
          target_symbols: 1_000,
          intention: 'Продолжить черновик',
          mode: 'flow',
        },
      },
      {
        url: '/api/game/notifications',
        method: undefined,
        body: null,
      },
      {
        url: '/api/game/notifications/notice%2Fid/read',
        method: 'POST',
        body: null,
      },
      {
        url: '/api/game/notifications/read-all',
        method: 'POST',
        body: null,
      },
      {
        url: '/api/game/streak-freezes/apply',
        method: 'POST',
        body: { target: 'project', project_id: 'project/id' },
      },
      {
        url: '/api/game/inventory/use',
        method: 'POST',
        body: { category: 'Предметы', item_id: 'Медаль качества', count: 1 },
      },
      {
        url: '/api/game/bank/credit/partial-repayment',
        method: 'POST',
        body: { amount: 125 },
      },
    ])
  })

  it('encodes custom award IDs before addressing a saved definition', async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ ok: true }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    )
    vi.stubGlobal('fetch', fetchMock)

    await gameApi.updateCustomAward('award/id', { name: 'Выходной', price: 80 })

    const [url, options] = fetchMock.mock.calls[0] as [string, RequestInit]
    expect(url).toBe('/api/game/custom-awards/award%2Fid')
    expect(options.method).toBe('PATCH')
  })
})
