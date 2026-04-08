import axios from 'axios';

const api = axios.create({
  baseURL: import.meta.env.PROD ? "https://api.xtracker.hu" : "/",
  withCredentials: true,
  headers: {
    'Accept': 'application/json',
    'Content-Type': 'application/json'
  }
});

export default api;