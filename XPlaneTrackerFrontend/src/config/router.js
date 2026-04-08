import { createRouter, createWebHistory } from 'vue-router';
import HomeView from '../views/HomeView.vue';
import LoginView from '../views/LoginView.vue';
import FlightView from '../views/FlightView.vue';
import SharedFlightView from '../views/SharedFlightView.vue';
import { useAuthStore } from '../stores/auth';

const routes = [
  {
    path: '/',
    name: 'home',
    component: HomeView
  },
  {
    path: '/login',
    name: 'login',
    component: LoginView
  },
  {
    path: '/flights',
    name: 'flights',
    component: FlightView,
    meta: { requiresAuth: true }
  },
  {
    path: '/flight/:id',
    name: 'shared-flight',
    component: SharedFlightView
  }
];

const router = createRouter({
  history: createWebHistory(),
  routes
});

router.beforeEach(async (to, from, next) => {
  const authStore = useAuthStore();

  if (to.meta.requiresAuth && !authStore.isAuthenticated) {
    try {
      await authStore.fetchUser();
      next();
    } catch (e) {
      next('/login');
    }
  } else if (to.name === 'login' && authStore.isAuthenticated) {
    next('/flights');
  } else {
    next();
  }
});

export default router;