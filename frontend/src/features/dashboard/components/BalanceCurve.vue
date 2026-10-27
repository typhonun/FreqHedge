<template>
  <div class="chart-wrapper">
    <div class="toolbar">
      <span
        v-for="p in ['1D', '7D', '30D', '90D']"
        :key="p"
        class="period-btn"
        :class="{ active: period === p }"
        @click="handlePeriodChange(p)"
      >
        {{ p }}
      </span>
    </div>

    <VChart
      ref="chartRef"
      class="chart"
      :option="option"
      autoresize
    />
  </div>
</template>

<script setup>
import { computed, ref, onMounted } from "vue"
import VChart from "vue-echarts"

const props = defineProps({
  data: {
    type: Array,
    default: () => []
  },
  modelPeriod: {
    type: String,
    default: '1D'
  }
})

const emit = defineEmits(['change'])

const zoomStart = ref(0)
const zoomEnd = ref(100)
const period = ref(props.modelPeriod)

const chartRef = ref(null)

const handlePeriodChange = (p) => {
  if (period.value === p) return
  period.value = p
  zoomStart.value = 0
  zoomEnd.value = 100
  emit('change', p)
}

// =========================================================
// 核心：处理时间轴，补全缺失的日期
// =========================================================
const processedData = computed(() => {
  if (!props.data || props.data.length === 0) return []

  const rawData = [...props.data].sort((a, b) => a.time - b.time)

  // 如果是 1D，保持原样，不做按天补全
  if (period.value === '1D') {
    return rawData.map(item => ({
      time: item.time,
      displayTime: new Date(item.time * 1000).toLocaleTimeString("zh-CN", { hour: '2-digit', minute: '2-digit', hour12: false }),
      balance: Number(item.balance),
      profit: Number(item.profit || 0),
      wallet: Number(item.wallet || 0)
    }))
  }

  // 对于 7D, 30D, 90D，需要补全日期
  const daysMap = {}

  // 1. 按天归类已有数据
  rawData.forEach(item => {
    const d = new Date(item.time * 1000)
    const dateStr = `${d.getFullYear()}-${(d.getMonth() + 1).toString().padStart(2, '0')}-${d.getDate().toString().padStart(2, '0')}`
    if (!daysMap[dateStr]) daysMap[dateStr] = []
    daysMap[dateStr].push(item)
  })

  // 2. 计算需要补全的日期范围
  const daysCount = { '7D': 7, '30D': 30, '90D': 90 }[period.value] || 7
  const result = []
  const now = new Date()

  // 获取基准金额（如果有历史数据，用第一条的余额，否则用0）
  let lastKnownBalance = rawData.length > 0 ? Number(rawData[0].balance) : 0
  let lastKnownWallet = rawData.length > 0 ? Number(rawData[0].wallet) : 0

  // 倒推生成日期序列
  for (let i = daysCount - 1; i >= 0; i--) {
    const d = new Date()
    d.setDate(now.getDate() - i)
    const dateStr = `${d.getFullYear()}-${(d.getMonth() + 1).toString().padStart(2, '0')}-${d.getDate().toString().padStart(2, '0')}`
    const displayTime = `${(d.getMonth() + 1).toString().padStart(2, '0')}-${d.getDate().toString().padStart(2, '0')}`

    if (daysMap[dateStr]) {
      // 这天有数据，取当天的最后一条
      const dayData = daysMap[dateStr][daysMap[dateStr].length - 1]
      lastKnownBalance = Number(dayData.balance)
      lastKnownWallet = Number(dayData.wallet || 0)

      result.push({
        time: dayData.time,
        displayTime,
        balance: lastKnownBalance,
        profit: Number(dayData.profit || 0),
        wallet: lastKnownWallet
      })
    } else {
      // 这天没有数据，用上一次已知的余额补齐，盈亏为0
      result.push({
        time: d.getTime() / 1000,
        displayTime,
        balance: lastKnownBalance,
        profit: 0,
        wallet: lastKnownWallet
      })
    }
  }

  return result
})

// =========================================================
// Y轴范围计算
// =========================================================
const _niceMin = (v) => {
  if (!Number.isFinite(v)) return 0
  const abs = Math.abs(v)
  let step = abs >= 1000 ? 1 : abs >= 100 ? 0.1 : abs >= 10 ? 0.01 : abs >= 1 ? 0.001 : 0.0001
  return Math.floor(v / step) * step
}

const _niceMax = (v) => {
  if (!Number.isFinite(v)) return 100
  const abs = Math.abs(v)
  let step = abs >= 1000 ? 1 : abs >= 100 ? 0.1 : abs >= 10 ? 0.01 : abs >= 1 ? 0.001 : 0.0001
  return Math.ceil(v / step) * step
}

const yAxisRange = computed(() => {
  if (!processedData.value.length) return { min: 0, max: 100 }

  const values = processedData.value
    .map(item => item.balance)
    .filter(v => Number.isFinite(v))

  if (!values.length) return { min: 0, max: 100 }

  const min = Math.min(...values)
  const max = Math.max(...values)

  if (min === max) {
    const padding = Math.max(Math.abs(min) * 0.001, 1)
    return {
      min: _niceMin(Math.max(0, min - padding)),
      max: _niceMax(max + padding)
    }
  }

  const range = max - min
  const padding = range * 0.2

  return {
    min: _niceMin(Math.max(0, min - padding)),
    max: _niceMax(max + padding)
  }
})

// =========================================================
// ECharts Option
// =========================================================
const option = computed(() => {
  const dataLength = processedData.value.length
  const interval = dataLength > 10 ? Math.floor(dataLength / 7) : 0

  return {
    tooltip: {
      trigger: "axis",
      formatter(params) {
        if (!params.length) return ""
        const item = processedData.value[params[0].dataIndex]
        if (!item) return ""

        let timeStr = period.value === '1D'
          ? new Date(item.time * 1000).toLocaleString("zh-CN", { hour12: false })
          : item.displayTime

        return `
          时间：${timeStr}<br/>
          实时资金：${Number(item.balance).toFixed(2)}<br/>
          账户余额：${Number(item.wallet).toFixed(2)}<br/>
          累计收益：${Number(item.profit).toFixed(2)}
        `
      }
    },
    grid: {
      left: 20,
      right: 20,
      top: 40,
      bottom: 20,
      containLabel: true
    },
    xAxis: {
      type: "category",
      boundaryGap: false,
      data: processedData.value.map(item => item.displayTime),
      axisLabel: {
        hideOverlap: true,
        interval: interval,
        rotate: 0,
        margin: 10
      }
    },
    yAxis: {
      type: "value",
      scale: true,
      name: "USDT",
      nameLocation: "end",
      nameGap: 12,
      nameTextStyle: {
        align: "right",
        verticalAlign: "bottom",
        padding: [0, 0, 6, 0]
      },
      min: yAxisRange.value.min,
      max: yAxisRange.value.max,
      axisLabel: {
        formatter: (value) => {
          const n = Number(value)
          if (!Number.isFinite(n)) return ""
          if (Math.abs(n) >= 100) return n.toFixed(0)
          if (Math.abs(n) >= 1) return n.toFixed(2)
          return n.toFixed(4)
        }
      }
    },
    dataZoom: [
      {
        type: "inside",
        xAxisIndex: 0,
        filterMode: "none",
        zoomOnMouseWheel: true,
        moveOnMouseMove: true,
        moveOnMouseWheel: true
      }
    ],
    series: [
      {
        type: "line",
        // ★ 核心修改：1D 时为 false (直角折线)，其他周期平滑
        smooth: period.value !== '1D',
        symbol: "none",
        sampling: "lttb",
        lineStyle: {
          color: "#E6A23C",
          width: 3
        },
        areaStyle: {
          color: {
            type: "linear",
            x: 0, y: 0, x2: 0, y2: 1,
            colorStops: [
              { offset: 0, color: "rgba(230,162,60,0.45)" },
              { offset: 1, color: "rgba(230,162,60,0.02)" }
            ]
          }
        },
        data: processedData.value.map(item => item.balance)
      }
    ]
  }
})

onMounted(() => {
  const chart = chartRef.value?.chart
  if (!chart) return

  chart.on("datazoom", params => {
    const batch = params.batch?.[0]
    if (!batch) return
    zoomStart.value = batch.start
    zoomEnd.value = batch.end
  })
})
</script>

<style scoped>
/* 样式保持不变 */
.chart {
  height: 320px;
  width: 100%;
}
.chart-wrapper {
  position: relative;
}
.toolbar {
  position: absolute;
  top: 5px;
  right: 10px;
  z-index: 10;
  display: flex;
  gap: 8px;
}
.period-btn {
  cursor: pointer;
  padding: 2px 8px;
  font-size: 12px;
  color: #909399;
}
.period-btn.active {
  color: #409EFF;
  font-weight: 600;
}
</style>