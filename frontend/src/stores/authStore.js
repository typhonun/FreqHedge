// src/stores/authStore.js
import { defineStore } from 'pinia'
import axios from 'axios'

const API = 'http://localhost:9000'
const TOKEN_KEY = 'dcatp_token'

const api = axios.create({ baseURL: API })

// 请求拦截：自动带 token
api.interceptors.request.use((config) => {
  const token = localStorage.getItem(TOKEN_KEY)
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

// 响应拦截：401 跳登录
api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      localStorage.removeItem(TOKEN_KEY)
      if (location.pathname !== '/login') location.href = '/login'
    }
    return Promise.reject(err)
  }
)

export const useAuthStore = defineStore('auth', {
  state: () => ({
    user: null,
    token: localStorage.getItem(TOKEN_KEY) || '',
    initialized: false,
  }),
  getters: {
    isLoggedIn: (s) => !!s.token,
  },
  actions: {
    async register({ email, password, nickname }) {
      const { data } = await api.post('/auth/register', { email, password, nickname })
      this._setAuth(data)
    },
    async login({ email, password }) {
      const { data } = await api.post('/auth/login', { email, password })
      this._setAuth(data)
    },
    async fetchMe() {
      if (!this.token) return
      try {
        const { data } = await api.get('/auth/me')
        this.user = data
      } catch {
        this.logout()
      } finally {
        this.initialized = true
      }
    },
    async updateProfile(nickname) {
      const { data } = await api.put('/auth/profile', { nickname })
      // 更新本地 user
      this.user = { ...this.user, ...data }
      return data
    },
    async changePassword(oldPassword, newPassword) {
      await api.post('/auth/change-password', {
        old_password: oldPassword,
        new_password: newPassword,
      })
    },
    async sendVerifyEmail() {
      await api.post('/auth/send-verify')
    },
    async forgot(email) {
      const { data } = await api.post('/auth/forgot', { email })
      return data      // ★ 把后端的响应返回出去
    },
    async reset(token, newPassword) {
      await api.post('/auth/reset', { token, new_password: newPassword })
    },
    logout() {
      this.token = ''
      this.user = null
      localStorage.removeItem(TOKEN_KEY)
    },
    _setAuth({ access_token, user }) {
      this.token = access_token
      this.user = user
      localStorage.setItem(TOKEN_KEY, access_token)
    },
  },
})

export { api as authApi }