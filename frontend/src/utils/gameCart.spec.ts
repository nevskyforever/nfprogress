import { describe, expect, it } from 'vitest'

import type { GameInventory, GameItem } from '@/types/game'
import { cartCapacity, clampCartCount, reconcileCart } from './gameCart'

function item(maximumQuantity: number | null): GameItem {
  return {
    id: 'Предметы:test', key: 'test', category: 'Предметы', name: 'test', description: '', count: 0,
    sellable: false, usable: false, buy: true, maximum_quantity: maximumQuantity,
  }
}

function inventory(count: number): GameInventory {
  return {
    categories: [{
      key: 'Предметы', name: 'Предметы',
      items: [{ ...item(5), count }],
    }],
  }
}

describe('game cart inventory limits', () => {
  it('clamps requested quantities to the remaining inventory capacity', () => {
    expect(cartCapacity(item(5), inventory(3))).toBe(2)
    expect(clampCartCount(item(5), inventory(3), 10)).toBe(2)
    expect(clampCartCount(item(5), inventory(3), 1 + 10)).toBe(2)
    expect(clampCartCount(item(1), inventory(0), 2)).toBe(1)
    expect(clampCartCount(item(5), inventory(5), 1)).toBe(0)
  })

  it('reconciles an open cart when inventory changes', () => {
    const limited = item(5)
    expect(reconcileCart([{ item: limited, count: 3 }], inventory(4)))
      .toEqual([{ item: limited, count: 1 }])
    expect(reconcileCart([{ item: limited, count: 3 }], inventory(5))).toEqual([])
  })

  it('keeps unlimited items unrestricted', () => {
    expect(cartCapacity(item(null), inventory(999))).toBeNull()
    expect(clampCartCount(item(null), inventory(999), 10_000)).toBe(10_000)
  })
})
