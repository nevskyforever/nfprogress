export const PROGRESS_SHARE_IMAGE_SIZE = 1080

const RING_CENTER_X = PROGRESS_SHARE_IMAGE_SIZE / 2
const RING_CENTER_Y = 435
const RING_OUTER_DIAMETER = 620
const RING_WIDTH = 78
const RING_RADIUS = RING_OUTER_DIAMETER / 2 - RING_WIDTH / 2
const TITLE_AREA = { x: 80, y: 805, width: PROGRESS_SHARE_IMAGE_SIZE - 160, height: 157 }
const BRAND_CENTER_Y = PROGRESS_SHARE_IMAGE_SIZE - 54
const BRAND_ICON_SIZE = 46
const BRAND_SPACING = 14
const BRAND_TEXT = 'nfprogress'

const START_COLOR = [169, 169, 169] as const
const END_COLOR = [37, 104, 172] as const

export interface ProgressSharePayload {
  title: string
  progress: number
}

export type ProgressShareResult = 'clipboard' | 'downloaded'

interface TextLayout {
  fontSize: number
  lineHeight: number
  lines: string[]
}

interface ClipboardItemConstructor {
  new (items: Record<string, Blob>): ClipboardItem
}

function canvasContext(canvas: HTMLCanvasElement): CanvasRenderingContext2D {
  const context = canvas.getContext('2d')
  if (!context) throw new Error('Canvas rendering is unavailable.')
  return context
}

export function normalizeProgressSharePercent(value: number): number {
  if (!Number.isFinite(value)) return 0
  return Math.min(100, Math.max(0, Math.round(value)))
}

export function progressShareColor(progress: number): string {
  const ratio = normalizeProgressSharePercent(progress) / 100
  const channels = START_COLOR.map((start, index) => {
    const end = END_COLOR[index] ?? start
    return Math.trunc(start + ratio * (end - start))
  })
  return `rgb(${channels.join(', ')})`
}

export function progressShareTitle(name: string, parentName?: string): string {
  const normalizedName = name.trim() || BRAND_TEXT
  const normalizedParentName = parentName?.trim()
  return normalizedParentName ? `${normalizedParentName}: ${normalizedName}` : normalizedName
}

function titleMaxFontSize(title: string): number {
  const length = title.trim().length
  if (length <= 1) return 155
  if (length <= 4) return 139
  if (length <= 14) return 123
  if (length <= 28) return 104
  return 85
}

function splitLongWord(
  context: CanvasRenderingContext2D,
  word: string,
  maximumWidth: number,
): string[] {
  const chunks: string[] = []
  let chunk = ''

  for (const character of Array.from(word)) {
    const candidate = `${chunk}${character}`
    if (chunk && context.measureText(candidate).width > maximumWidth) {
      chunks.push(chunk)
      chunk = character
    } else {
      chunk = candidate
    }
  }
  if (chunk) chunks.push(chunk)
  return chunks
}

function wrapTitle(
  context: CanvasRenderingContext2D,
  title: string,
  maximumWidth: number,
): string[] {
  const words = title.trim().split(/\s+/).filter(Boolean)
  if (!words.length) return [BRAND_TEXT]

  const lines: string[] = []
  let line = ''
  for (const word of words) {
    const candidates = context.measureText(word).width > maximumWidth
      ? splitLongWord(context, word, maximumWidth)
      : [word]
    for (const candidate of candidates) {
      const combined = line ? `${line} ${candidate}` : candidate
      if (line && context.measureText(combined).width > maximumWidth) {
        lines.push(line)
        line = candidate
      } else {
        line = combined
      }
    }
  }
  if (line) lines.push(line)
  return lines
}

function ellipsizeLine(
  context: CanvasRenderingContext2D,
  line: string,
  maximumWidth: number,
): string {
  const suffix = '…'
  if (context.measureText(line).width <= maximumWidth) return line
  let shortened = line
  while (shortened && context.measureText(`${shortened}${suffix}`).width > maximumWidth) {
    shortened = Array.from(shortened).slice(0, -1).join('')
  }
  return shortened ? `${shortened}${suffix}` : suffix
}

function fitTitle(context: CanvasRenderingContext2D, title: string): TextLayout {
  const maximumFontSize = titleMaxFontSize(title)
  for (let fontSize = maximumFontSize; fontSize >= 27; fontSize -= 2) {
    const lineHeight = Math.ceil(fontSize * 1.16)
    context.font = `700 ${fontSize}px Arial, sans-serif`
    const lines = wrapTitle(context, title, TITLE_AREA.width)
    if (lines.length * lineHeight <= TITLE_AREA.height) {
      return { fontSize, lineHeight, lines }
    }
  }

  const fontSize = 27
  const lineHeight = Math.ceil(fontSize * 1.16)
  const maximumLines = Math.max(1, Math.floor(TITLE_AREA.height / lineHeight))
  context.font = `700 ${fontSize}px Arial, sans-serif`
  const lines = wrapTitle(context, title, TITLE_AREA.width)
  if (lines.length <= maximumLines) return { fontSize, lineHeight, lines }

  const visibleLines = lines.slice(0, maximumLines)
  const lastIndex = visibleLines.length - 1
  const lastLine = visibleLines[lastIndex]
  if (lastLine !== undefined) {
    visibleLines[lastIndex] = ellipsizeLine(context, `${lastLine} ${lines.slice(maximumLines).join(' ')}`, TITLE_AREA.width)
  }
  return { fontSize, lineHeight, lines: visibleLines }
}

function drawProgressRing(context: CanvasRenderingContext2D, progress: number): void {
  context.lineWidth = RING_WIDTH
  context.lineCap = 'round'
  context.strokeStyle = '#E6EBEF'
  context.beginPath()
  context.arc(RING_CENTER_X, RING_CENTER_Y, RING_RADIUS, 0, Math.PI * 2)
  context.stroke()

  if (!progress) return
  context.strokeStyle = progressShareColor(progress)
  context.beginPath()
  context.arc(
    RING_CENTER_X,
    RING_CENTER_Y,
    RING_RADIUS,
    -Math.PI / 2,
    -Math.PI / 2 + (progress / 100) * Math.PI * 2,
  )
  context.stroke()
}

function drawTitle(context: CanvasRenderingContext2D, title: string): void {
  const layout = fitTitle(context, title)
  const totalHeight = layout.lines.length * layout.lineHeight
  let centerY = TITLE_AREA.y + (TITLE_AREA.height - totalHeight) / 2 + layout.lineHeight / 2
  context.fillStyle = '#000000'
  context.font = `700 ${layout.fontSize}px Arial, sans-serif`
  context.textAlign = 'center'
  context.textBaseline = 'middle'
  for (const line of layout.lines) {
    context.fillText(line, PROGRESS_SHARE_IMAGE_SIZE / 2, centerY)
    centerY += layout.lineHeight
  }
}

function roundedRectangle(
  context: CanvasRenderingContext2D,
  x: number,
  y: number,
  width: number,
  height: number,
  radius: number,
): void {
  const boundedRadius = Math.min(radius, width / 2, height / 2)
  context.moveTo(x + boundedRadius, y)
  context.lineTo(x + width - boundedRadius, y)
  context.quadraticCurveTo(x + width, y, x + width, y + boundedRadius)
  context.lineTo(x + width, y + height - boundedRadius)
  context.quadraticCurveTo(x + width, y + height, x + width - boundedRadius, y + height)
  context.lineTo(x + boundedRadius, y + height)
  context.quadraticCurveTo(x, y + height, x, y + height - boundedRadius)
  context.lineTo(x, y + boundedRadius)
  context.quadraticCurveTo(x, y, x + boundedRadius, y)
  context.closePath()
}

function drawBrand(context: CanvasRenderingContext2D): void {
  context.font = '700 37px Arial, sans-serif'
  const textWidth = context.measureText(BRAND_TEXT).width
  const groupWidth = BRAND_ICON_SIZE + BRAND_SPACING + textWidth
  const groupX = (PROGRESS_SHARE_IMAGE_SIZE - groupWidth) / 2
  const iconY = BRAND_CENTER_Y - BRAND_ICON_SIZE / 2

  context.fillStyle = '#2568AC'
  context.beginPath()
  roundedRectangle(context, groupX, iconY, BRAND_ICON_SIZE, BRAND_ICON_SIZE, 12)
  context.fill()
  context.fillStyle = '#FFFFFF'
  context.font = '700 24px Arial, sans-serif'
  context.textAlign = 'center'
  context.textBaseline = 'middle'
  context.fillText('nf', groupX + BRAND_ICON_SIZE / 2, BRAND_CENTER_Y + 1)

  context.fillStyle = '#2568AC'
  context.font = '700 37px Arial, sans-serif'
  context.textAlign = 'left'
  context.fillText(BRAND_TEXT, groupX + BRAND_ICON_SIZE + BRAND_SPACING, BRAND_CENTER_Y)
}

export function drawProgressShareImage(
  context: CanvasRenderingContext2D,
  payload: ProgressSharePayload,
): void {
  const progress = normalizeProgressSharePercent(payload.progress)
  const title = progressShareTitle(payload.title)

  context.fillStyle = '#FFFFFF'
  context.fillRect(0, 0, PROGRESS_SHARE_IMAGE_SIZE, PROGRESS_SHARE_IMAGE_SIZE)
  drawProgressRing(context, progress)

  context.fillStyle = progressShareColor(progress)
  context.font = '700 210px Arial, sans-serif'
  context.textAlign = 'center'
  context.textBaseline = 'middle'
  context.fillText(`${progress}%`, RING_CENTER_X, RING_CENTER_Y)

  drawTitle(context, title)
  drawBrand(context)
}

function canvasBlob(canvas: HTMLCanvasElement): Promise<Blob> {
  return new Promise((resolve, reject) => {
    canvas.toBlob((blob) => {
      if (blob) {
        resolve(blob)
      } else {
        reject(new Error('PNG generation failed.'))
      }
    }, 'image/png')
  })
}

export async function createProgressShareImage(payload: ProgressSharePayload): Promise<Blob> {
  if (typeof document === 'undefined') throw new Error('Canvas rendering is unavailable.')
  const canvas = document.createElement('canvas')
  canvas.width = PROGRESS_SHARE_IMAGE_SIZE
  canvas.height = PROGRESS_SHARE_IMAGE_SIZE
  drawProgressShareImage(canvasContext(canvas), payload)
  return canvasBlob(canvas)
}

function clipboardItemConstructor(): ClipboardItemConstructor | undefined {
  return (globalThis as typeof globalThis & { ClipboardItem?: ClipboardItemConstructor }).ClipboardItem
}

async function copyImageToClipboard(blob: Blob): Promise<boolean> {
  const ClipboardImageItem = clipboardItemConstructor()
  if (
    typeof navigator === 'undefined'
    || !navigator.clipboard
    || typeof navigator.clipboard.write !== 'function'
    || !ClipboardImageItem
  ) {
    return false
  }
  try {
    await navigator.clipboard.write([
      new ClipboardImageItem({ [blob.type || 'image/png']: blob }),
    ])
    return true
  } catch {
    return false
  }
}

function downloadImage(blob: Blob): void {
  if (typeof document === 'undefined' || typeof URL.createObjectURL !== 'function') {
    throw new Error('PNG download is unavailable.')
  }
  const url = URL.createObjectURL(blob)
  const revokeObjectURL = typeof URL.revokeObjectURL === 'function'
    ? URL.revokeObjectURL
    : undefined
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = 'nfprogress-progress.png'
  anchor.rel = 'noopener'
  anchor.style.display = 'none'
  document.body.append(anchor)
  anchor.click()
  anchor.remove()
  if (revokeObjectURL) window.setTimeout(() => revokeObjectURL(url), 0)
}

export async function shareProgressImage(payload: ProgressSharePayload): Promise<ProgressShareResult> {
  const image = await createProgressShareImage(payload)
  if (await copyImageToClipboard(image)) return 'clipboard'
  downloadImage(image)
  return 'downloaded'
}
