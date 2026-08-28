import { describe, expect, it } from 'vitest'

import type { ProgressResult } from '@/types/api'

import { progressChangeNotification } from './progressNotifications'

describe('progress notifications', () => {
  const translate = (source: string, parameters: Record<string, string | number> = {}) =>
    source.replace(/\{(\d+)\}/g, (_, key: string) => String(parameters[key] ?? ''))
  const formatNumber = (value: number) => String(value)
  const formatUnit = () => 'символов'

  it('uses a success notification for added units', () => {
    const feedback = progressChangeNotification(
      { entry: { added: 120 } } as ProgressResult,
      { unit: 'symbols' },
      translate,
      formatNumber,
      formatUnit,
    )

    expect(feedback).toEqual({
      kind: 'success',
      message: 'В проект добавлено 120 символов',
    })
  })

  it('uses a warning notification and absolute amount for removed units', () => {
    const feedback = progressChangeNotification(
      { entry: { added: -35 } } as ProgressResult,
      { unit: 'symbols' },
      translate,
      formatNumber,
      formatUnit,
    )

    expect(feedback).toEqual({
      kind: 'warning',
      message: 'Из проекта удалено 35 символов',
    })
  })
})
