import { createRouter, createWebHistory } from 'vue-router'
import Login from '../views/Login.vue'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    { path: '/', redirect: '/login' },
    { path: '/login', name: 'Login', component: Login },
    { 
      path: '/user', 
      component: () => import('../views/user/Upload.vue') 
    },
    { 
      path: '/auditor', 
      component: () => import('../views/auditor/Review.vue') 
    },
    { 
      path: '/admin', 
      component: () => import('../views/admin/Dashboard.vue') 
    }
  ]
})

export default router