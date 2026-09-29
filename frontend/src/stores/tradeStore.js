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
      try {
        const [closed, closedProfit, profitCurve, balanceCurve] = await Promise.all([
          axios.get(`${API}/position/closed${q}`),
          axios.get(`${API}/position/closed_profit${q}`),
          axios.get(`${API}/position/profit_curve`),   // 曲线暂时全局
          axios.get(`${API}/position/balance_curve`),  // 曲线暂时全局
        ])
        this.closedPositions = closed.data
        this.closedProfit = closedProfit.data
        this.profitCurve = profitCurve.data
        this.balanceCurve = balanceCurve.data
      } catch (e) {
        console.error("history error", e.response?.data || e)
      }
    },
  },
})