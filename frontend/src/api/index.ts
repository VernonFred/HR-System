import axios from 'axios';

const api = axios.create({
  // 生产环境使用相对路径（nginx代理），开发环境可通过环境变量配置
  baseURL: import.meta.env.VITE_API_BASE_URL || '',
  timeout: 30000
});

// 请求拦截器
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// 响应拦截器
api.interceptors.response.use(
  (response) => {
    return response;
  },
  (error) => {
    if (error.response?.status === 401) {
      // Token 过期或未授权
      localStorage.removeItem('token');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

export default api;

