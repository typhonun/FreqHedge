// ⚠️ 修改时请同步 backend/app/core/defaults.py 的 GRID_DEFAULTS
export const GRID_DEFAULTS = Object.freeze({
  lower_price: 0,
  upper_price: 0,
  grid_count: 20,
  spacing_algo: 'arithmetic',
  amount_per_grid: 50,
  tp_per_grid_pct: 0.5,
  stop_below_lower: true,
  stop_above_upper: false,
  start_mode: 'wait',
})

export function getDefaultGridConfig() {
  return JSON.parse(JSON.stringify(GRID_DEFAULTS))
}