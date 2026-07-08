import axios from 'axios'

const client = axios.create({
  baseURL: '',
  timeout: 10000
})

// 增加请求拦截器动态装载 X-User-Id
client.interceptors.request.use(config => {
  const userId = localStorage.getItem('current_user_id') || '1'
  config.headers['X-User-Id'] = userId
  return config
})

export default client

