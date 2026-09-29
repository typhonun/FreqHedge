<template>
  <el-card class="account-card">
    <template #header>
      <div class="card-header">
        <h2>账户总览</h2>

        <!-- 新增下拉框 -->
        <el-select
          v-model="selected"
          size="small"
          style="width: 180px"
          @change="handleChange"
        >
          <el-option label="总资金" value="__total__" />
          <el-option
            v-for="bot in botList"
            :key="bot.id"
            :label="bot.name"
            :value="bot.id"
          />
        </el-select>
      </div>
    </template>

    <el-row :gutter="20">
      <el-col :span="6">
        <div class="stat-item">
          <div class="label">总资金</div>
          <div class="value">
            {{ format(summary.total_balance) }}
          </div>
        </div>
      </el-col>

      <el-col :span="6">
        <div class="stat-item">
          <div class="label">可用资金</div>
          <div class="value">
            {{ format(summary.available_balance) }}
          </div>
        </div>
      </el-col>

      <el-col :span="6">
        <div class="stat-item">
          <div class="label">持仓保证金</div>
          <div class="value">
            {{ format(summary.used_margin) }}
          </div>
        </div>
      </el-col>

      <el-col :span="6">
        <div class="stat-item">
          <div class="label">未实现盈亏</div>
          <div
            class="value"
            :class="floating.total_float >= 0 ? 'profit' : 'loss'"
          >
            {{ format(floating.total_float) }}
          </div>
        </div>
      </el-col>
    </el-row>

    <div class="curve-title">
      实时权益曲线（Equity）
    </div>

    <BalanceCurve
      :data="balanceCurve"
    />
  </el-card>
</template>

<script setup>
import { ref, watch } from 'vue'
import BalanceCurve from './BalanceCurve.vue'

const props = defineProps({
  summary: {
    type: Object,
    default: () => ({})
  },
  floating: {
    type: Object,
    default: () => ({})
  },
  balanceCurve: { type: Array, default: () => [] },
  // 新增：机器人列表
  botList: { type: Array, default: () => [] },
  // 新增：当前选中值（受控，可选）
  modelValue: { type: [String, Number], default: '__total__' }
})

const emit = defineEmits(['update:modelValue', 'change'])

const selected = ref(props.modelValue)

watch(() => props.modelValue, v => { selected.value = v })

const handleChange = (val) => {
  emit('update:modelValue', val)
  emit('change', val)   // 父组件监听这个事件去拉数据
}

const format = (value) => Number(value || 0).toFixed(2)
</script>

<style scoped>
.stat-item {
  display: flex;
  flex-direction: column;
}

.label {
  color: #909399;
  font-size: 14px;
}

.value {
  margin-top: 8px;
  font-size: 24px;
  font-weight: 700;
}

.profit {
  color: #67c23a;
}

.loss {
  color: #f56c6c;
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
</style>