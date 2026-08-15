import { createApp } from 'vue'
import { createPinia } from 'pinia'
import { IonicVue } from '@ionic/vue'

import '@ionic/vue/css/core.css'
import '@ionic/vue/css/normalize.css'
import '@ionic/vue/css/structure.css'
import '@ionic/vue/css/typography.css'
import '@ionic/vue/css/padding.css'
import '@ionic/vue/css/display.css'

import App from './App.vue'
import { initializePlatformRuntime } from './platform/runtime'
import router from './router'
import { useLocaleStore } from './stores/locale'
import { useThemeStore } from './stores/theme'
import './theme/tokens.css'
import './theme/global.css'

async function bootstrap(): Promise<void> {
  await initializePlatformRuntime()

  const app = createApp(App)
  const pinia = createPinia()

  app.use(pinia)
  app.use(IonicVue)
  app.use(router)

  const theme = useThemeStore(pinia)
  const locale = useLocaleStore(pinia)
  theme.initialize()

  await router.isReady()
  app.mount('#app')
  void locale.initialize()
}

void bootstrap()
