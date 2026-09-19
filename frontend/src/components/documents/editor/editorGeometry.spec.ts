import { describe, expect, it } from 'vitest'
import { calculateEditorPageGeometry } from './editorGeometry'

describe('custom editor page geometry', () => {
  const desktopInput = {
    viewportWidth: 1000,
    viewportHeight: 800,
    viewportPaddingX: 24,
    viewportPaddingY: 24,
    contentHeight: 1200,
    typewriterMode: false,
  }

  it('keeps page width and visual margins fixed while zooming the content', () => {
    const normal = calculateEditorPageGeometry({ ...desktopInput, zoom: 100 })
    const zoomed = calculateEditorPageGeometry({ ...desktopInput, zoom: 180 })

    expect(normal.pageWidth).toBe(850)
    expect(zoomed.pageWidth).toBe(normal.pageWidth)
    expect(zoomed.contentLeft).toBe(normal.contentLeft)
    expect(zoomed.contentTop).toBe(normal.contentTop)
    expect(zoomed.bottomSpace).toBe(normal.bottomSpace)
  })

  it('compensates layout width so scaled content keeps its visual width', () => {
    const normal = calculateEditorPageGeometry({ ...desktopInput, zoom: 100 })
    const zoomed = calculateEditorPageGeometry({ ...desktopInput, zoom: 180 })

    expect(zoomed.contentLayoutWidth).toBeCloseTo(normal.contentLayoutWidth / 1.8)
    expect(zoomed.contentLayoutWidth * zoomed.scale).toBeCloseTo(normal.visualContentWidth)
    expect(zoomed.visualContentWidth).toBe(normal.visualContentWidth)
  })

  it('uses scaled, reflowed content height for the page height', () => {
    const normal = calculateEditorPageGeometry({ ...desktopInput, contentHeight: 600, zoom: 100 })
    const zoomed = calculateEditorPageGeometry({ ...desktopInput, contentHeight: 900, zoom: 180 })

    expect(normal.pageHeight).toBe(normal.contentTop + 600 + normal.bottomSpace)
    expect(zoomed.pageHeight).toBe(zoomed.contentTop + 900 * 1.8 + zoomed.bottomSpace)
    expect(zoomed.pageHeight).toBeGreaterThan(normal.pageHeight)
  })

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
    expect(geometry.pageWidth).toBe(850)
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
    expect(geometry.visualContentWidth).toBe(334)
    expect(geometry.contentLayoutWidth).toBe(334)
    expect(geometry.contentLeft).toBe(20)
  })
})
