// frontend/src/config/gridDefaults.js
// ⚠️ 修改时请同步 backend/app/core/defaults.py 的 GRID_DEFAULTS

export const GRID_DEFAULTS = Object.freeze({
  lower_price: 0,
  upper_price: 0,
  grid_count: 20,
  spacing_algo: 'arithmetic',
  tp_per_grid_pct: 0.5,
  stop_below_lower: false,
  stop_above_upper: false,
  start_mode: 'grid',        // 三种模式：'grid' | 'trigger' | 'immediate'
  max_open_grids: 20,
  amount_per_grid: 0,
  trigger_price: 0,
  min_notional_value: 10,
  restart_after_all_tp: false,
  trailing_up: false,
  trailing_down: false,
  dynamic_whitelist: false,  // 动态白名单开关

  // ★ 单币止盈默认值兜底
  pair_tp_enabled: false,
  pair_tp_mode: 'ratio',     // 'ratio' | 'amount'
  pair_tp_ratio: 3.0,
  pair_tp_amount: 10,

  // ★ 多因子区间策略默认值兜底（手动模式下 BotConfig buildPayload 会移除该字段）
  smart_range_mode: 'moderate', // 'aggressive' | 'moderate' | 'conservative'
})

export function getDefaultGridConfig() {
  return {
    timeframe: '1m',
    grid: JSON.parse(JSON.stringify(GRID_DEFAULTS)),
  }
}