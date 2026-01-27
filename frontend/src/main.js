import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'

// 設計系統 - CSS 變數
import './assets/styles/tokens.css'

const app = createApp(App)

app.use(createPinia())
app.use(router)

app.mount('#app')
