<template>
  <div class="grid-panel">
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
          <el-form-item label="网格下限价" class="form-item-half">
            <el-input-number v-model="config.grid.lower_price" :min="0" :step="100" controls-position="right" class="short-input" />
          </el-form-item>
          <el-form-item label="网格上限价" class="form-item-half">
            <el-input-number v-model="config.grid.upper_price" :min="0" :step="100" controls-position="right" class="short-input" />
          </el-form-item>
        </div>
      </div>

      <!-- ── 2. 网格参数 ── -->
      <div class="section-block">
        <div class="section-header">
          <div class="section-title">网格参数</div>
        </div>

        <div class="form-row">
          <el-form-item label="网格数量" class="form-item-half">
            <el-input-number v-model="config.grid.grid_count" :min="2" :max="200" :step="1" controls-position="right" class="short-input" @change="onGridCountChange" />
          </el-form-item>
          <el-form-item label="间距算法" class="form-item-half">
            <el-select v-model="config.grid.spacing_algo" class="short-input">
              <el-option label="等差" value="arithmetic" />
              <el-option label="等比" value="geometric" />
            </el-select>
          </el-form-item>
        </div>

        <div class="form-row">
          <el-form-item label="每格金额" class="form-item-half">
            <div class="input-with-hint">
              <el-input :model-value="perGridText" readonly class="short-input" />
              <div class="inline-hint">
                <el-icon class="section-label__info"><InfoFilled /></el-icon>
                投入资金 / 网格数量 = {{ capital }} / {{ config.grid.grid_count }} USDT
              </div>
            </div>
          </el-form-item>
          <el-form-item label="最多同时持仓格数" class="form-item-half">
            <div class="input-with-hint">
              <el-input-number v-model="config.grid.max_open_grids" :min="1" :max="config.grid.grid_count" :step="1" controls-position="right" class="short-input" />
              <div class="inline-hint">
                <el-icon class="section-label__info"><InfoFilled /></el-icon>
                默认 = 网格数量；调小可作风控
              </div>
            </div>
          </el-form-item>
        </div>
      </div>

      <!-- ── 3. 止损 ── -->
      <div class="section-block">
        <div class="section-header">
          <div class="section-title">止损</div>
        </div>
        <div class="form-row">
          <el-form-item label="跌破下沿止损" class="form-item-full">
            <div class="input-with-hint" style="flex-direction: row; align-items: center; gap: 12px;">
              <el-switch v-model="config.grid.stop_below_lower" />
              <span class="inline-hint">
                <el-icon class="section-label__info"><InfoFilled /></el-icon>
                价格跌破下沿时，清空所有持仓并停止机器人
              </span>
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
            <el-radio-group v-model="config.grid.start_mode">
              <el-radio-button value="grid">网格触发</el-radio-button>
              <el-radio-button value="trigger">触发价启动</el-radio-button>
              <el-radio-button value="immediate">立即启动</el-radio-button>
            </el-radio-group>
          </el-form-item>
        </div>

        <div class="form-row" v-if="config.grid.start_mode === 'trigger'">
          <el-form-item label="触发价格" class="form-item-full">
            <div class="input-with-hint" style="flex-direction: row; align-items: center; gap: 12px;">
              <el-input-number
                v-model="config.grid.trigger_price"
                :min="0" :step="10"
                controls-position="right"
                class="short-input"
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

        <div class="field-hint-block" v-if="config.grid.start_mode === 'grid'">
          <el-icon class="section-label__info"><InfoFilled /></el-icon>
          价格跌到最近的买格（多头）/ 涨到最近的卖格（空头）时，自动买入首仓
        </div>
        <div class="field-hint-block" v-else-if="config.grid.start_mode === 'trigger'">
          <el-icon class="section-label__info"><InfoFilled /></el-icon>
          价格跌破（多头）/ 突破（空头）触发价时，买入首仓并启动网格。
          <span class="text-warning">若机器人启动时价格已在触发价下方（多头）/ 上方（空头），需等价格重新穿越触发价才会开仓。</span>
        </div>
        <div class="field-hint-block" v-else>
          <el-icon class="section-label__info"><InfoFilled /></el-icon>
          机器人启动后，以当前价立即买入首仓
        </div>
      </div>

      <!-- ── 5. 网格预览（可折叠，放在启动模式下方） ── -->
      <div v-if="gridPreview" class="grid-preview-wrapper">
        <div class="grid-preview-header" @click="showGridPreview = !showGridPreview">
          <div class="grid-preview-title">
            <span>网格预览</span>
            <span class="grid-preview-stats-inline">
              格距 ≈ {{ gridPreview.stepText }} |
              每格利润 ≈ {{ gridPreview.profitText }} |
              总投入 ≈ {{ gridPreview.totalText }} USDT
            </span>
            <span v-if="gridPreview.tooNarrow" class="grid-preview-warn">
              <el-icon><WarningFilled /></el-icon> 格距过小
            </span>
          </div>
          <el-icon class="toggle-icon" :class="{ 'is-expanded': showGridPreview }">
            <ArrowDown />
          </el-icon>
        </div>

        <el-collapse-transition>
          <div v-show="showGridPreview" class="grid-preview-content">
            <div class="grid-preview__lines">
              <!-- 渲染全部网格线 -->
              <span v-for="(p, i) in gridPreview.allLevels" :key="i">
                {{ p }}
              </span>
            </div>
            <div class="grid-preview__tip">
              <el-icon class="section-label__info"><InfoFilled /></el-icon>
              网格逻辑：价格跌到某格，在该格买入；价格涨到该格上沿，卖出止盈
            </div>
          </div>
        </el-collapse-transition>
      </div>

    </el-form>
  </div>
</template>

<script setup>
import { computed, ref, watch, onMounted } from 'vue'
import axios from 'axios'
import { ElMessage } from 'element-plus'
import { InfoFilled, WarningFilled, ArrowDown } from '@element-plus/icons-vue'

const API = 'http://localhost:9000'

const props = defineProps({
  config: { type: Object, required: true },
  capital: { type: Number, default: 1000 },
  pair:    { type: String, default: '' },
  direction: { type: String, default: 'long' },
})

const loadingSuggest = ref(0)
const lastSuggestInfo = ref('')
const currentPrice = ref(null)
const showGridPreview = ref(false)  // 默认折叠

/** 每格金额 */
const perGrid = computed(() => {
  const c = props.config?.grid || {}
  const count = Math.max(1, Number(c.grid_count || 0))
  const cap = Number(props.capital || 0)
  return cap / count
})

const perGridText = computed(() => {
  const v = perGrid.value
  if (!Number.isFinite(v) || v <= 0) return '—'
  return `${v.toFixed(2)} USDT`
})

// ============================================================
// ★ 触发价智能提示与校验
// ============================================================
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

/** 网格数量变化 → 自动跟随最大持仓 */
const onGridCountChange = (val) => {
  const c = props.config?.grid
  if (!c) return
  const n = Math.max(1, Number(val || 0))
  if (
    c.max_open_grids == null ||
    c.max_open_grids === 0 ||
    c.max_open_grids > n
  ) {
    c.max_open_grids = n
  }
}

// ============================================================
// ★ 智能区间
// ============================================================
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

    ElMessage.success(`已根据近 ${days} 天极值填入区间`)
  } catch (e) {
    console.error('[applySuggest] failed', e)
    ElMessage.error('获取建议区间失败')
  } finally {
    loadingSuggest.value = 0
  }
}

// ============================================================
// ★ 默认值兜底
// ============================================================
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

    // ★ 修复：wait 改为 trigger
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

watch(
  () => props.pair,
  () => {
    const g = props.config?.grid || {}
    if (Number(g.lower_price) <= 0 || Number(g.upper_price) <= 0) {
      initDefaultRange()
    }
  }
)

// ============================================================
// 网格预览（完整列表）
// ============================================================
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
  const profitUsdt = perGrid.value * (profitMinPct / 100)

  const profitText = `${profitUsdt.toFixed(2)} USDT (${profitMinPct.toFixed(2)}% ~ ${profitMaxPct.toFixed(2)}%)`
  const tooNarrow = stepPct < 0.2
  const total = (perGrid.value * count).toFixed(2)

  // 显示全部网格
  const allLevels = levels.map(lv => lv.toFixed(2))

  return {
    stepText,
    profitText,
    totalText: total,
    allLevels,
    tooNarrow,
  }
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
  margin-bottom: 12px;
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

/* 限制输入框宽度 */
.short-input {
  width: 160px !important;
}

/* 分区样式 */
.section-block {
  margin-bottom: 20px;
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

/* 带提示的输入框容器 */
.input-with-hint {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

/* 内联提示文字 */
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

/* 独占一行的提示 */
.field-hint-block {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  color: var(--el-text-color-secondary);
  line-height: 1.4;
  margin-top: 6px;
}
.text-warning {
  color: var(--el-color-warning);
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

.grid-preview__tip {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  color: var(--el-text-color-placeholder);
  line-height: 1.4;
}

/* 基础信息图标 */
.section-label__info {
  color: var(--el-text-color-placeholder);
  font-size: 14px;
  cursor: help;
  transition: color 0.2s;
}
.section-label__info:hover {
  color: var(--el-color-primary);
}
</style>