// frontend/src/config/gridDefaults.js
// ⚠️ 修改时请同步 backend/app/core/defaults.py 的 GRID_DEFAULTS

export const GRID_DEFAULTS = Object.freeze({
  lower_price: 0,
  upper_price: 0,
  grid_count: 20,
  spacing_algo: 'arithmetic',
  tp_per_grid_pct: 0.5,        // ⚠️ 已废弃：卖点由格上沿决定，此字段仅用于向后兼容
  stop_below_lower: true,
  stop_above_upper: false,
  start_mode: 'wait',
  max_open_grids: 20,
  amount_per_grid: 0,
})

export function getDefaultGridConfig() {
  return {
    timeframe: '5m',
    grid: JSON.parse(JSON.stringify(GRID_DEFAULTS)),
  }
}