import { currentPlatform } from './runtime'

export const WORKSPACE_WINDOW_QUERY = 'workspace_window'

const WORKSPACE_WINDOW_WIDTH = 1180
const WORKSPACE_WINDOW_HEIGHT = 820

function workspacePath(path: string): string {
  const url = new URL(path, window.location.href)
  url.searchParams.set(WORKSPACE_WINDOW_QUERY, '1')
  return `${url.pathname}${url.search}${url.hash}`
}

export function isWorkspaceWindow(): boolean {
  if (typeof window === 'undefined') return false
  return new URLSearchParams(window.location.search).get(WORKSPACE_WINDOW_QUERY) === '1'
}

export async function openWorkspaceWindow(path: string, title: string): Promise<void> {
  const target = workspacePath(path)
  if (currentPlatform() === 'tauri') {
    const { WebviewWindow } = await import('@tauri-apps/api/webviewWindow')
    const label = `workspace-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`
    const window = new WebviewWindow(label, {
      url: target,
      title,
      width: WORKSPACE_WINDOW_WIDTH,
      height: WORKSPACE_WINDOW_HEIGHT,
      minWidth: 760,
      minHeight: 560,
      center: true,
    })
    await new Promise<void>((resolve, reject) => {
      void window.once('tauri://created', () => resolve())
      void window.once('tauri://error', (error) => {
        reject(new Error(String(error.payload || 'workspace_window_failed')))
      })
    })
    return
  }
  window.open(
    target,
    '_blank',
    [
      'popup=yes',
      `width=${WORKSPACE_WINDOW_WIDTH}`,
      `height=${WORKSPACE_WINDOW_HEIGHT}`,
      'resizable=yes',
      'scrollbars=yes',
      'noopener',
      'noreferrer',
    ].join(','),
  )
}
