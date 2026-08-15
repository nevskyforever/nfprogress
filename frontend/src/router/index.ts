import { createRouter, createWebHistory } from '@ionic/vue-router'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    { path: '/', redirect: '/projects' },
    {
      path: '/projects',
      name: 'projects',
      component: () => import('@/pages/ProjectsPage.vue'),
      meta: { title: 'Проекты' },
    },
    {
      path: '/projects/:projectId',
      name: 'project-detail',
      component: () => import('@/pages/ProjectDetailPage.vue'),
      props: true,
      meta: { title: 'Проект' },
    },
    {
      path: '/projects/:projectId/notes',
      name: 'project-notes',
      component: () => import('@/pages/NotesPage.vue'),
      props: true,
      meta: { title: 'Заметки проекта' },
    },
    { path: '/:pathMatch(.*)*', redirect: '/projects' },
  ],
})

router.afterEach((route) => {
  const pageTitle = typeof route.meta.title === 'string' ? route.meta.title : ''
  document.title = pageTitle ? `${pageTitle} · nfprogress` : 'nfprogress'
})

export default router
