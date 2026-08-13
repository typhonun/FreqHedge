<template>
  <el-card class="account-card">
    <template #header>
      <h2>账户总览</h2>
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
  </el-card>
</template>

<script setup>
const props = defineProps({
  summary: {
    type: Object,
    default: () => ({})
  },
  floating: {
    type: Object,
    default: () => ({})
  }
})

const format = (value) => {
  return Number(value || 0).toFixed(2)
}
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
</style>