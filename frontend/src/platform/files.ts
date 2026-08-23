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

export async function pickDesktopScrivenerProject(title: string): Promise<string | null> {
  const { open } = await requireTauriDialog()
  return selectedPath(
    await open({
      title,
      multiple: false,
      directory: true,
    }),
  )
}
