import axios from 'axios';

const api = axios.create({
  baseURL: import.meta.env.PROD ? "https://api.vacchunesports.online" : "/",
  withCredentials: true,
});

api.interceptors.request.use(config => {
  const token = document.cookie
    .split('; ')
    .find(row => row.startsWith('XSRF-TOKEN='))
    ?.split('=')[1];

  if (token) {
    config.headers['X-XSRF-TOKEN'] = decodeURIComponent(token);
  }
  return config;
});

export default api;