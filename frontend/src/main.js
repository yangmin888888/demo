import { createApp } from 'vue'
import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import zhCn from 'element-plus/es/locale/lang/zh-cn'
import * as ElementPlusIconsVue from '@element-plus/icons-vue'

import App from './App.vue'
import router from './router'
import { setForbiddenHandler, setUnauthorizedHandler } from './utils/request'
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
  useUserStore().clearSession()
  if (router.currentRoute.value.path !== '/login') {
    router.push({ path: '/login', replace: true })
  }
})

// 403 表示"已登录但无权访问"，与 401 的处理不同：
// 不清空登录态，只提示原因并把用户带回可访问的页面
setForbiddenHandler((message) => {
  const store = useUserStore()
  if (!store.token) {
    // 未登录却收到 403（如登录接口对禁用账号返回 403），退回到登录页
    if (router.currentRoute.value.path !== '/login') {
      router.push({ path: '/login', replace: true })
    }
    return
  }
  if (router.currentRoute.value.meta?.superOnly) {
    router.push({ path: '/dashboard', replace: true })
  }
})

app.mount('#app')
