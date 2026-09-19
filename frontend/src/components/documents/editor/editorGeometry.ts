export const BASE_PAGE_WIDTH = 850
export const DESKTOP_HORIZONTAL_MARGIN = 88
export const DESKTOP_VERTICAL_MARGIN = 80
export const MOBILE_HORIZONTAL_MARGIN = 20
export const MOBILE_VERTICAL_MARGIN = 32
export const TYPEWRITER_RATIO = 0.5

export interface EditorPageGeometryInput {
  viewportWidth: number
  viewportHeight: number
  viewportPaddingX: number
  viewportPaddingY: number
  contentHeight: number
  zoom: number
  typewriterMode: boolean
}

export interface EditorPageGeometry {
  basePageWidth: number
  visualContentWidth: number
  contentLayoutWidth: number
  scale: number
  pageWidth: number
  pageHeight: number
  contentLeft: number
  contentTop: number
  bottomSpace: number
}

export function calculateEditorPageGeometry(input: EditorPageGeometryInput): EditorPageGeometry {
  const scale = Math.min(5, Math.max(0.7, input.zoom / 100))
  const availableWidth = input.viewportWidth > 0
    ? Math.max(280, input.viewportWidth - input.viewportPaddingX * 2)
    : BASE_PAGE_WIDTH
  const basePageWidth = Math.min(BASE_PAGE_WIDTH, availableWidth)
  const compact = basePageWidth < 704
  const horizontalMargin = compact ? MOBILE_HORIZONTAL_MARGIN : DESKTOP_HORIZONTAL_MARGIN
  const verticalMargin = compact ? MOBILE_VERTICAL_MARGIN : DESKTOP_VERTICAL_MARGIN
  const visualContentWidth = Math.max(1, basePageWidth - horizontalMargin * 2)
  const contentLayoutWidth = visualContentWidth / scale
  const normalBottomSpace = verticalMargin
  const bottomSpace = input.typewriterMode
    ? Math.max(normalBottomSpace, input.viewportHeight * TYPEWRITER_RATIO)
    : normalBottomSpace
  const contentTop = verticalMargin
  const contentHeight = Math.max(1, input.contentHeight) * scale
  const naturalHeight = contentTop + contentHeight + bottomSpace
  const minimumHeight = Math.max(1, input.viewportHeight - input.viewportPaddingY * 2)

  return {
    basePageWidth,
    visualContentWidth,
    contentLayoutWidth,
    scale,
    pageWidth: basePageWidth,
    pageHeight: Math.max(naturalHeight, minimumHeight),
    contentLeft: horizontalMargin,
    contentTop,
    bottomSpace,
  }
}
