import { describe, expect, it } from 'vitest'

import {
  extractMindMapNotes,
  normalizeMindMapData,
} from './normalization'

describe('Mind Elixir normalization', () => {
  it('preserves IDs, ordering, freeNodes and opaque fields', () => {
    const input = {
      nodeData: {
        id: 'root',
        topic: 'Root',
        children: [
          { id: 'first', topic: 'First', children: [] },
          { id: 'second', topic: 'Second', children: [] },
        ],
        customNodeField: { keep: true },
      },
      freeNodes: [{
        id: 'note',
        topic: 'Note',
        children: [],
        position: { x: 40, y: 60 },
        nfprogressNote: true,
        customFreeField: 'keep',
      }],
      customMapField: ['opaque'],
    }

    const result = normalizeMindMapData(input)
    expect(result).not.toBeNull()
    expect(result?.nodeData).toEqual(input.nodeData)
    expect(result?.customMapField).toEqual(['opaque'])
    expect(result?.freeNodes).toEqual([{
      ...input.freeNodes[0],
      nfprogressFreeRoot: true,
    }])
    expect(extractMindMapNotes(result)).toEqual([{ id: 'note', text: 'Note' }])
  })

  it('rejects invalid roots and excessive tree depth', () => {
    expect(normalizeMindMapData({ nodeData: { id: 'root', topic: 'Root' } })).toBeNull()
    expect(normalizeMindMapData({ nodeData: { id: 'root', topic: 'Root', children: [{ id: 'x', topic: 'x', children: 'bad' }] } })).toBeNull()
  })
})
