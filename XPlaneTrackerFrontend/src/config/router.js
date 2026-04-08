import { createRouter, createWebHistory } from 'vue-router';
import HomeView from '../views/HomeView.vue';
import LoginView from '../views/LoginView.vue';
import FlightView from '../views/FlightView.vue';

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
    component: FlightView
  }
];

const router = createRouter({
  history: createWebHistory(),
  routes
});

export default router;