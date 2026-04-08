import { defineStore } from 'pinia';
import api from '../config/api';

export const useAuthStore = defineStore('auth', {
  state: () => ({
    user: null,
    isAuthenticated: false,
  }),

  actions: {
    async login(credentials) {
      try {
        const response = await api.post('/api/login', credentials);

        this.user = response.data.user;
        this.isAuthenticated = true;

        return response.data;
      } catch (error) {
        this.isAuthenticated = false;
        this.user = null;
        throw error;
      }
    },

    async fetchUser() {
      try {
        const response = await api.get('/api/user');
        this.user = response.data;
        this.isAuthenticated = true;
      } catch (error) {
        this.user = null;
        this.isAuthenticated = false;
      }
    },

    async logout() {
      await api.post('/api/logout');
      this.user = null;
      this.isAuthenticated = false;
    }
  }
});