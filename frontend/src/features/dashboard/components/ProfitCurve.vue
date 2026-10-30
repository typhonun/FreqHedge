<template>
  <el-card>
    <template #header>
      <div class="header">
        <h2>收益曲线</h2>

        <div class="header-right">
          <div class="toolbar">
            <span
              v-for="p in ['1D', '7D', '30D', '90D', 'ALL']"
              :key="p"
              class="period-btn"
              :class="{ active: period === p }"
              @click="handlePeriodChange(p)"
            >
              {{ p === 'ALL' ? '全部' : p }}
            </span>
          </div>

          <el-select
            v-model="selected"
            size="small"
            style="width: 180px"
            @change="handleChange"
          >
            <el-option label="总收益" value="__total__" />
            <el-option
              v-for="bot in botList"
              :key="bot.id"
              :label="bot.name"
              :value="bot.id"
            />
          </el-select>
        </div>
      </div>
    </template>

    <VChart
      ref="chartRef"
      class="chart"
      :option="option"
      autoresize
    />
  </el-card>
</template>

<script setup>
import { computed, ref, watch, onMounted } from "vue"
import VChart from "vue-echarts"

const props = defineProps({
  data: { type: Array, default: () => [] },
  botList: { type: Array, default: () => [] },
  modelValue: { type: [String, Number], default: '__total__' },
  modelPeriod: { type: String, default: 'ALL' }   // 新增，和 BalanceCurve 对齐
})

const emit = defineEmits(['update:modelValue', 'change', 'periodChange'])

const selected = ref(props.modelValue)
const period = ref(props.modelPeriod)

watch(() => props.modelValue, (v) => {
  if (v !== selected.value) {
    selected.value = v
  }
})

const chartRef = ref(null)
const zoomStart = ref(0)
const zoomEnd = ref(100)

const handleChange = (val) => {
  emit('update:modelValue', val)
  emit('change', val)
}

const handlePeriodChange = (p) => {
  if (period.value === p) return
  period.value = p
  zoomStart.value = 0
  zoomEnd.value = 100
  emit('periodChange', p)   // 父组件监听去重新拉数据（若按 period 请求）
}

// =========================================================
// 核心：时间处理 + 补全 + 按 period 过滤
// 返回 [{ time, displayTime, profit }]
// =========================================================
const processedData = computed(() => {
  const raw = [...(props.data || [])].sort((a, b) => a.time - b.time)
  if (raw.length === 0) return []

  // 通用：时间戳(秒) -> 显示串
  const fmtTime = (ts) => {
    const d = new Date(ts * 1000)
    const MM = (d.getMonth() + 1).toString().padStart(2, '0')
    const DD = d.getDate().toString().padStart(2, '0')
    const hh = d.getHours().toString().padStart(2, '0')
    const mm = d.getMinutes().toString().padStart(2, '0')
    // 1D 用时分，多天用 月-日 时:分
    return period.value === '1D'
      ? `${hh}:${mm}`
      : `${MM}-${DD} ${hh}:${mm}`
  }

  // ---- 1D：只取最近 24h（无数据就返回空，不拿旧数据充数）----
  if (period.value === '1D') {
    const now = Date.now() / 1000
    const from = now - 24 * 3600
    return raw
      .filter(it => it.time >= from)
      .map(it => ({
        time: it.time,
        displayTime: fmtTime(it.time),
        profit: Number(it.total_profit || 0)
      }))
  }

  // ---- ALL：原样返回（交给 dataZoom），标签带日期 ----
  if (period.value === 'ALL') {
    return raw.map(it => ({
      time: it.time,
      displayTime: fmtTime(it.time),
      profit: Number(it.total_profit || 0)
    }))
  }

  // ---- 7D / 30D / 90D：按天补全 ----
  const daysCount = { '7D': 7, '30D': 30, '90D': 90 }[period.value] || 7

  // 按天分组，取每天最后一个点
  const dayMap = {}
  raw.forEach(it => {
    const d = new Date(it.time * 1000)
    const key = `${d.getFullYear()}-${d.getMonth() + 1}-${d.getDate()}`
    dayMap[key] = it
  })

  const result = []
  const now = new Date()
  let lastProfit = 0
  // 初始化 lastProfit 为窗口起点之前的最后一个点（如果有）
  for (let i = daysCount - 1; i >= 0; i--) {
    const d = new Date()
    d.setDate(now.getDate() - i)
    const key = `${d.getFullYear()}-${d.getMonth() + 1}-${d.getDate()}`
    const tsSec = d.getTime() / 1000

    const hit = dayMap[key]
    if (hit) {
      lastProfit = Number(hit.total_profit || 0)
      result.push({ time: hit.time, displayTime: fmtTime(hit.time), profit: lastProfit })
    } else {
      result.push({ time: tsSec, displayTime: fmtTime(tsSec), profit: lastProfit })
    }
  }
  return result
})

// 当前收益（最后一个点）用于线色
const currentProfit = computed(() => {
  const arr = processedData.value
  return arr.length ? arr[arr.length - 1].profit : 0
})

const lineColor = computed(() =>
  currentProfit.value >= 0 ? "#16c784" : "#ea3943"
)

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
        return `时间：${item.displayTime}<br/>累计收益：${Number(item.profit).toFixed(2)}`
      }
    },
    grid: { left: 40, right: 20, top: 20, bottom: 50, containLabel: true },
    xAxis: {
      type: "category",
      boundaryGap: false,
      data: processedData.value.map(i => i.displayTime),
      axisLabel: {
        hideOverlap: true,      // 只留这一行，interval 删掉
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
      nameTextStyle: { align: "right", verticalAlign: "bottom", padding: [0, 0, 6, 0] },
      axisLabel: {
        formatter: (v) => {
          const n = Number(v)
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
        filterMode: "filter",
        zoomOnMouseWheel: true,
        moveOnMouseMove: true,
        moveOnMouseWheel: true,
        start: zoomStart.value,
        end: zoomEnd.value
      }
    ],
    series: [
      {
        type: "line",
        smooth: period.value !== '1D',
        symbol: "none",
        sampling: "lttb",
        lineStyle: { width: 3, color: lineColor.value },
        areaStyle: {
          color: {
            type: "linear",
            x: 0, y: 0, x2: 0, y2: 1,
            colorStops: [
              { offset: 0, color: lineColor.value },
              { offset: 1, color: "rgba(0,0,0,0)" }
            ]
          }
        },
        data: processedData.value.map(i => i.profit)
      }
    ]
  }
})

onMounted(() => {
  const chart = chartRef.value?.chart
  if (!chart) return
  chart.on("datazoom", (params) => {
    const batch = params.batch?.[0] || params
    zoomStart.value = batch.start
    zoomEnd.value = batch.end
  })
})
</script>

<style scoped>
.chart { height: 400px; width: 100%; }
.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
}
.header-right {
  display: flex;
  align-items: center;
  gap: 16px;
}
.toolbar {
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