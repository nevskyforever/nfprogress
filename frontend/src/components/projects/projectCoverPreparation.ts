export const MAX_COVER_SOURCE_BYTES = 20 * 1024 * 1024
export const MAX_COVER_PREPARED_BYTES = 2 * 1024 * 1024
export const COVER_WIDTH = 1000
export const COVER_HEIGHT = 1500

export type CoverDraw = (canvas: HTMLCanvasElement, width: number, height: number) => void

function toBlob(canvas: HTMLCanvasElement, quality: number): Promise<Blob> {
  return new Promise((resolve, reject) => canvas.toBlob((blob) => {
    if (blob) resolve(blob)
    else reject(new Error('Cover encoding failed.'))
  }, 'image/jpeg', quality))
}

/** Encodes a cropped 2:3 image by byte size, never by Data URL length. */
export async function prepareProjectCover(draw: CoverDraw): Promise<Blob> {
  let width = COVER_WIDTH
  let height = COVER_HEIGHT
  for (let scaleAttempt = 0; scaleAttempt < 6; scaleAttempt += 1) {
    const canvas = document.createElement('canvas')
    canvas.width = width
    canvas.height = height
    draw(canvas, width, height)
    for (const quality of [0.9, 0.82, 0.74, 0.66, 0.58, 0.5, 0.42]) {
      const blob = await toBlob(canvas, quality)
      if (blob.type === 'image/jpeg' && blob.size <= MAX_COVER_PREPARED_BYTES) return blob
    }
    width = Math.max(2, Math.floor(width * 0.8))
    height = Math.max(3, Math.floor(height * 0.8))
  }
  throw new Error('Cover exceeds size limit.')
}

export function blobToDataUrl(blob: Blob): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => typeof reader.result === 'string' ? resolve(reader.result) : reject(new Error('Cover reading failed.'))
    reader.onerror = () => reject(new Error('Cover reading failed.'))
    reader.readAsDataURL(blob)
  })
}

export async function projectCoverDataUrlToBytes(value: string): Promise<Uint8Array> {
  if (!/^data:image\/jpeg;base64,[A-Za-z0-9+/]+={0,2}$/.test(value)) throw new TypeError('Invalid project cover Data URL.')
  const response = await fetch(value)
  if (!response.ok) throw new TypeError('Invalid project cover Data URL.')
  const bytes = new Uint8Array(await response.arrayBuffer())
  if (bytes.byteLength > MAX_COVER_PREPARED_BYTES) throw new RangeError('Project cover exceeds 2 MiB.')
  return bytes
}
