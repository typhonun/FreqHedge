// src/stores/botStore.js
import { reactive } from 'vue'
import axios from 'axios'

const API = 'http://localhost:9000'

const state = reactive({
  bots: [],
  loading: false,
})

export function useBotStore() {
  const fetchBots = async () => {
    state.loading = true
    try {
      const { data } = await axios.get(`${API}/bots`)
      state.bots = data
    } finally {
      state.loading = false
    }
  }

  const createBot = async (payload) => {
    const { data } = await axios.post(`${API}/bots`, payload)
    await fetchBots()
    return data
  }

  const updateBot = async (id, payload) => {
    await axios.put(`${API}/bots/${id}`, payload)
    await fetchBots()
  }

  const deleteBot = async (id) => {
    await axios.delete(`${API}/bots/${id}`)
    await fetchBots()
  }

  const toggleBot = async (id, currentStatus) => {
    const action = currentStatus === 'running' ? 'stop' : 'start'
    await axios.post(`${API}/bots/${id}/${action}`)
    await fetchBots()
  }

  return {
    state,
    listBots: () => state.bots,
    fetchBots,
    createBot,
    updateBot,
    deleteBot,
    toggleBot,
  }
}