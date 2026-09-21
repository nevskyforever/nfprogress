import { describe, expect, it, vi } from 'vitest'
import { COVER_HEIGHT, COVER_WIDTH, MAX_COVER_PREPARED_BYTES, MAX_COVER_SOURCE_BYTES, prepareProjectCover, projectCoverDataUrlToBytes, validateProjectCoverSource } from './projectCoverPreparation'

describe('project cover preparation', () => {
  it('uses JPEG Blob bytes and reduces quality before reducing resolution', async () => {
    const sizes = [MAX_COVER_PREPARED_BYTES + 1, 100]
    vi.spyOn(HTMLCanvasElement.prototype, 'toBlob').mockImplementation((callback) => callback(new Blob([new Uint8Array(sizes.shift() ?? 100)], { type: 'image/jpeg' })))
    const draw = vi.fn()
    const result = await prepareProjectCover(draw)
    expect(result.type).toBe('image/jpeg'); expect(result.size).toBe(100); expect(draw).toHaveBeenCalledWith(expect.any(HTMLCanvasElement), 1000, 1500)
    vi.restoreAllMocks()
  })

  it('rejects malformed and unsupported stored data URLs', async () => {
    await expect(projectCoverDataUrlToBytes('data:image/png;base64,AA==')).rejects.toThrow(TypeError)
    await expect(projectCoverDataUrlToBytes('not-a-data-url')).rejects.toThrow(TypeError)
  })

  it('accepts only the declared source MIME types and source size', () => {
    for (const type of ['image/jpeg', 'image/png', 'image/webp']) expect(() => validateProjectCoverSource({ type, size: 1 })).not.toThrow()
    for (const type of ['image/gif', 'image/svg+xml', 'image/avif']) expect(() => validateProjectCoverSource({ type, size: 1 })).toThrow(TypeError)
    expect(() => validateProjectCoverSource({ type: 'image/jpeg', size: MAX_COVER_SOURCE_BYTES + 1 })).toThrow(RangeError)
    expect(COVER_WIDTH / COVER_HEIGHT).toBe(2 / 3)
  })
})
