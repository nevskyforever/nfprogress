import { describe, expect, it, vi } from 'vitest'
import { MAX_COVER_PREPARED_BYTES, prepareProjectCover, projectCoverDataUrlToBytes } from './projectCoverPreparation'

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
})
