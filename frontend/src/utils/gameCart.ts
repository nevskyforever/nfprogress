import type { GameInventory, GameItem } from '@/types/game'

export interface CartEntry {
  item: GameItem
  count: number
}

export function inventoryItemCount(item: GameItem, inventory: GameInventory): number {
  return inventory.categories
    .find((category) => category.key === item.category)?.items
    .find((inventoryItem) => inventoryItem.key === item.key)?.count ?? 0
}

export function cartCapacity(item: GameItem, inventory: GameInventory): number | null {
  if (item.maximum_quantity === null || item.maximum_quantity === undefined) return null
  return Math.max(0, item.maximum_quantity - inventoryItemCount(item, inventory))
}

export function clampCartCount(
  item: GameItem,
  inventory: GameInventory,
  requestedTotal: number,
): number {
  const normalized = Math.max(0, Math.floor(requestedTotal))
  const capacity = cartCapacity(item, inventory)
  return capacity === null ? normalized : Math.min(normalized, capacity)
}

export function reconcileCart<T extends CartEntry>(lines: T[], inventory: GameInventory): T[] {
  return lines.flatMap((line) => {
    const count = clampCartCount(line.item, inventory, line.count)
    return count > 0 ? [{ ...line, count }] : []
  })
}
