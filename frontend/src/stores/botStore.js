// src/stores/botStore.js
import { reactive } from 'vue'
import axios from 'axios'
import { useModeStore } from './modeStore'

const API = 'http://localhost:9000'

const state = reactive({
  bots: [],
  loading: false,
})
const cache = new Map()
const requests = new Map()

export function useBotStore() {
  const fetchBots = async ({ force = false } = {}) => {
    const modeStore = useModeStore()
    const dryRun = modeStore.isSimulation.value
    const modeKey = dryRun ? 'simulation' : 'live'
    const version = modeStore.requestVersion.value
    const cached = cache.get(modeKey)

    if (!force && cached) {
      state.bots = cached
      return cached
    }
    if (requests.has(modeKey)) return requests.get(modeKey)

    state.loading = true
    const request = axios.get(`${API}/bots`, {
      params: { dry_run: dryRun },
      ...modeStore.getRequestConfig(),
    }).then(({ data }) => {
      if (modeStore.isCurrent(modeKey, version)) {
        cache.set(modeKey, data)
        state.bots = data
      }
      return data
    }).catch((error) => {
      if (axios.isCancel(error)) return cache.get(modeKey) || []
      throw error
    }).finally(() => {
      if (requests.get(modeKey) === request) requests.delete(modeKey)
      state.loading = false
    })
    requests.set(modeKey, request)
    return request
  }

  const createBot = async (payload) => {
    const { data } = await axios.post(`${API}/bots`, payload)
    await fetchBots({ force: true })
    return data
  }

  const updateBot = async (id, payload) => {
    await axios.put(`${API}/bots/${id}`, payload)
    await fetchBots({ force: true })
  }

  const deleteBot = async (id) => {
    await axios.delete(`${API}/bots/${id}`)
    await fetchBots({ force: true })
  }

  const toggleBot = async (id, currentStatus) => {
    const action = currentStatus === 'running' ? 'stop' : 'start'
    await axios.post(`${API}/bots/${id}/${action}`)
    await fetchBots({ force: true })
  }
  const createDraft = async (strategyType = 'dca') => {
    const modeStore = useModeStore()
    const { data } = await axios.post(`${API}/bots/draft`, null, {
      params: {
        strategyType,
        dry_run: modeStore.isSimulation.value,
      }
    })
    return data
  }

  return {
    state,
    listBots: () => state.bots,
    fetchBots,
    createBot,
    updateBot,
    deleteBot,
    toggleBot,
    createDraft,
  }
}