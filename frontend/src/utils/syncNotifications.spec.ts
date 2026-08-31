import { describe, expect, it } from 'vitest'

import { syncBatchNotification } from './syncNotifications'
import type { SyncBatchResult } from '@/types/integrations'
import { projectFixture } from '@/test/fixtures'

const project = projectFixture({ id: 'project-a', unit: 'symbols' })

describe('syncBatchNotification', () => {
  it('combines every target and delta into one notification', () => {
    const batch: SyncBatchResult = {
      checked: 3,
      changed: 2,
      failed: 1,
      items: [
        {
          project_id: 'project-a', stage_id: null, ok: true, changed: true, symbols: 100,
          error: null,
          progress: { project, entry: { id: 'a', new_total: 100, new_total_symbols: 100, added: 100, added_symbols: 100, added_progress: 10, created_at: '2026-08-31T10:00:00' }, added_symbols: 100, game: null, warning: null },
        },
        {
          project_id: 'project-b', stage_id: 'stage-b', ok: true, changed: true, symbols: 20,
          error: null,
          progress: { project: { ...projectFixture({ id: 'project-b', unit: 'A4' }), stages: [projectFixture({ id: 'stage-b', unit: 'A4' })] }, entry: { id: 'b', new_total: 8, new_total_symbols: 14_400, added: -2, added_symbols: -3_600, added_progress: -1, created_at: '2026-08-31T10:00:00' }, added_symbols: -3_600, game: null, warning: null },
        },
        { project_id: 'project-c', stage_id: null, ok: false, changed: false, symbols: null, progress: null, error: { code: 'missing', message: 'Нет файла' } },
      ],
    }

    const result = syncBatchNotification(batch, (source, values = {}) => source.replace(/\{(\w+)\}/g, (_, key) => String(values[key])), String, (unit, value) => `${unit}:${value}`)

    expect(result).toEqual({
      kind: 'warning',
      message: 'Синхронизировано: 1 проектов, 1 этапов. Добавлено: 100 symbols:100. Удалено: 2 A4:2. Не удалось синхронизировать источников: 1.',
    })
  })
})
