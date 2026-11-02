import { defineStore } from "pinia"
import axios from "axios"
import { useModeStore } from './modeStore'

const API = "http://localhost:9000"
let profitCurveSeq = 0
const accountRequests = new Map()
const generalRequests = new Map()
const historyRequests = new Map()

const _q = (botId, dryRun) => {
  const parts = []
  if (botId != null) parts.push(`bot_id=${botId}`)
  parts.push(`dry_run=${dryRun}`)
  parts.push(`_t=${Date.now()}`)
  return `?${parts.join('&')}`
}

export const useTradeStore = defineStore("trade", {
  state: () => ({
    // ============ 账户总览（独立） ============
    accountBotId: null,
    summary: {},
    floating: {},
    balanceCurve: [],

    // ============ 收益曲线（独立） ============
    profitBotId: null,
    profitCurve: [],

    // ============ 其它通用 ============
    profit: {},
    closedProfit: {},
    positions: { long: [], short: [] },
    closedPositions: { long: [], short: [] },
  }),

  actions: {
    // 账户总览：summary / floating / balanceCurve
    async refreshAccount(botId = null, period = "1D") {
      const modeStore = useModeStore()
      const dryRun = modeStore.isSimulation.value
      const modeKey = dryRun ? 'simulation' : 'live'
      const version = modeStore.requestVersion.value
      const key = `${modeKey}:${botId ?? 'all'}:${period}`
      if (accountRequests.has(key)) return accountRequests.get(key)

      const request = (async () => {
        this.accountBotId = botId
        const q = _q(botId, dryRun)
        try {
          const config = modeStore.getRequestConfig()
          const [summary, floating, curve] = await Promise.all([
            axios.get(`${API}/position/summary${q}`, config),
            axios.get(`${API}/position/floating${q}`, config),
            axios.get(`${API}/position/balance_curve${q}&period=${period}`, config),
          ])
          if (modeStore.isCurrent(modeKey, version)) {
            this.summary = summary.data
            this.floating = floating.data
            this.balanceCurve = curve.data
          }
        } catch (e) {
          if (!axios.isCancel(e)) console.error("refreshAccount error", e.response?.data || e)
        } finally {
          accountRequests.delete(key)
        }
      })()
      accountRequests.set(key, request)
      return request
    },

    // 收益曲线：profitCurve
    async refreshProfitCurve(botId = null, period = 'ALL') {
      const seq = ++profitCurveSeq
      const modeStore = useModeStore()
      const dryRun = modeStore.isSimulation.value
      const modeKey = dryRun ? 'simulation' : 'live'
      const version = modeStore.requestVersion.value
      this.profitBotId = botId
      const q = _q(botId, dryRun)
      try {
        const { data } = await axios.get(
          `${API}/position/profit_curve${q}&period=${period}`,
          modeStore.getRequestConfig()
        )
        // 只有最新一次请求的结果才写入，避免旧响应覆盖新数据
        if (seq === profitCurveSeq && modeStore.isCurrent(modeKey, version)) {
          this.profitCurve = data
        }
      } catch (e) {
        if (!axios.isCancel(e)) console.error("refreshProfitCurve error", e.response?.data || e)
      }
    },

    // 其它页面用的（持仓等，保持全局）
    async refresh(botId = null) {
      const modeStore = useModeStore()
      const dryRun = modeStore.isSimulation.value
      const modeKey = dryRun ? 'simulation' : 'live'
      const version = modeStore.requestVersion.value
      const key = `${modeKey}:${botId ?? 'all'}`
      if (generalRequests.has(key)) return generalRequests.get(key)

      const request = (async () => {
        const q = _q(botId, dryRun)
        try {
          const config = modeStore.getRequestConfig()
          const [profit, positions, summary, floating] = await Promise.all([
            axios.get(`${API}/position/profit${q}`, config),
            axios.get(`${API}/position/open${q}`, config),
            axios.get(`${API}/position/summary${q}`, config),
            axios.get(`${API}/position/floating${q}`, config),
          ])
          if (modeStore.isCurrent(modeKey, version)) {
            this.profit = profit.data
            this.positions = positions.data
            this.summary = summary.data
            this.floating = floating.data
          }
        } catch (e) {
          if (!axios.isCancel(e)) console.error("refresh error", e.response?.data || e)
        } finally {
          generalRequests.delete(key)
        }
      })()
      generalRequests.set(key, request)
      return request
    },

    async refreshHistory(botId = null) {
      const modeStore = useModeStore()
      const dryRun = modeStore.isSimulation.value
      const modeKey = dryRun ? 'simulation' : 'live'
      const version = modeStore.requestVersion.value
      const key = `${modeKey}:${botId ?? 'all'}`
      if (historyRequests.has(key)) return historyRequests.get(key)

      const request = (async () => {
        const q = _q(botId, dryRun)
        const config = modeStore.getRequestConfig()
        const results = await Promise.allSettled([
          axios.get(`${API}/position/closed${q}`, config),
          axios.get(`${API}/position/closed_profit${q}`, config),
        ])
        if (!modeStore.isCurrent(modeKey, version)) return
        if (results[0].status === 'fulfilled') this.closedPositions = results[0].value.data
        if (results[1].status === 'fulfilled') this.closedProfit = results[1].value.data
      })().finally(() => historyRequests.delete(key))
      historyRequests.set(key, request)
      return request
    }
  }
})