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

  if (period.value === '1D') {
    return rawData.map(item => ({
      time: item.time,
      displayTime: new Date(item.time * 1000).toLocaleTimeString("zh-CN", { hour: '2-digit', minute: '2-digit', hour12: false }),
      balance: Number(item.balance),
      profit: Number(item.profit || 0),
      wallet: Number(item.wallet || 0)
    }))
  }

  const daysMap = {}
  rawData.forEach(item => {
    const d = new Date(item.time * 1000)
    const dateStr = `${d.getFullYear()}-${(d.getMonth() + 1).toString().padStart(2, '0')}-${d.getDate().toString().padStart(2, '0')}`
    if (!daysMap[dateStr]) daysMap[dateStr] = []
    daysMap[dateStr].push(item)
  })

  const daysCount = { '7D': 7, '30D': 30, '90D': 90 }[period.value] || 7
  const result = []
  const now = new Date()

  let lastKnownBalance = rawData.length > 0 ? Number(rawData[0].balance) : 0
  let lastKnownWallet = rawData.length > 0 ? Number(rawData[0].wallet) : 0

  for (let i = daysCount - 1; i >= 0; i--) {
    const d = new Date()
    d.setDate(now.getDate() - i)
    const dateStr = `${d.getFullYear()}-${(d.getMonth() + 1).toString().padStart(2, '0')}-${d.getDate().toString().padStart(2, '0')}`
    const displayTime = `${(d.getMonth() + 1).toString().padStart(2, '0')}-${d.getDate().toString().padStart(2, '0')}`

    if (daysMap[dateStr]) {
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
// ECharts Option (移除了强制指定的 Y 轴 Range)
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
      // 允许 Y 轴不从 0 开始，自适应数据
      scale: true,
      // 上下留白 10%，防止曲线贴顶或贴底
      boundaryGap: ['10%', '10%'],
      name: "USDT",
      nameLocation: "end",
      nameGap: 12,
      nameTextStyle: {
        align: "right",
        verticalAlign: "bottom",
        padding: [0, 0, 6, 0]
      },
      // 移除 min 和 max，让 ECharts 自动根据当前渲染的数据计算
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
        // ★ 关键修改：改为 filter，当 X 轴缩放/拖拽时，Y 轴只计算当前可见区域的数据
        filterMode: "filter",
        zoomOnMouseWheel: true,
        moveOnMouseMove: true,
        moveOnMouseWheel: true
      }
    ],
    series: [
      {
        type: "line",
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