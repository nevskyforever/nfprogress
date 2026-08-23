import { afterEach, describe, expect, it, vi } from 'vitest'

import {
  drawProgressShareImage,
  normalizeProgressSharePercent,
  progressShareColor,
  progressShareTitle,
  shareProgressImage,
} from './progressShare'

const initialClipboardDescriptor = Object.getOwnPropertyDescriptor(navigator, 'clipboard')

function drawingContext(): CanvasRenderingContext2D {
  return {
    arc: vi.fn(),
    beginPath: vi.fn(),
    closePath: vi.fn(),
    fill: vi.fn(),
    fillRect: vi.fn(),
    fillText: vi.fn(),
    lineTo: vi.fn(),
    measureText: vi.fn((text: string) => ({ width: text.length * 18 })),
    moveTo: vi.fn(),
    quadraticCurveTo: vi.fn(),
    stroke: vi.fn(),
  } as unknown as CanvasRenderingContext2D
}

describe('progressShare', () => {
  afterEach(() => {
    if (initialClipboardDescriptor) {
      Object.defineProperty(navigator, 'clipboard', initialClipboardDescriptor)
    } else {
      Reflect.deleteProperty(navigator, 'clipboard')
    }
    vi.restoreAllMocks()
    vi.unstubAllGlobals()
  })

  it('keeps the legacy rounded percentage and parent-stage title rules', () => {
    expect(normalizeProgressSharePercent(-1)).toBe(0)
    expect(normalizeProgressSharePercent(42.6)).toBe(43)
    expect(normalizeProgressSharePercent(101)).toBe(100)
    expect(progressShareColor(0)).toBe('rgb(169, 169, 169)')
    expect(progressShareColor(50)).toBe('rgb(103, 136, 170)')
    expect(progressShareColor(100)).toBe('rgb(37, 104, 172)')
    expect(progressShareTitle('Глава 3', 'Роман')).toBe('Роман: Глава 3')
  })

  it('draws the publication card with the ring, percentage, title, and brand', () => {
    const context = drawingContext()

    drawProgressShareImage(context, { title: 'Дом у моря', progress: 42.6 })

    expect(context.fillRect).toHaveBeenCalledWith(0, 0, 1080, 1080)
    expect(context.arc).toHaveBeenCalledTimes(2)
    expect(context.fillText).toHaveBeenCalledWith('43%', 540, 435)
    expect(context.fillText).toHaveBeenCalledWith('nf', expect.any(Number), 1027)
    expect(context.fillText).toHaveBeenCalledWith('nfprogress', expect.any(Number), 1026)
  })

  it('copies a real PNG blob when the platform supports image clipboard writes', async () => {
    const context = drawingContext()
    const image = new Blob(['png'], { type: 'image/png' })
    const write = vi.fn().mockResolvedValue(undefined)
    vi.spyOn(HTMLCanvasElement.prototype, 'getContext').mockReturnValue(context)
    vi.spyOn(HTMLCanvasElement.prototype, 'toBlob').mockImplementation((callback) => callback(image))
    Object.defineProperty(navigator, 'clipboard', {
      configurable: true,
      value: { write },
    })
    class ClipboardItemMock {
      constructor(readonly items: Record<string, Blob>) {}
    }
    vi.stubGlobal('ClipboardItem', ClipboardItemMock)

    await expect(shareProgressImage({ title: 'Дом у моря', progress: 25 })).resolves.toBe('clipboard')

    expect(write).toHaveBeenCalledTimes(1)
    expect(write.mock.calls[0]?.[0]).toHaveLength(1)
  })

  it('downloads the PNG after a clipboard permission or platform fallback', async () => {
    const context = drawingContext()
    const image = new Blob(['png'], { type: 'image/png' })
    const createObjectURL = vi.fn(() => 'blob:nfprogress-progress')
    const revokeObjectURL = vi.fn()
    vi.spyOn(HTMLCanvasElement.prototype, 'getContext').mockReturnValue(context)
    vi.spyOn(HTMLCanvasElement.prototype, 'toBlob').mockImplementation((callback) => callback(image))
    Object.defineProperty(navigator, 'clipboard', {
      configurable: true,
      value: undefined,
    })
    vi.stubGlobal('URL', { createObjectURL, revokeObjectURL })
    const click = vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => {})

    await expect(shareProgressImage({ title: 'Дом у моря', progress: 25 })).resolves.toBe('downloaded')

    expect(createObjectURL).toHaveBeenCalledWith(image)
    expect(click).toHaveBeenCalledTimes(1)
  })
})
