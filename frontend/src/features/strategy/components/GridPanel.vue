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
        <el-col :span="8">
          <el-form-item label="网格数量">
            <el-input-number
              v-model="config.grid.grid_count"
              :min="2" :max="200" :step="1"
              controls-position="right"
              style="width: 100%"
            />
          </el-form-item>
        </el-col>
        <el-col :span="8">
          <el-form-item label="间距算法">
            <el-select v-model="config.grid.spacing_algo" style="width: 100%">
              <el-option label="等差" value="arithmetic" />
              <el-option label="等比" value="geometric" />
            </el-select>
          </el-form-item>
        </el-col>
        <el-col :span="8">
          <el-form-item label="每格金额(USDT)">
            <el-input-number
              v-model="config.grid.amount_per_grid"
              :min="1" :step="10"
              controls-position="right"
              style="width: 100%"
            />
          </el-form-item>
        </el-col>
      </el-row>

      <!-- 实时预览 -->
      <div v-if="gridPreview" class="grid-preview">
        <div class="grid-preview__title">网格预览</div>
        <div class="grid-preview__stats">
          <span>格距 ≈ {{ gridPreview.stepText }}</span>
          <span>总投入 ≈ {{ gridPreview.totalText }} USDT</span>
        </div>
        <div class="grid-preview__lines">
          <span v-for="(p, i) in gridPreview.sampleLevels" :key="i">
            {{ p }}
          </span>
          <span v-if="gridPreview.more">…</span>
        </div>
      </div>

      <el-divider content-position="left">止盈 / 止损</el-divider>
      <el-row :gutter="12">
        <el-col :span="12">
          <el-form-item label="每格止盈(%)">
            <el-input-number
              v-model="config.grid.tp_per_grid_pct"
              :min="0.1" :max="5" :step="0.1" :precision="2"
              controls-position="right"
              style="width: 100%"
            />
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="跌破下沿止损">
            <el-switch v-model="config.grid.stop_below_lower" />
          </el-form-item>
        </el-col>
      </el-row>

      <div class="field-hint" style="margin: -6px 0 12px 140px">
        每格止盈需覆盖双边手续费 + 滑点，建议 ≥ 0.3%
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
  config: { type: Object, required: true }
})

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
  const stepText = step0.toFixed(4)
  const total = (Number(c.amount_per_grid || 0) * count).toFixed(2)

  const sample = []
  const maxShow = 6
  for (let i = 0; i < Math.min(levels.length, maxShow); i++) {
    sample.push(levels[i].toFixed(4))
  }
  return {
    stepText: `${stepText} (${((step0 / lower) * 100).toFixed(2)}%)`,
    totalText: total,
    sampleLevels: sample,
    more: levels.length > maxShow
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
}
.grid-preview__stats {
  display: flex;
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
}
.grid-preview__lines span {
  padding: 1px 6px;
  background: var(--el-bg-color);
  border-radius: 4px;
  border: 1px solid var(--el-border-color-lighter);
}
.field-hint {
  font-size: 12px;
  color: var(--el-text-color-secondary);
  line-height: 1.4;
}
</style>