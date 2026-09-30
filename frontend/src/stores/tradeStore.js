import { defineStore } from "pinia"
import axios from "axios"

const API = "http://localhost:9000"
const _q = (botId) => {
  const parts = []
  if (botId != null) parts.push(`bot_id=${botId}`)
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
    async refreshAccount(botId = null) {
      this.accountBotId = botId
      const q = _q(botId)
      try {
        const [summary, floating, curve] = await Promise.all([
          axios.get(`${API}/position/summary${q}`),
          axios.get(`${API}/position/floating${q}`),
          axios.get(`${API}/position/balance_curve${q}`),
        ])
        this.summary = summary.data
        this.floating = floating.data
        this.balanceCurve = curve.data
      } catch (e) {
        console.error("refreshAccount error", e.response?.data || e)
      }
    },

    // 收益曲线：profitCurve
    async refreshProfitCurve(botId = null) {
      this.profitBotId = botId
      const q = _q(botId)
      try {
        const { data } = await axios.get(`${API}/position/profit_curve${q}`)
        this.profitCurve = data
      } catch (e) {
        console.error("refreshProfitCurve error", e.response?.data || e)
      }
    },

    // 其它页面用的（持仓等，保持全局）
    async refresh(botId = null) {
      const q = _q(botId)
      try {
        const [profit, positions, summary, floating] = await Promise.all([
          axios.get(`${API}/position/profit${q}`),
          axios.get(`${API}/position/open${q}`),
          axios.get(`${API}/position/summary${q}`),
          axios.get(`${API}/position/floating${q}`),
        ])
        this.profit = profit.data
        this.positions = positions.data
        this.summary = summary.data
        this.floating = floating.data
      } catch (e) {
        console.error("refresh error", e.response?.data || e)
      }
    },

    async refreshHistory(botId = null) {
      const q = _q(botId)
      const results = await Promise.allSettled([
        axios.get(`${API}/position/closed${q}`),
        axios.get(`${API}/position/closed_profit${q}`),
      ])
      if (results[0].status === 'fulfilled') this.closedPositions = results[0].value.data
      if (results[1].status === 'fulfilled') this.closedProfit = results[1].value.data
    }
  }
})