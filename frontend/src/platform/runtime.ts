import { Capacitor } from '@capacitor/core'

interface DesktopBackendConnection {
  apiBaseUrl: string
  sessionToken: string
}

export type RuntimePlatform = 'web' | 'tauri' | 'ios' | 'android'

let runtimePlatform: RuntimePlatform = 'web'

function isTauriRuntime(): boolean {
  return typeof window !== 'undefined' && window.__TAURI_INTERNALS__ !== undefined
}

export function currentPlatform(): RuntimePlatform {
  return runtimePlatform
}

export function isNativeMobile(): boolean {
  return runtimePlatform === 'ios' || runtimePlatform === 'android'
}

async function initializeTauriRuntime(): Promise<void> {
  const { invoke } = await import('@tauri-apps/api/core')
  try {
    const connection = await invoke<DesktopBackendConnection>('backend_connection')
    window.__NFPROGRESS_RUNTIME__ = {
      apiBaseUrl: connection.apiBaseUrl,
      getSessionToken: () => connection.sessionToken,
    }
  } catch (error) {
    window.__NFPROGRESS_RUNTIME__ = {
      startupError:
        error instanceof Error ? error.message : String(error || 'Локальный backend недоступен.'),
    }
  }
}

async function initializeCapacitorRuntime(): Promise<void> {
  const nativePlatform = Capacitor.getPlatform()
  runtimePlatform = nativePlatform === 'ios' ? 'ios' : 'android'
  document.documentElement.dataset.platform = runtimePlatform

  const [{ App }, { Keyboard, KeyboardResize }, { StatusBar, Style }] = await Promise.all([
    import('@capacitor/app'),
    import('@capacitor/keyboard'),
    import('@capacitor/status-bar'),
  ])
  await Promise.allSettled([
    Keyboard.setResizeMode({ mode: KeyboardResize.Native }),
    StatusBar.setOverlaysWebView({ overlay: false }),
    StatusBar.setStyle({ style: Style.Default }),
  ])
  await App.addListener('backButton', ({ canGoBack }) => {
    if (canGoBack) {
      window.history.back()
    } else {
      void App.minimizeApp()
    }
  })
}

export async function syncNativeSystemBars(theme: 'light' | 'dark'): Promise<void> {
  if (!isNativeMobile()) return
  const { StatusBar, Style } = await import('@capacitor/status-bar')
  await Promise.allSettled([
    StatusBar.setStyle({ style: theme === 'dark' ? Style.Dark : Style.Light }),
    StatusBar.setBackgroundColor({ color: theme === 'dark' ? '#171b1a' : '#f7f5ef' }),
  ])
}

export async function initializePlatformRuntime(): Promise<void> {
  if (isTauriRuntime()) {
    runtimePlatform = 'tauri'
    document.documentElement.dataset.platform = runtimePlatform
    await initializeTauriRuntime()
    return
  }
  if (Capacitor.isNativePlatform()) {
    await initializeCapacitorRuntime()
    return
  }
  document.documentElement.dataset.platform = runtimePlatform
}

export async function openExternalUrl(url: string): Promise<void> {
  const parsedUrl = new URL(url)
  if (!['https:', 'http:'].includes(parsedUrl.protocol)) {
    throw new Error('Разрешены только HTTP- и HTTPS-ссылки.')
  }
  if (runtimePlatform === 'tauri') {
    const { openUrl } = await import('@tauri-apps/plugin-opener')
    await openUrl(parsedUrl.toString())
    return
  }
  if (isNativeMobile()) {
    const { Browser } = await import('@capacitor/browser')
    await Browser.open({ url: parsedUrl.toString() })
    return
  }
  window.open(parsedUrl.toString(), '_blank', 'noopener,noreferrer')
}
