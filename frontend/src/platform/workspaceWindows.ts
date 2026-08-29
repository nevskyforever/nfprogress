import { currentPlatform } from './runtime'

export async function openWorkspaceWindow(path: string, title: string): Promise<void> {
  if (currentPlatform() === 'tauri') {
    const { WebviewWindow } = await import('@tauri-apps/api/webviewWindow')
    const label = `workspace-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`
    const window = new WebviewWindow(label, {
      url: path,
      title,
      width: 1180,
      height: 820,
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
  window.open(path, '_blank', 'noopener,noreferrer')
}
