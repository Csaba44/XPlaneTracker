import axios from 'axios';

const api = axios.create({
  baseURL: import.meta.env.PROD ? "https://api.vacchunesports.online" : "/",
  withCredentials: true,
  headers: {
    'Accept': 'application/json',
    'Content-Type': 'application/json'
  }
});

export default api;