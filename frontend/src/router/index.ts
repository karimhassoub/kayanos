import { createRouter, createWebHistory } from 'vue-router'
import AppLayout from '../layouts/AppLayout.vue'

const router = createRouter({
  history: createWebHistory('/kayanos/'),
  routes: [
    {
      path: '/',
      component: AppLayout,
      children: [
        {
          path: '',
          name: 'Dashboard',
          component: () => import('../pages/Dashboard.vue')
        },
        {
          path: 'units',
          name: 'UnitsList',
          component: () => import('../pages/UnitsList.vue')
        }
      ]
    }
  ]
})

export default router
