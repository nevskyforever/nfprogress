import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { currentPlatform } from './runtime'
import { isWorkspaceWindow, openWorkspaceWindow } from './workspaceWindows'

vi.mock('./runtime', () => ({
  currentPlatform: vi.fn(),
}))

describe('workspace windows', () => {
  beforeEach(() => {
    vi.mocked(currentPlatform).mockReturnValue('web')
  })

  afterEach(() => {
    vi.restoreAllMocks()
    window.history.replaceState({}, '', '/')
  })

  it('opens web workspaces as popup windows with a standalone marker', async () => {
    const open = vi.spyOn(window, 'open').mockReturnValue(null)

    await openWorkspaceWindow('/maps/project-id?stageId=stage-a', 'Карта проекта')

    expect(open).toHaveBeenCalledWith(
      '/maps/project-id?stageId=stage-a&workspace_window=1',
      '_blank',
      expect.stringContaining('popup=yes'),
    )
    expect(open.mock.calls[0]?.[2]).toContain('width=1180')
    expect(open.mock.calls[0]?.[2]).toContain('height=820')
  })

  it('detects a standalone workspace URL', () => {
    window.history.replaceState({}, '', '/notes/project-id?workspace_window=1')

    expect(isWorkspaceWindow()).toBe(true)
  })
})
