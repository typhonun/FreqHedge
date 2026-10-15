// ⚠️ 修改时请同步 backend/app/core/defaults.py
export const BOT_DEFAULTS = Object.freeze({
  capital: 1000,
  stakeAmount: 50,
  leverage: 5,
  maxOpenTrades: 3,
  tradingMode: 'futures',
  marginMode: 'cross',
})

export const RISK_DEFAULTS = Object.freeze({
  tp_enabled: false,
  tp_mode: 'amount',
  tp_amount: 0,
  tp_ratio: 0,
  sl_enabled: false,
  sl_mode: 'amount',
  sl_amount: 0,
  sl_ratio: 0,
  trail_enabled: false,
  trail_mode: 'ratio',
  trail_activate_amount: 10,
  trail_activate_ratio: 1,
  trail_drawdown_amount: 5,
  trail_drawdown_ratio: 0.5,
  auto_stop_on_tp: true,
  auto_stop_on_sl: true,
  auto_stop_on_trail: true,
})

export const getDirectionalDefaults = (side) => ({
  entryRsiValue: side === 'long' ? 35 : 65,
  rsiLimit: side === 'long' ? 20 : 80,
  jLimit: side === 'long' ? 0 : 100,
})
