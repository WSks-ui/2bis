import { createApp } from 'vue'
import { createPinia } from 'pinia'
import './styles/global.css'
import App from './App.vue'
import router, { preloadAuthRoutes, preloadStudioRoute } from './router'
import { installMotion } from './services/motion'
import { preloadAuthImages } from './utils/authAssets'

const app = createApp(App)
app.use(createPinia())
app.use(router)
installMotion(app)
app.mount('#app')

preloadAuthImages()
preloadAuthRoutes()
preloadStudioRoute()
