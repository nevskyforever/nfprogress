import { createPinia } from 'pinia'
import { describe, expect, it } from 'vitest'

import { useLocaleStore } from './locale'

describe('locale project unit formatting', () => {
  it('uses the correct Russian form for every project unit', () => {
    const locale = useLocaleStore(createPinia())
    locale.language = 'ru'

    expect(locale.formatUnit('symbols', 1)).toBe('символ')
    expect(locale.formatUnit('symbols', 2)).toBe('символа')
    expect(locale.formatUnit('symbols', 5)).toBe('символов')
    expect(locale.formatUnit('symbols', 11)).toBe('символов')
    expect(locale.formatUnit('symbols', 21)).toBe('символ')

    expect(locale.formatUnit('A4', 1)).toBe('лист A4')
    expect(locale.formatUnit('A4', 3)).toBe('листа A4')
    expect(locale.formatUnit('A4', 8)).toBe('листов A4')
    expect(locale.formatUnit('author_list', 1)).toBe('авторский лист')
    expect(locale.formatUnit('author_list', 4)).toBe('авторских листа')
    expect(locale.formatUnit('author_list', 12)).toBe('авторских листов')
    expect(locale.formatUnit('ficbook_pages', 1)).toBe('страница Ficbook')
    expect(locale.formatUnit('ficbook_pages', 2)).toBe('страницы Ficbook')
    expect(locale.formatUnit('ficbook_pages', 5)).toBe('страниц Ficbook')
  })

  it('uses singular and plural translations outside Russian', () => {
    const locale = useLocaleStore(createPinia())
    locale.language = 'en'
    locale.messages = {
      'символ': 'symbol',
      'символов': 'characters',
      'лист A4': 'A4 sheet',
      'листов A4': 'A4 sheets',
    }

    expect(locale.formatUnit('symbols', 1)).toBe('symbol')
    expect(locale.formatUnit('symbols', 2)).toBe('characters')
    expect(locale.formatUnit('A4', 1)).toBe('A4 sheet')
    expect(locale.formatUnit('A4', 2)).toBe('A4 sheets')
  })
})
