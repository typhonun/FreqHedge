import { defineStore } from "pinia"
import axios from "axios"
import { useModeStore } from './modeStore'
import { useExchangeAccounts } from '@/composables/useExchangeAccounts'

const API = "http://localhost:9000"
let profitCurveSeq = 0
let accountCurveSeq = 0
const accountRequests = new Map()
const generalRequests = new Map()
const historyRequests = new Map()

const applyExchangeEquity = (curve, baseCapital, closedProfit, floatingProfit) => {
  const totalEquity = baseCapital + closedProfit + floatingProfit
  const rawCurve = Array.isArray(curve) ? curve : []
  if (!rawCurve.length) return rawCurve

  const latestRawEquity = Number(rawCurve[rawCurve.length - 1].balance || 0)
  const offset = totalEquity - latestRawEquity
  return rawCurve.map((point) => {
    const profit = Number(point.profit || 0)
    const balance = Number((Number(point.balance || 0) + offset).toFixed(2))
    return {
      ...point,
      balance,
      // wallet = equity - floating PnL，按每个时间点动态展示
      wallet: Number((balance - profit).toFixed(2)),
    }
  })
}

const _q = (botId, dryRun, accountId = null) => {
  const parts = []
  if (botId != null) parts.push(`bot_id=${botId}`)
  if (accountId != null) parts.push(`account_id=${encodeURIComponent(accountId)}`)
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
    async refreshAccount(botId = null, period = "1D", accountId = null) {
      const modeStore = useModeStore()
      const dryRun = modeStore.isSimulation.value
      const modeKey = dryRun ? 'simulation' : 'live'
      const version = modeStore.requestVersion.value
      const requestSeq = ++accountCurveSeq
      const key = `${modeKey}:${botId ?? 'all'}:${accountId ?? 'all'}:${period}`
      if (accountRequests.has(key)) return accountRequests.get(key)

      const request = (async () => {
        this.accountBotId = botId
        const q = _q(botId, dryRun, accountId)
        try {
          const config = modeStore.getRequestConfig()
          const accountStore = useExchangeAccounts()
          const liveBalanceRequest = botId == null && !dryRun
            ? accountStore.refreshLiveBalances(accountId)
            : null
          const [summary, floating, curve, closedProfit] = await Promise.all([
            axios.get(`${API}/position/summary${q}`, config),
            axios.get(`${API}/position/floating${q}`, config),
            axios.get(`${API}/position/balance_curve${q}&period=${period}`, config),
            axios.get(`${API}/position/closed_profit${q}`, config),
          ])
          if (requestSeq === accountCurveSeq && modeStore.isCurrent(modeKey, version)) {
            if (botId == null) {
              if (liveBalanceRequest) await liveBalanceRequest
              if (requestSeq !== accountCurveSeq) return
              if (!modeStore.isCurrent(modeKey, version)) return
              const totalCapital = accountStore.totalCapital(dryRun, accountId)
              const usedMargin = Number(summary.data.used_margin || 0)
              const closed = Number(closedProfit.data.total_closed_profit || 0)
              const floatingValue = Number(floating.data.total_float || 0)
              this.summary = {
                ...summary.data,
                total_balance: Number((totalCapital + closed).toFixed(2)),
                available_balance: Number((totalCapital + closed - usedMargin).toFixed(2)),
              }
              this.balanceCurve = applyExchangeEquity(
                curve.data,
                totalCapital,
                closed,
                floatingValue,
              )
            } else {
              this.summary = summary.data
              this.balanceCurve = curve.data
            }
            this.floating = floating.data
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
          const [profit, positions, summary, floating, closedProfit] = await Promise.all([
            axios.get(`${API}/position/profit${q}`, config),
            axios.get(`${API}/position/open${q}`, config),
            axios.get(`${API}/position/summary${q}`, config),
            axios.get(`${API}/position/floating${q}`, config),
            axios.get(`${API}/position/closed_profit${q}`, config),
          ])
          if (modeStore.isCurrent(modeKey, version)) {
            this.profit = profit.data
            this.positions = positions.data
            const accountStore = useExchangeAccounts()
            if (botId == null) {
              if (!dryRun) await accountStore.refreshLiveBalances()
              if (!modeStore.isCurrent(modeKey, version)) return
              const totalCapital = accountStore.totalCapital(dryRun)
              const usedMargin = Number(summary.data.used_margin || 0)
              const closed = Number(closedProfit.data.total_closed_profit || 0)
              const floatingValue = Number(floating.data.total_float || 0)
              this.summary = {
                ...summary.data,
                total_balance: Number((totalCapital + closed).toFixed(2)),
                available_balance: Number((totalCapital + closed - usedMargin).toFixed(2)),
              }
            } else {
              this.summary = summary.data
            }
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