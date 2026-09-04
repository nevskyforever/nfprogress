import { currentPlatform } from './runtime'

function selectedPath(value: string | string[] | null): string | null {
  if (typeof value === 'string') return value
  return value?.[0] ?? null
}

async function requireTauriDialog() {
  if (currentPlatform() !== 'tauri') {
    throw new Error('Системный выбор локального пути доступен только в desktop-приложении.')
  }
  return import('@tauri-apps/plugin-dialog')
}

export async function pickDesktopWordFile(title: string, filterName: string): Promise<string | null> {
  const { open } = await requireTauriDialog()
  return selectedPath(
    await open({
      title,
      multiple: false,
      directory: false,
      filters: [{ name: filterName, extensions: ['docx'] }],
    }),
  )
}

export async function pickDesktopWordSavePath(title: string, defaultName: string): Promise<string | null> {
  const { save } = await requireTauriDialog()
  return save({ title, defaultPath: defaultName, filters: [{ name: 'Word', extensions: ['docx'] }] })
}

export async function pickDesktopScrivenerProject(title: string): Promise<string | null> {
  const { open } = await requireTauriDialog()
  return selectedPath(
    await open({
      title,
      multiple: false,
      // A .scriv project is a directory package on macOS.  The legacy UI
      // opens it through a file dialog, which lets the user select the package
      // itself instead of navigating inside it as a plain folder.
      directory: false,
      filters: [{ name: 'Scrivener', extensions: ['scriv'] }],
    }),
  )
}
