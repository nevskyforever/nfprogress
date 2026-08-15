import { onBeforeUnmount, onMounted, readonly, ref } from 'vue'

import { isNativeMobile } from '@/platform/runtime'

export function useNetworkStatus() {
  const online = ref(typeof navigator === 'undefined' ? true : navigator.onLine)
  let nativeListener: { remove: () => Promise<void> } | null = null
  let disposed = false

  const markOnline = () => {
    online.value = true
  }
  const markOffline = () => {
    online.value = false
  }

  onMounted(() => {
    window.addEventListener('online', markOnline)
    window.addEventListener('offline', markOffline)
    if (isNativeMobile()) {
      void import('@capacitor/network').then(async ({ Network }) => {
        const status = await Network.getStatus()
        if (disposed) return
        online.value = status.connected
        const listener = await Network.addListener('networkStatusChange', (nextStatus) => {
          online.value = nextStatus.connected
        })
        if (disposed) {
          await listener.remove()
        } else {
          nativeListener = listener
        }
      })
    }
  })
  onBeforeUnmount(() => {
    disposed = true
    window.removeEventListener('online', markOnline)
    window.removeEventListener('offline', markOffline)
    void nativeListener?.remove()
    nativeListener = null
  })

  return { online: readonly(online) }
}
