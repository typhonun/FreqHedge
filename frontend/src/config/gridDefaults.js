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
  start_mode: 'grid',        // ★ 改为 'grid'，三种模式：'grid' | 'trigger' | 'immediate'
  max_open_grids: 20,
  amount_per_grid: 0,
  trigger_price: 0,
  restart_after_all_tp: false,
})

export function getDefaultGridConfig() {
  return {
    timeframe: '1m',
    grid: JSON.parse(JSON.stringify(GRID_DEFAULTS)),
  }
}