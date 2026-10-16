<template>
  <div class="grid-panel">
    <el-form label-width="140px" size="small">

      <el-divider content-position="left">价格区间</el-divider>
      <el-row :gutter="12">
        <el-col :span="12">
          <el-form-item label="网格下限价">
            <el-input-number
              v-model="config.grid.lower_price"
              :min="0" :step="100"
              controls-position="right"
              style="width: 100%"
            />
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="网格上限价">
            <el-input-number
              v-model="config.grid.upper_price"
              :min="0" :step="100"
              controls-position="right"
              style="width: 100%"
            />
          </el-form-item>
        </el-col>
      </el-row>

      <div class="field-hint" style="margin: -6px 0 12px 140px">
        当前价需落在 [下沿, 上沿] 之间才会触发网格开仓
      </div>

      <el-divider content-position="left">网格参数</el-divider>
      <el-row :gutter="12">
        <el-col :span="12">
          <el-form-item label="网格数量">
            <el-input-number
              v-model="config.grid.grid_count"
              :min="2" :max="200" :step="1"
              controls-position="right"
              style="width: 100%"
              @change="onGridCountChange"
            />
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="间距算法">
            <el-select v-model="config.grid.spacing_algo" style="width: 100%">
              <el-option label="等差" value="arithmetic" />
              <el-option label="等比" value="geometric" />
            </el-select>
          </el-form-item>
        </el-col>
      </el-row>

      <el-row :gutter="12">
        <el-col :span="12">
          <el-form-item label="每格金额">
            <el-input
              :model-value="perGridText"
              readonly
              style="width: 100%"
            />
            <span class="field-hint" style="margin-top: 4px">
              投入资金 / 网格数量 = {{ capital }} / {{ config.grid.grid_count }} USDT
            </span>
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="最多同时持仓格数">
            <el-input-number
              v-model="config.grid.max_open_grids"
              :min="1" :max="config.grid.grid_count" :step="1"
              controls-position="right"
              style="width: 100%"
            />
            <span class="field-hint" style="margin-top: 4px">
              默认 = 网格数量；调小可作风控，但可能卡住网格
            </span>
          </el-form-item>
        </el-col>
      </el-row>

      <!-- ★ 实时预览：显示格距、每格利润、买卖点 -->
      <div v-if="gridPreview" class="grid-preview">
        <div class="grid-preview__title">
          网格预览
          <span
            v-if="gridPreview.tooNarrow"
            class="grid-preview__warn"
          >
            ⚠ 格距过小，可能无法覆盖手续费
          </span>
        </div>

        <div class="grid-preview__stats">
          <span>格距 ≈ {{ gridPreview.stepText }}</span>
          <span>每格利润 ≈ {{ gridPreview.profitText }}</span>
          <span>总投入 ≈ {{ gridPreview.totalText }} USDT</span>
        </div>

        <div class="grid-preview__lines">
          <span v-for="(p, i) in gridPreview.sampleLevels" :key="i">
            {{ p }}
          </span>
          <span v-if="gridPreview.more">…</span>
        </div>

        <div class="grid-preview__tip">
          网格逻辑：价格跌到某格，在该格买入；价格涨到该格上沿，卖出止盈
        </div>
      </div>

      <el-divider content-position="left">止损</el-divider>
      <el-row :gutter="12">
        <el-col :span="12">
          <el-form-item label="跌破下沿止损">
            <el-switch v-model="config.grid.stop_below_lower" />
          </el-form-item>
        </el-col>
      </el-row>

      <div class="field-hint" style="margin: -6px 0 12px 140px">
        价格跌破下沿时，清空所有持仓并停止机器人
      </div>

      <el-divider content-position="left">启动模式</el-divider>
      <el-row :gutter="12">
        <el-col :span="12">
          <el-form-item label="启动模式">
            <el-select v-model="config.grid.start_mode" style="width: 100%">
              <el-option label="等价格进入区间" value="wait" />
              <el-option label="立即启动" value="immediate" />
            </el-select>
          </el-form-item>
        </el-col>
      </el-row>
    </el-form>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  config: { type: Object, required: true },
  capital: { type: Number, default: 1000 },
})

/** 每格金额 = 投入资金 / 网格数量 */
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

/** 网格数量变化 → 若 max_open_grids 未手动调小，自动跟随 grid_count */
const onGridCountChange = (val) => {
  const c = props.config?.grid
  if (!c) return
  const n = Math.max(1, Number(val || 0))
  // 只有当 max_open_grids 缺失或等于原 grid_count 时才自动跟随
  if (
    c.max_open_grids == null ||
    c.max_open_grids === 0 ||
    c.max_open_grids > n
  ) {
    c.max_open_grids = n
  }
}

/** 网格预览：格距、每格利润、采样格线 */
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

  // 格距（按第 0 格算，等比时后面格距会递增）
  const step0 = levels[1] - levels[0]
  const stepPct = (step0 / levels[0]) * 100
  const stepText = `${step0.toFixed(2)} (${stepPct.toFixed(2)}%)`

  // ★ 每格利润估算：买入价取该格上沿（略低），卖出价 = 该格上沿
  //   利润 ≈ step0 × qty
  //   利润率 ≈ step0 / entry
  //   保守取 entry = levels[i]，即该格下沿
  //   利润率 ≈ step0 / levels[i] × 100
  //   真实利润率随 entry 在格内的位置浮动，这里给一个范围
  //   最保守：entry = 上沿 → 利润率 = step0 / 上沿
  //   最乐观：entry = 下沿 → 利润率 = step0 / 下沿
  const profitMinPct = (step0 / levels[1]) * 100
  const profitMaxPct = (step0 / levels[0]) * 100
  const profitUsdt = perGrid.value * (profitMinPct / 100)   // 保守估算

  const profitText = `${profitUsdt.toFixed(2)} USDT (${profitMinPct.toFixed(2)}% ~ ${profitMaxPct.toFixed(2)}%)`

  // 格距过小警告（默认 0.2% 阈值，可调）
  const tooNarrow = stepPct < 0.2

  const total = (perGrid.value * count).toFixed(2)

  const sample = []
  const maxShow = 6
  for (let i = 0; i < Math.min(levels.length, maxShow); i++) {
    sample.push(levels[i].toFixed(2))
  }

  return {
    stepText,
    profitText,
    totalText: total,
    sampleLevels: sample,
    more: levels.length > maxShow,
    tooNarrow,
  }
})
</script>

<style scoped>
.grid-panel {
  padding: 4px 0;
}

.grid-preview {
  margin: 8px 0 16px 140px;
  padding: 10px 12px;
  background: var(--el-fill-color-extra-light);
  border-radius: 6px;
}
.grid-preview__title {
  font-size: 13px;
  font-weight: 600;
  margin-bottom: 6px;
  display: flex;
  align-items: center;
  gap: 8px;
}
.grid-preview__warn {
  color: var(--el-color-danger);
  font-weight: 400;
  font-size: 12px;
}
.grid-preview__stats {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
  font-size: 12px;
  color: var(--el-text-color-secondary);
  margin-bottom: 6px;
}
.grid-preview__lines {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  font-size: 12px;
  font-family: monospace;
  color: var(--el-text-color-primary);
  margin-bottom: 6px;
}
.grid-preview__lines span {
  padding: 1px 6px;
  background: var(--el-bg-color);
  border-radius: 4px;
  border: 1px solid var(--el-border-color-lighter);
}
.grid-preview__tip {
  font-size: 12px;
  color: var(--el-text-color-placeholder);
  line-height: 1.4;
  border-top: 1px dashed var(--el-border-color-lighter);
  padding-top: 6px;
}
.field-hint {
  font-size: 12px;
  color: var(--el-text-color-secondary);
  line-height: 1.4;
}
</style>