import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [vue(), tailwindcss()],
  server: {
    proxy: {
      "/api": {
        target: "http://nginx",
        changeOrigin: true,
      },
      "/sanctum": {
        target: "http://nginx",
        changeOrigin: true,
      },
      "/ws": {
        target: "http://reverb:8081",
        changeOrigin: true,
      },
    },
    allowedHosts: ["xtracker.local"],
  },
});