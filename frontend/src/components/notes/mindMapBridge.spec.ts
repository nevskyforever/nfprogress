import { describe, expect, it } from 'vitest'

import { parseMindMapData, parseMindMapEvents } from './mindMapBridge'

describe('Mind Elixir bridge adapter', () => {
  it('accepts map objects and rejects invalid or non-object payloads', () => {
    expect(parseMindMapData('{"nodeData":{"id":"root"}}')).toEqual({
      nodeData: { id: 'root' },
    })
    expect(parseMindMapData('[]')).toBeNull()
    expect(parseMindMapData('{broken')).toBeNull()
  })

  it('keeps only recognized, correctly typed editor events', () => {
    const events = parseMindMapEvents(
      JSON.stringify([
        { type: 'ready' },
        { type: 'save', payload: '{"nodeData":{}}' },
        { type: 'save', payload: 42 },
        { type: 'unknown' },
        null,
      ]),
    )

    expect(events).toEqual([
      { type: 'ready' },
      { type: 'save', payload: '{"nodeData":{}}' },
    ])
  })
})
