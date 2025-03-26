import { createRouter, createWebHistory } from 'vue-router'
import HomeView from '../views/HomeView.vue'
import { useAPIStore } from '../stores/apis'


const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  linkActiveClass: "route-active",
  scrollBehavior(to) {
    if (to.hash) {
        return { el: to.hash }
    }else{
      window.scrollTo(0, 0);
    }
  },
  routes: [
    {
      path: '/',
      name: 'home',
      component: HomeView,
    },
    {
      path: '/try/:api',
      name: 'try',
      props: true,
      component: () => import('../views/Try.vue'),
      beforeEnter: (to, from, next) => {
        const store = useAPIStore();
        if (store.apis.includes(to.params.api)) {
          store.query = ""
          next()
        }else{
          next({name: '404'})
        }
      }
    },
    {
      path: '/about',
      name: 'about',
      // route level code-splitting
      // this generates a separate chunk (About.[hash].js) for this route
      // which is lazy-loaded when the route is visited.
      component: () => import('../views/AboutView.vue'),
    },
    {
      path: "/:catchAll(.*)",
      name: '404',
      component: () => import('../views/404.vue'),
      meta: { sitemap: { ignoreRoute: true } }
  }
  ],
});

export default router
