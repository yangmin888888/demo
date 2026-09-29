import { createRouter, createWebHistory } from 'vue-router'
import { useUserStore } from '@/stores/user'

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/Login.vue'),
    meta: { title: '登录', public: true },
  },
  {
    path: '/',
    component: () => import('@/layout/AdminLayout.vue'),
    redirect: '/dashboard',
    children: [
      {
        path: 'dashboard',
        name: 'Dashboard',
        component: () => import('@/views/Dashboard.vue'),
        meta: { title: '仪表盘', icon: 'Odometer' },
      },
      {
        path: 'users',
        name: 'Users',
        component: () => import('@/views/user/UserList.vue'),
        meta: { title: '用户管理', icon: 'User', superOnly: true },
      },
      {
        path: 'audit-logs',
        name: 'AuditLogs',
        component: () => import('@/views/audit/AuditLogs.vue'),
        meta: { title: '审计日志', icon: 'Finished', superOnly: true },
      },
    ],
  },
  {
    path: '/:pathMatch(.*)*',
    name: 'NotFound',
    component: () => import('@/views/NotFound.vue'),
    meta: { title: '页面不存在' },
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach(async (to) => {
  const userStore = useUserStore()

  // 刷新页面后 localStorage 里的 token 可能已失效，先确认再放行
  if (userStore.token && !userStore.sessionChecked) {
    await userStore.restoreSession()
  }

  document.title = to.meta.title ? `${to.meta.title} - 管理后台` : '管理后台'

  if (to.meta.public) {
    if (userStore.token && to.path === '/login') return '/dashboard'
    return true
  }
  if (!userStore.token) return { path: '/login', query: to.fullPath === '/' ? {} : { redirect: to.fullPath } }
  if (to.meta.superOnly && !userStore.isSuperuser) return '/dashboard'
  return true
})

export default router
