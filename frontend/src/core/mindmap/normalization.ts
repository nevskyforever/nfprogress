import type { JsonObject, JsonValue } from '@/types/notes'

export const MAX_MAP_BYTES = 16 * 1024 * 1024
export const MAX_MAP_NODES = 50_000
export const MAX_MAP_DEPTH = 512
export const MAX_TOPIC_LENGTH = 300_000

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}

function cloneJson(value: unknown): unknown {
  const serialized = JSON.stringify(value)
  if (serialized === undefined || serialized.length > MAX_MAP_BYTES) return null
  return JSON.parse(serialized) as unknown
}

function normalizeFreeNode(value: unknown, isRoot: boolean, depth: number): JsonObject | null {
  if (!isRecord(value) || typeof value.id !== 'string' || !value.id
    || value.id.length > 512 || typeof value.topic !== 'string'
    || value.topic.length > MAX_TOPIC_LENGTH || value.topic.includes('\0')
    || depth > MAX_MAP_DEPTH) return null
  const node = { ...value } as JsonObject
  const children = Array.isArray(value.children)
    ? value.children.flatMap((child) => {
        const normalized = normalizeFreeNode(child, false, depth + 1)
        return normalized ? [normalized] : []
      })
    : []
  node.children = children
  if (isRoot) {
    const position = isRecord(value.position) ? value.position : {}
    const x = typeof position.x === 'number' && Number.isFinite(position.x) ? position.x : 320
    const y = typeof position.y === 'number' && Number.isFinite(position.y) ? position.y : 240
    node.position = { x, y }
    node.nfprogressFreeRoot = true
  } else {
    delete node.position
    delete node.nfprogressFreeRoot
  }
  if (typeof node.nfprogressNote !== 'boolean') delete node.nfprogressNote
  delete node.parent
  return node
}

function validateNode(value: unknown, depth: number, counter: { value: number }): boolean {
  if (!isRecord(value) || typeof value.id !== 'string' || !value.id
    || typeof value.topic !== 'string' || value.topic.length > MAX_TOPIC_LENGTH
    || value.topic.includes('\0') || !Array.isArray(value.children)
    || depth > MAX_MAP_DEPTH) return false
  counter.value += 1
  if (counter.value > MAX_MAP_NODES) return false
  return value.children.every((child) => validateNode(child, depth + 1, counter))
}

/** Mirrors the Python normalization contract while retaining opaque fields. */
export function normalizeMindMapData(value: unknown): JsonObject | null {
  const cloned = cloneJson(value)
  if (!isRecord(cloned) || !isRecord(cloned.nodeData)) return null
  const root = cloned.nodeData
  if (typeof root.id !== 'string' || !root.id || typeof root.topic !== 'string'
    || !Array.isArray(root.children)) return null
  const counter = { value: 0 }
  if (!validateNode(root, 0, counter)) return null

  const normalized = cloned as JsonObject
  if ('freeNodes' in normalized) {
    if (Array.isArray(normalized.freeNodes)) {
      normalized.freeNodes = normalized.freeNodes.flatMap((item) => {
        const node = normalizeFreeNode(item, true, 0)
        return node ? [node] : []
      })
    } else delete normalized.freeNodes
  }
  if ('nfprogressFloatingItems' in normalized) {
    if (Array.isArray(normalized.nfprogressFloatingItems)) {
      const items = normalized.nfprogressFloatingItems.flatMap((item) => {
        if (!isRecord(item) || typeof item.id !== 'string' || !item.id
          || !['node', 'note'].includes(String(item.kind)) || typeof item.text !== 'string'
          || typeof item.x !== 'number' || !Number.isFinite(item.x)
          || typeof item.y !== 'number' || !Number.isFinite(item.y)) return []
        return [{
          ...item,
          x: Math.min(100, Math.max(0, item.x)),
          y: Math.min(100, Math.max(0, item.y)),
        } as JsonObject]
      })
      const ids = new Set(items.map((item) => String(item.id)))
      normalized.nfprogressFloatingItems = items.map((item) => {
        if (item.kind !== 'node' || typeof item.parentId !== 'string'
          || !ids.has(item.parentId) || item.parentId === item.id) {
          const result = { ...item }
          delete result.parentId
          return result
        }
        return item
      })
    } else delete normalized.nfprogressFloatingItems
  }
  if ('nfprogressFloatingLinks' in normalized) {
    if (Array.isArray(normalized.nfprogressFloatingLinks)) {
      normalized.nfprogressFloatingLinks = normalized.nfprogressFloatingLinks.filter((item): item is JsonValue => {
        if (!isRecord(item) || typeof item.id !== 'string' || !item.id
          || !['floating', 'node'].includes(String(item.fromType))
          || typeof item.from !== 'string' || !item.from
          || !['floating', 'node'].includes(String(item.toType))
          || typeof item.to !== 'string' || !item.to) return false
        return item.fromType !== item.toType || item.from !== item.to
      })
    } else delete normalized.nfprogressFloatingLinks
  }
  return normalized
}

export interface MindMapNote {
  id: string
  text: string
}

export function extractMindMapNotes(value: unknown): MindMapNote[] {
  const map = normalizeMindMapData(value)
  if (!map) return []
  const result: MindMapNote[] = []
  const seen = new Set<string>()
  const add = (id: unknown, text: unknown): void => {
    if (typeof id !== 'string' || !id || typeof text !== 'string' || seen.has(id)) return
    seen.add(id)
    result.push({ id, text })
  }
  if (Array.isArray(map.nfprogressFloatingItems)) {
    for (const item of map.nfprogressFloatingItems) {
      if (isRecord(item) && item.kind === 'note') add(item.id, item.text)
    }
  }
  const walk = (items: unknown): void => {
    if (!Array.isArray(items)) return
    for (const item of items) {
      if (isRecord(item) && item.nfprogressNote === true) add(item.id, item.topic)
      if (isRecord(item)) walk(item.children)
    }
  }
  walk(map.freeNodes)
  return result
}
