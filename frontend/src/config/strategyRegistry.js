// frontend/src/config/strategyRegistry.js
import { getDefaultStrategyConfig } from '@features/strategy/composables/useStrategyConfig.js'
import { getDefaultGridConfig } from '@/config/gridDefaults.js'
import StrategyPanel from '@features/strategy/components/StrategyPanel.vue'
import GridPanel from '@features/strategy/components/GridPanel.vue'

export const STRATEGY_DEFS = {
  dca: {
    label: 'DCA 机器人',
    desc: '经典马丁格尔加仓策略，支持 RSI/KDJ 过滤、动态止盈、网格等丰富配置',
    icon: 'TrendCharts',
    color: '#409EFF',
    panel: StrategyPanel,
    configKey: 'longConfig',          // 提交给后端的字段名
    defaultConfig: (side) => getDefaultStrategyConfig(side),
    singlePair: false,
    unwrap: (data, side) => {
      // DCA 长/短各一份，优先按 side 取
      if (side === 'short') return data.shortConfig || data.longConfig
      return data.longConfig || data.shortConfig
    },
    // ★ 面板是否需要"金额模式"等额外 watch（DCA 需要，网格不需要）
    // 目前 BotConfig 里 DCA 特有的一些逻辑通过 v-if 判断 isDca 保留
  },
  grid: {
    label: '网格机器人',
    desc: '在设定价格区间内自动低买高卖，适合震荡行情',
    icon: 'Grid',
    color: '#67C23A',
    panel: GridPanel,
    configKey: 'gridConfig',
    defaultConfig: () => getDefaultGridConfig(),
    singlePair: true, 
    unwrap: (data) => data.gridConfig,
  },
  // ★ 未来加第三种：
  // trailing: {
  //   label: '跟踪止盈机器人',
  //   desc: '浮盈达到激活线后从最高点回撤触发平仓',
  //   icon: 'TrendCharts',
  //   color: '#E6A23C',
  //   panel: () => import('@features/strategy/components/TrailingPanel.vue'),
  //   configKey: 'trailingConfig',
  //   defaultConfig: () => getDefaultTrailingConfig(),
  //   unwrap: (data) => data.trailingConfig,
  // },
}

export function getStrategyDef(type) {
  return STRATEGY_DEFS[type] || STRATEGY_DEFS.dca
}

// ★ 给 StrategySelectDialog 用：列出所有类型
export function listStrategyDefs() {
  return Object.entries(STRATEGY_DEFS).map(([key, def]) => ({ key, ...def }))
}