<template>
  <el-card>
    <template #header>
      <h2>资金分布</h2>
    </template>

    <VChart
      class="chart"
      :option="option"
      autoresize
    />
  </el-card>
</template>

<script setup>
import { computed } from 'vue'
import VChart from 'vue-echarts'

const props = defineProps({
  summary: {
    type: Object,
    default: () => ({})
  }
})

const total = computed(
  () => Number(props.summary.total_balance || 0)
)

const longMargin = computed(
  () => Number(
    props.summary.long_margin || 0
  )
)

const shortMargin = computed(
  () => Number(
    props.summary.short_margin || 0
  )
)

const usedMargin = computed(
  () => Number(props.summary.used_margin || 0)
)

const availableBalance = computed(
  () => Number(
    props.summary.available_balance || 0
  )
)

const longPercent = computed(
  () =>
    total.value
      ? (
          longMargin.value
          /
          total.value
          *
          100
        ).toFixed(1)
      : 0
)

const shortPercent = computed(
  () =>
    total.value
      ? (
          shortMargin.value
          /
          total.value
          *
          100
        ).toFixed(1)
      : 0
)

const availablePercent = computed(
  () =>
    total.value
      ? (
          availableBalance.value
          /
          total.value
          *
          100
        ).toFixed(1)
      : 0
)

const option = computed(() => ({
  color: [
    '#00C087',
    '#F6465D',
    '#3B82F6'
  ],

  tooltip: {
    trigger: 'item'
  },

  legend: {
    bottom: 0
  },

  series: [
    {
      type: 'pie',
      radius: ['50%', '75%'],

      label: {
        formatter: '{b}\n{d}%'
      },

      data: [
        {
          value: longMargin.value,
          name: '多头仓位'
        },
        {
          value: shortMargin.value,
          name: '空头仓位'
        },
        {
          value: availableBalance.value,
          name: '可用资金'
        }
      ]
    }
  ]
}))
</script>

<style scoped>
.chart {
  height: 260px;
}

.legend {
  display: flex;
  justify-content: space-between;
  margin-top: 16px;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 8px;
}

.dot {
  width: 12px;
  height: 12px;
  border-radius: 50%;
}

.long .dot {
  background: #00C087;
}

.short .dot {
  background: #F6465D;
}

.cash .dot {
  background: #3B82F6;
}

.legend-item b {
  font-size: 18px;
}
</style>