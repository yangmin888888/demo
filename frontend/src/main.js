import { createApp } from 'vue'
import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import zhCn from 'element-plus/es/locale/lang/zh-cn'
import * as ElementPlusIconsVue from '@element-plus/icons-vue'

import App from './App.vue'
import router from './router'
import { setUnauthorizedHandler } from './utils/request'
import { useUserStore } from '@/stores/user'
import './styles/index.css'

const app = createApp(App)

for (const [name, component] of Object.entries(ElementPlusIconsVue)) {
  app.component(name, component)
}

app.use(createPinia())
app.use(router)
app.use(ElementPlus, { locale: zhCn })

// token 失效时同步清空 Pinia 状态并跳转登录页，
// 否则路由守卫会因残留的 token 把用户又弹回 /dashboard
setUnauthorizedHandler(() => {
  useUserStore().logout()
  if (router.currentRoute.value.path !== '/login') {
    router.push({ path: '/login', replace: true })
  }
})

app.mount('#app')
