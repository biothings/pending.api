import './assets/main.css'

import { createApp } from 'vue'
import { createPinia } from 'pinia'

import { useAPIStore } from './stores/apis'

import App from './App.vue'
import router from './router'

const app = createApp(App)

// dev base api url
app.config.globalProperties.$apiUrl =
  process.env.NODE_ENV == 'development' ? 'https://pending.biothings.io' : ''

app.use(createPinia())
app.use(router)

const apiStore = useAPIStore()
apiStore.setApiUrl(app.config.globalProperties.$apiUrl)

app.mount('#app')
