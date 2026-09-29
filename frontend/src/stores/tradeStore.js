import { defineStore } from "pinia"
import axios from "axios"

const API = "http://localhost:9000"

const _q = (botId) => (botId != null ? `?bot_id=${botId}` : "")

export const useTradeStore = defineStore("trade", {
  state: () => ({
    // 当前选中的 bot
    currentBotId: null,

    profit: {},
    closedProfit: {},
    profitCurve: [],
    balanceCurve: [],
    summary: {},
    floating: {},
    positions: { long: [], short: [] },
    closedPositions: { long: [], short: [] },
  }),

  actions: {
    setBotId(botId) {
      if (this.currentBotId === botId) return
      this.currentBotId = botId
      // 清空旧数据，避免切 bot 时短暂显示上一个 bot
      this.profit = {}
      this.closedProfit = {}
      this.summary = {}
      this.floating = {}
      this.positions = { long: [], short: [] }
      this.closedPositions = { long: [], short: [] }
    },

    async refresh(botId = undefined) {
      const q = _q(botId !== undefined ? botId : this.currentBotId)
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

    async refreshHistory(botId = undefined) {
      const q = _q(botId !== undefined ? botId : this.currentBotId)
      const results = await Promise.allSettled([
        axios.get(`${API}/position/closed${q}`),
        axios.get(`${API}/position/closed_profit${q}`),
        axios.get(`${API}/position/profit_curve`),
        axios.get(`${API}/position/balance_curve`),
      ])
      if (results[0].status === 'fulfilled') this.closedPositions = results[0].value.data
      if (results[1].status === 'fulfilled') this.closedProfit = results[1].value.data
      if (results[2].status === 'fulfilled') this.profitCurve = results[2].value.data
      if (results[3].status === 'fulfilled') this.balanceCurve = results[3].value.data
      for (const r of results) {
        if (r.status === 'rejected') {
          console.error('history error', r.reason?.response?.data || r.reason)
        }
      }
    }
  },
})