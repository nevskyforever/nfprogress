export interface SessionTokenProvider {
  getSessionToken(): Promise<string | null>
}

class BrowserRuntimeTokenProvider implements SessionTokenProvider {
  async getSessionToken(): Promise<string | null> {
    const token = await window.__NFPROGRESS_RUNTIME__?.getSessionToken?.()
    if (typeof token !== 'string') {
      return null
    }
    return token.trim() || null
  }
}

let activeProvider: SessionTokenProvider = new BrowserRuntimeTokenProvider()

/**
 * Installs a runtime token source. Tauri can replace the browser provider
 * without exposing a persistent secret in the Vite bundle.
 */
export function setSessionTokenProvider(provider: SessionTokenProvider): void {
  activeProvider = provider
}

export function resetSessionTokenProvider(): void {
  activeProvider = new BrowserRuntimeTokenProvider()
}

export async function discoverSessionToken(): Promise<string | null> {
  return activeProvider.getSessionToken()
}
