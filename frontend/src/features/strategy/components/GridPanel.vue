<template>
  <div class="grid-panel">
    <!-- ★ 优化：取消全局的固定 label-width，让自适应和特定宽度结合 -->
    <el-form size="small" class="compact-form" label-width="auto">

      <!-- ── 1. 价格区间 ── -->
      <div class="section-block">
        <div class="section-header">
          <div class="section-title">价格区间</div>
          <div class="smart-range-inline">
            <span class="smart-label">智能填入：</span>
            <el-button-group>
              <el-button size="small" :loading="loadingSuggest === 7" @click="applySuggest(7)">激进(7天)</el-button>
              <el-button size="small" :loading="loadingSuggest === 30" @click="applySuggest(30)">稳健(30天)</el-button>
              <el-button size="small" :loading="loadingSuggest === 90" @click="applySuggest(90)">保守(90天)</el-button>
            </el-button-group>
            <span v-if="lastSuggestInfo" class="current-price-tip">{{ lastSuggestInfo }}</span>
          </div>
        </div>

        <div class="form-row">
          <!-- ★ 使用全局自适应宽度，输入框限制最大宽度 -->
          <el-form-item label="网格下限价" class="form-item-half">
            <el-input-number v-model="config.grid.lower_price" :min="0" :step="100" controls-position="right" class="num-input" />
          </el-form-item>
          <el-form-item label="网格上限价" class="form-item-half">
            <el-input-number v-model="config.grid.upper_price" :min="0" :step="100" controls-position="right" class="num-input" />
          </el-form-item>
        </div>
      </div>

      <!-- ── 2. 网格参数 ── -->
      <div class="section-block">
        <div class="section-header">
          <div class="section-title">网格参数</div>
        </div>

        <!-- 第一行：网格数量 & 最大持仓网格 -->
        <div class="form-row">
          <el-form-item label="网格数量" class="form-item-half">
            <el-input-number
              v-model="config.grid.grid_count"
              :min="2" :max="200" :step="1"
              controls-position="right" class="num-input"
              @change="onGridCountChange"
            />
          </el-form-item>

          <!-- ★ 单独为此项设置更宽的 label，防止文字挤行 -->
          <el-form-item label="最大持仓网格" class="form-item-half" label-width="100px">
            <div class="input-with-icon">
              <el-input-number
                v-model="config.grid.max_open_grids"
                :min="1"
                :max="config.grid.grid_count"
                :step="1"
                controls-position="right"
                class="num-input"
              />
              <el-tooltip placement="top" effect="dark"
                content="同时持有的最大未止盈网格数量，调小可限制单边行情下的敞口">
                <el-icon class="section-label__info"><InfoFilled /></el-icon>
              </el-tooltip>
            </div>
          </el-form-item>
        </div>

        <!-- 第二行：间距算法 & K线周期 -->
        <div class="form-row">
          <el-form-item label="间距算法" class="form-item-half">
            <el-select v-model="config.grid.spacing_algo" class="flex-input">
              <el-option label="等差" value="arithmetic" />
              <el-option label="等比" value="geometric" />
            </el-select>
          </el-form-item>
          <el-form-item label="K 线周期" class="form-item-half">
            <el-select v-model="config.timeframe" class="flex-input" @change="onTimeframeChange">
              <el-option label="1m"  value="1m" />
              <el-option label="3m"  value="3m" />
              <el-option label="5m"  value="5m" />
              <el-option label="15m" value="15m" />
              <el-option label="30m" value="30m" />
            </el-select>
          </el-form-item>
        </div>
      </div>

      <!-- ── 3. 止损 ── -->
      <div class="section-block">
        <div class="section-header">
          <div class="section-title">止损</div>
        </div>
        <div class="form-row">
          <el-form-item v-if="direction === 'long'" label="跌破下沿止损" class="form-item-full" label-width="100px">
            <div class="input-with-icon">
              <el-switch v-model="config.grid.stop_below_lower" />
              <el-tooltip placement="top" effect="dark" content="价格跌破下沿时，清空所有持仓并停止机器人">
                <el-icon class="section-label__info"><InfoFilled /></el-icon>
              </el-tooltip>
            </div>
          </el-form-item>
          <el-form-item v-if="direction === 'short'" label="突破上沿止损" class="form-item-full" label-width="100px">
            <div class="input-with-icon">
              <el-switch v-model="config.grid.stop_above_upper" />
              <el-tooltip placement="top" effect="dark" content="价格突破上沿时，清空所有持仓并停止机器人">
                <el-icon class="section-label__info"><InfoFilled /></el-icon>
              </el-tooltip>
            </div>
          </el-form-item>
        </div>
      </div>

      <!-- ── 4. 启动模式 ── -->
      <div class="section-block">
        <div class="section-header">
          <div class="section-title">启动模式</div>
        </div>

        <div class="form-row">
          <el-form-item label="启动模式" class="form-item-full">
            <div class="input-with-icon">
              <el-radio-group v-model="config.grid.start_mode">
                <el-radio-button value="grid">网格触发</el-radio-button>
                <el-radio-button value="trigger">触发价启动</el-radio-button>
                <el-radio-button value="immediate">立即启动</el-radio-button>
              </el-radio-group>
              <el-tooltip placement="top" effect="dark">
                <template #content>
                  <template v-if="config.grid.start_mode === 'grid'">
                    价格跌到最近的买格（多头）/ 涨到最近的卖格（空头）时，自动买入首仓
                  </template>
                  <template v-else-if="config.grid.start_mode === 'trigger'">
                    价格跌破（多头）/ 突破（空头）触发价时，买入首仓并启动网格。<br/>
                    <span style="color: #e6a23c;">若机器人启动时价格已在触发价下方（多头）/ 上方（空头），需等价格重新穿越触发价才会开仓。</span>
                  </template>
                  <template v-else>
                    机器人启动后，以当前价立即买入首仓
                  </template>
                </template>
                <el-icon class="section-label__info"><InfoFilled /></el-icon>
              </el-tooltip>
            </div>
          </el-form-item>
        </div>

        <div class="form-row" v-if="config.grid.start_mode === 'trigger'">
          <el-form-item label="触发价格" class="form-item-full">
            <div class="input-with-hint" style="flex-direction: row; align-items: center; gap: 12px;">
              <el-input-number
                v-model="config.grid.trigger_price"
                :min="0" :step="10"
                controls-position="right"
                class="num-input"
                :class="triggerPriceError ? 'is-error' : ''"
              />
              <div v-if="triggerPriceTip" class="inline-hint" :class="triggerPriceError ? 'is-error' : 'is-info'">
                <el-icon class="section-label__info">
                  <WarningFilled v-if="triggerPriceError" />
                  <InfoFilled v-else />
                </el-icon>
                {{ triggerPriceTip }}
              </div>
            </div>
          </el-form-item>
        </div>
      </div>

      <!-- ── 5. 高级选项 ── -->
      <div class="section-block">
        <div class="section-header">
          <div class="section-title">高级选项</div>
        </div>
        <div class="form-row">
          <!-- ★ 加宽 label 防止挤压 -->
          <el-form-item label="全部止盈后重启" class="form-item-full" label-width="110px">
            <div class="input-with-icon">
              <el-switch v-model="config.grid.restart_after_all_tp" />
              <el-tooltip placement="top" effect="dark" content="当所有网格仓位全部止盈平仓后，如果价格继续上涨/下跌，不等待回落，直接以当前价再次买入首仓">
                <el-icon class="section-label__info"><InfoFilled /></el-icon>
              </el-tooltip>
            </div>
          </el-form-item>
        </div>
      </div>

      <!-- ── 6. 网格预览（可折叠） ── -->
      <div v-if="gridPreview" class="grid-preview-wrapper">
        <div class="grid-preview-header" @click="showGridPreview = !showGridPreview">
          <div class="grid-preview-title">
            <span>网格预览</span>

            <!-- 原有的统计数据 -->
            <span class="grid-preview-stats-inline">
              格距 ≈ {{ gridPreview.stepText }} |
              每格利润 ≈ {{ gridPreview.profitText }} |
              总投入 ≈ {{ gridPreview.totalText }} USDT |
              最大持仓 {{ config.grid.max_open_grids }} 格
            </span>

            <!-- ★ 新增：止盈低于手续费的红色警告 -->
            <span v-if="isProfitTooLow" class="grid-preview-warn" style="color: var(--el-color-danger);">
              <el-icon><WarningFilled /></el-icon>
              单格利润过低，可能无法覆盖手续费，建议增加网格步长或减少网格数
            </span>

            <!-- 原有的格距过小提示 -->
            <span v-if="gridPreview.tooNarrow && !isProfitTooLow" class="grid-preview-warn">
              <el-icon><WarningFilled /></el-icon> 格距过小
            </span>
          </div>
          <el-icon class="toggle-icon" :class="{ 'is-expanded': showGridPreview }">
            <ArrowDown />
          </el-icon>
        </div>

        <el-collapse-transition>
          <div v-show="showGridPreview" class="grid-preview-content">
            <div class="grid-preview-divider">
              <span class="divider-line"></span>
              <span class="divider-text">当前价 {{ gridPreview.refPriceText }}</span>
              <span class="divider-line"></span>
            </div>

            <div class="grid-preview-section">
              <div class="grid-preview-section-title">{{ gridPreview.topLabel }}</div>
              <div class="grid-preview__lines">
                <span v-for="(p, i) in gridPreview.topLevels" :key="'top-'+i">
                  {{ p }}
                </span>
              </div>
            </div>

            <div class="grid-preview-section">
              <div class="grid-preview-section-title">{{ gridPreview.bottomLabel }}</div>
              <div class="grid-preview__lines">
                <span v-for="(p, i) in gridPreview.bottomLevels" :key="'bot-'+i">
                  {{ p }}
                </span>
              </div>
            </div>
          </div>
        </el-collapse-transition>
      </div>

    </el-form>
  </div>
</template>

<script setup>
// ... 保持原样，逻辑未变
import { computed, ref, onMounted } from 'vue'
import axios from 'axios'
import { ElMessage } from 'element-plus'
import { InfoFilled, WarningFilled, ArrowDown } from '@element-plus/icons-vue'

const API = 'http://localhost:9000'
const FEE_RATE = 0.001 // 双边预计手续费 0.1% (Taker)

const props = defineProps({
  config: { type: Object, required: true },
  capital: { type: Number, default: 1000 },
  pair:    { type: String, default: '' },
  direction: { type: String, default: 'long' },
  leverage:  { type: Number, default: 1 },
})
const emit = defineEmits(['timeframe-change'])
const onTimeframeChange = (val) => {
  emit('timeframe-change', val)
}

const loadingSuggest = ref(0)
const lastSuggestInfo = ref('')
const currentPrice = ref(null)
const showGridPreview = ref(false)

const perGrid = computed(() => {
  const c = props.config?.grid || {}
  const count = Math.max(1, Number(c.grid_count || 0))
  const cap = Number(props.capital || 0)
  return cap / count
})

const triggerPriceTip = computed(() => {
  const g = props.config?.grid
  if (!g || g.start_mode !== 'trigger') return ''

  const trigger = Number(g.trigger_price || 0)
  const current = Number(currentPrice.value || 0)

  if (trigger <= 0) return '请输入触发价格'
  if (current <= 0) return ''

  const isShort = props.direction === 'short'

  if (!isShort) {
    if (trigger > current) {
      return `做多时，触发价通常应低于当前价 (${current})，以便在下跌时接盘`
    } else {
      return `价格跌至 ${trigger} 时，将买入首仓`
    }
  } else {
    if (trigger < current) {
      return `做空时，触发价通常应高于当前价 (${current})，以便在上涨时做空`
    } else {
      return `价格涨至 ${trigger} 时，将卖出首仓`
    }
  }
})

const triggerPriceError = computed(() => {
  const tip = triggerPriceTip.value
  return tip.startsWith('做多时') || tip.startsWith('做空时')
})

const onGridCountChange = (val) => {
  const c = props.config?.grid
  if (!c) return
  const n = Math.max(1, Number(val || 0))
  const prev = Number(c.max_open_grids || 0)

  if (prev <= 0) {
    c.max_open_grids = n
  } else if (prev > n) {
    c.max_open_grids = n
  }
}

const applySuggest = async (days) => {
  if (!props.pair) {
    ElMessage.warning('请先选择交易对')
    return
  }
  loadingSuggest.value = days
  try {
    const { data } = await axios.get(`${API}/chart/grid/suggest`, {
      params: { pair: props.pair, days }
    })

    if (!data || data.error) {
      ElMessage.warning('无法获取历史数据，请手动输入区间')
      return
    }

    props.config.grid.lower_price = data.lower_price
    props.config.grid.upper_price = data.upper_price

    if (!props.config.grid.grid_count || props.config.grid.grid_count <= 0) {
      props.config.grid.grid_count = data.suggest_grid_count || 20
    }
    if (!props.config.grid.max_open_grids || props.config.grid.max_open_grids <= 0) {
      props.config.grid.max_open_grids = props.config.grid.grid_count
    }

    currentPrice.value = data.current_price
    lastSuggestInfo.value = `当前价 ${data.current_price} | 近 ${days} 天 [${data.raw_low}, ${data.raw_high}]`

    if (Number(props.config.grid.max_open_grids) > Number(props.config.grid.grid_count)) {
      props.config.grid.max_open_grids = props.config.grid.grid_count
    }
    ElMessage.success(`已根据近 ${days} 天极值填入区间`)
  } catch (e) {
    console.error('[applySuggest] failed', e)
    ElMessage.error('获取建议区间失败')
  } finally {
    loadingSuggest.value = 0
  }
}

const initDefaultRange = async () => {
  const g = props.config?.grid || {}
  if (Number(g.lower_price) > 0 && Number(g.upper_price) > 0) return
  if (!props.pair) return

  try {
    const { data } = await axios.get(`${API}/chart/candles`, {
      params: { pair: props.pair, timeframe: '5m' }
    })
    if (!Array.isArray(data) || !data.length) return
    const price = Number(data[data.length - 1].close)
    if (!Number.isFinite(price) || price <= 0) return

    props.config.grid.lower_price = +(price * 0.9).toFixed(4)
    props.config.grid.upper_price = +(price * 1.1).toFixed(4)

    if (props.config.grid.start_mode === 'trigger' &&
        (!props.config.grid.trigger_price || props.config.grid.trigger_price <= 0)) {
      const isShort = props.direction === 'short'
      if (isShort) {
        props.config.grid.trigger_price = +(price * 1.02).toFixed(4)
      } else {
        props.config.grid.trigger_price = +(price * 0.98).toFixed(4)
      }
    }
    if (!props.config.grid.grid_count || props.config.grid.grid_count <= 0) {
      props.config.grid.grid_count = 20
    }
    if (!props.config.grid.max_open_grids || props.config.grid.max_open_grids <= 0) {
      props.config.grid.max_open_grids = props.config.grid.grid_count
    }
    currentPrice.value = price
    lastSuggestInfo.value = `默认区间 ±10%（当前价 ${price}）`
  } catch (e) {
    console.warn('[initDefaultRange] failed', e)
  }
}

onMounted(async () => {
  await initDefaultRange()
  if (props.pair && !currentPrice.value) {
    try {
      const { data } = await axios.get(`${API}/chart/candles`, {
        params: { pair: props.pair, timeframe: '5m' }
      })
      if (Array.isArray(data) && data.length) {
        currentPrice.value = Number(data[data.length - 1].close)
      }
    } catch (e) {
      console.warn('[onMounted] fetch current price failed', e)
    }
  }
})

// 1. 修改 gridPreview 的计算，加入利润与手续费的对比
const gridPreview = computed(() => {
  const c = props.config?.grid || {}
  const lower = Number(c.lower_price || 0)
  const upper = Number(c.upper_price || 0)
  const count = Number(c.grid_count || 0)
  if (lower <= 0 || upper <= 0 || count <= 0 || upper <= lower) return null

  const levels = []
  if (c.spacing_algo === 'geometric') {
    const ratio = Math.pow(upper / lower, 1 / count)
    for (let i = 0; i <= count; i++) levels.push(lower * Math.pow(ratio, i))
  } else {
    const step = (upper - lower) / count
    for (let i = 0; i <= count; i++) levels.push(lower + step * i)
  }

  const step0 = levels[1] - levels[0]
  const stepPct = (step0 / levels[0]) * 100
  const stepText = `${step0.toFixed(2)} (${stepPct.toFixed(2)}%)`

  const profitMinPct = (step0 / levels[1]) * 100
  const profitMaxPct = (step0 / levels[0]) * 100

  // 假设杠杆（从外部传入或默认，这里为了让组件独立，通过 props 获取，如果没有就用 1）
  const leverage = Number(props.leverage || 1)
  // 每格毛利（含杠杆）
  const profitUsdt = perGrid.value * leverage * (profitMinPct / 100)
  const profitText = `${profitUsdt.toFixed(2)} USDT (${profitMinPct.toFixed(2)}% ~ ${profitMaxPct.toFixed(2)}%)`

  const tooNarrow = stepPct < 0.2
  const total = (perGrid.value * count).toFixed(2)

  // 计算当前手续费成本
  const feeCost = perGrid.value * leverage * FEE_RATE

  const refPrice = currentPrice.value || (lower + upper) / 2
  let splitIdx = levels.findIndex(lv => lv >= refPrice)
  if (splitIdx === -1) splitIdx = count

  const formatLv = (lv) => lv.toFixed(2)

  let topLevels = []
  let bottomLevels = []
  let topLabel = ''
  let bottomLabel = ''

  if (props.direction === 'long') {
    topLevels = levels.slice(splitIdx).map(formatLv).reverse()
    bottomLevels = levels.slice(0, splitIdx).map(formatLv).reverse()
    topLabel = '🟢 减仓网格'
    bottomLabel = '🔴 加仓网格'
  } else {
    topLevels = levels.slice(splitIdx).map(formatLv).reverse()
    bottomLevels = levels.slice(0, splitIdx).map(formatLv).reverse()
    topLabel = '🔴 加仓网格'
    bottomLabel = '🟢 减仓网格'
  }

  return {
    stepText,
    profitText,
    totalText: total,
    topLevels,
    bottomLevels,
    topLabel,
    bottomLabel,
    refPriceText: refPrice.toFixed(2),
    tooNarrow,
    profitUsdt, // 返回毛利润
    feeCost,    // 返回手续费
  }
})

// 计算是否利润过薄，无法覆盖手续费
const isProfitTooLow = computed(() => {
  if (!gridPreview.value) return false
  const feeCost = gridPreview.value.feeCost
  const worstProfit = gridPreview.value.profitUsdt // 直接用预览算出来的每格毛利

  // 如果利润 <= 预估手续费，则提示
  return worstProfit <= feeCost
})
</script>

<style scoped>
.grid-panel {
  padding: 4px 0;
}

/* 统一的表单行间距 */
.form-row {
  display: flex;
  gap: 16px;
  margin-bottom: 16px; /* 稍微增加一点行间距，看起来不局促 */
}
.form-item-half {
  flex: 1;
  min-width: 0;
  margin-bottom: 0;
}
.form-item-full {
  flex: 1;
  min-width: 0;
  margin-bottom: 0;
}

/* ★ 数字输入框：设定最大宽度，不要铺满整个屏幕 */
.num-input {
  width: 100% !important;
  max-width: 200px !important;
}

/* ★ 下拉框：保留适当的宽度即可 */
.flex-input {
  width: 100% !important;
  max-width: 240px !important;
}

/* 分区样式 */
.section-block {
  margin-bottom: 24px; /* 区块之间留出更多呼吸感 */
}
.section-block:last-child {
  margin-bottom: 0;
}

.section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
  border-bottom: 1px solid var(--el-border-color-lighter);
  padding-bottom: 8px;
}
.section-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--el-text-color-primary);
}

/* 智能填入行 */
.smart-range-inline {
  display: flex;
  align-items: center;
  gap: 8px;
}
.smart-label {
  font-size: 12px;
  color: var(--el-text-color-secondary);
}
.current-price-tip {
  font-size: 12px;
  color: var(--el-text-color-placeholder);
  font-variant-numeric: tabular-nums;
  margin-left: 8px;
}

/* ★ 统一的行内图标布局 */
.input-with-icon {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
}

/* 带提示的输入框容器（保留用于触发价） */
.input-with-hint {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

/* 内联提示文字（保留用于触发价） */
.inline-hint {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  color: var(--el-text-color-secondary);
  line-height: 1.4;
}
.inline-hint.is-info {
  color: var(--el-color-primary);
}
.inline-hint.is-error {
  color: var(--el-color-danger);
  font-weight: 500;
}

/* 网格预览（折叠卡片） */
.grid-preview-wrapper {
  margin-top: 16px;
  background: var(--el-fill-color-extra-light);
  border-radius: 6px;
  border: 1px solid var(--el-border-color-lighter);
  overflow: hidden;
}

.grid-preview-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 12px;
  cursor: pointer;
  user-select: none;
  transition: background-color 0.2s;
}
.grid-preview-header:hover {
  background: var(--el-fill-color-light);
}

.grid-preview-title {
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 13px;
  font-weight: 600;
  color: var(--el-text-color-primary);
}

.grid-preview-stats-inline {
  font-size: 12px;
  font-weight: normal;
  color: var(--el-text-color-secondary);
}

.grid-preview-warn {
  color: var(--el-color-danger);
  font-size: 12px;
  display: inline-flex;
  align-items: center;
  gap: 2px;
}

.toggle-icon {
  transition: transform 0.3s;
  color: var(--el-text-color-secondary);
}
.toggle-icon.is-expanded {
  transform: rotate(180deg);
}

.grid-preview-content {
  padding: 0 12px 12px 12px;
  border-top: 1px dashed var(--el-border-color-lighter);
  padding-top: 12px;
}

.grid-preview__lines {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  font-size: 12px;
  font-family: monospace;
  color: var(--el-text-color-primary);
  margin-bottom: 12px;
}
.grid-preview__lines span {
  padding: 2px 6px;
  background: var(--el-bg-color);
  border-radius: 4px;
  border: 1px solid var(--el-border-color-lighter);
}

/* ★ 基础信息图标悬浮效果（统一） */
.section-label__info {
  color: var(--el-text-color-placeholder);
  font-size: 15px;
  cursor: help;
  transition: color 0.2s;
  margin-left: 2px;
}
.section-label__info:hover {
  color: var(--el-color-primary);
}

/* ★ 网格预览上下区域 */
.grid-preview-divider {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 12px 0;
}
.divider-line {
  flex: 1;
  height: 1px;
  background: var(--el-border-color);
}
.divider-text {
  font-size: 12px;
  font-weight: 600;
  color: var(--el-color-primary);
}

.grid-preview-section {
  margin-bottom: 12px;
}
.grid-preview-section-title {
  font-size: 12px;
  font-weight: 600;
  margin-bottom: 6px;
  color: var(--el-text-color-regular);
}
</style>