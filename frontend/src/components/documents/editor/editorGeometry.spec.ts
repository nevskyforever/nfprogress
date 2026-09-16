import { describe, expect, it } from 'vitest'
import { calculateEditorPageGeometry } from './editorGeometry'

describe('custom editor page geometry', () => {
  it.each([70, 100, 130, 150, 200, 300, 500])('keeps a half-viewport page tail at %i%% zoom', (zoom) => {
    const geometry = calculateEditorPageGeometry({
      viewportWidth: 1000,
      viewportHeight: 800,
      viewportPaddingX: 24,
      viewportPaddingY: 24,
      contentHeight: 1200,
      zoom,
      typewriterMode: true,
    })

    expect(geometry.scale).toBe(zoom / 100)
    expect(geometry.pageWidth).toBe(850 * zoom / 100)
    expect(geometry.bottomSpace).toBeGreaterThanOrEqual(400)
    expect(geometry.pageHeight).toBeGreaterThanOrEqual(
      geometry.contentTop + 1200 * geometry.scale + geometry.bottomSpace,
    )
  })

  it.each([[600, 300], [800, 400]])('recalculates the Typewriter canvas for a %ipx viewport', (height, minimumTail) => {
    const geometry = calculateEditorPageGeometry({
      viewportWidth: 900,
      viewportHeight: height,
      viewportPaddingX: 24,
      viewportPaddingY: 24,
      contentHeight: 100,
      zoom: 100,
      typewriterMode: true,
    })

    expect(geometry.bottomSpace).toBeGreaterThanOrEqual(minimumTail)
  })

  it('reduces the owned page margins on a narrow viewport', () => {
    const geometry = calculateEditorPageGeometry({
      viewportWidth: 390,
      viewportHeight: 700,
      viewportPaddingX: 8,
      viewportPaddingY: 8,
      contentHeight: 100,
      zoom: 100,
      typewriterMode: false,
    })

    expect(geometry.basePageWidth).toBe(374)
    expect(geometry.baseContentWidth).toBe(334)
    expect(geometry.contentLeft).toBe(20)
  })
})
