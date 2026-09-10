<template>

  <div class="chart-wrapper">

    <div class="toolbar">

      <span
        class="period-btn"
        :class="{ active: period === '1D' }"
        @click="period='1D'"
      >
        1D
      </span>

      <span
        class="period-btn"
        :class="{ active: period === '7D' }"
        @click="period='7D'"
      >
        7D
      </span>

      <span
        class="period-btn"
        :class="{ active: period === '30D' }"
        @click="period='30D'"
      >
        30D
      </span>

      <span
        class="period-btn"
        :class="{ active: period === '90D' }"
        @click="period='90D'"
      >
        90D
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

import {
  computed,
  ref
} from "vue"

import VChart from "vue-echarts"
import {
  watch,
  nextTick
} from "vue"

const zoomStart = ref(70)
const zoomEnd = ref(100)
const period = ref("1D")

const props = defineProps({

  data: {
    type: Array,
    default: () => []
  }

})

const chartRef = ref(null)


// =========================================================
// Y轴默认范围
// =========================================================

const yAxisRange = computed(() => {

  if (!visibleData.value.length) {

    return {
      min: 0,
      max: 100
    }

  }

  const values = visibleData.value

    .map(
      item => Number(item.balance)
    )

    .filter(
      v => Number.isFinite(v)
    )


  if (!values.length) {

    return {
      min: 0,
      max: 100
    }

  }


  const min =
    Math.min(...values)

  const max =
    Math.max(...values)


  // 没有波动

  if (min === max) {

    const padding =
      Math.max(
        Math.abs(min) * 0.001,
        1
      )

    return {

      min: Math.max(0, min - padding),

      max:
        max + padding

    }

  }


  const range =
    max - min


  // 默认上下各留20%

  const padding =
    range * 0.2


  return {

    min: Math.max(0, min - padding),

    max:
      max + padding

  }

})


// =========================================================
// ECharts
// =========================================================

const option = computed(() => ({

  // =======================================================
  // Tooltip
  // =======================================================

  tooltip: {

    trigger: "axis",

    formatter(params) {

      if (!params.length) {
        return ""
      }

      const item =
        props.data[
          params[0].dataIndex
        ]

      if (!item) {
        return ""
      }

      return `

        时间：
        ${new Date(
          item.time * 1000
        ).toLocaleString(
          "zh-CN",
          {
            hour12: false
          }
        )}

        <br/>

        实时资金：
        ${Number(
          item.balance
        ).toFixed(2)}

        <br/>

        账户余额：
        ${Number(
          item.wallet
        ).toFixed(2)}

        <br/>

        累计收益：
        ${Number(
          item.profit
        ).toFixed(2)}

      `

    }

  },


  // =======================================================
  // Grid
  // =======================================================

  grid: {

    left: 20,

    right: 20,

    top: 20,

    bottom: 50,

    containLabel: true

  },


  // =======================================================
  // X轴
  // =======================================================

  xAxis: {

    type: "category",

    boundaryGap: false,

    data: periodData.value.map(

      item =>
        new Date(
          item.time * 1000
        ).toLocaleTimeString(
          "zh-CN",
          {
            hour12: false
          }
        )

    )

  },


  // =======================================================
  // Y轴
  // =======================================================

  yAxis: {

    type: "value",

    scale: true,

    name: "USDT",

    min:
      yAxisRange.value.min,

    max:
      yAxisRange.value.max

  },


  // =======================================================
  // 核心：DataZoom
  // =======================================================

    dataZoom: [

      {
        type: "inside",

        xAxisIndex: 0,

        filterMode: "none",

        zoomOnMouseWheel: true,

        moveOnMouseMove: true,

        moveOnMouseWheel: true
      },

      {

        filterMode: "none",

        zoomOnMouseWheel: true,

        moveOnMouseMove: true,

        moveOnMouseWheel: true
      },

        {
          type: "slider",

          xAxisIndex: 0,

          start: zoomStart.value,

          end: zoomEnd.value,

          bottom: 5,

          height: 18,

          showDetail: false,

          showDataShadow: false,

          backgroundColor: "transparent",

          borderColor: "transparent",

          dataBackground: {
            lineStyle: {
              opacity: 0
            },
            areaStyle: {
              opacity: 0
            }
          },

          selectedDataBackground: {
            lineStyle: {
              opacity: 0
            },
            areaStyle: {
              opacity: 0
            }
          }
        }

    ],


  // =======================================================
  // 曲线
  // =======================================================

  series: [

    {

      type: "line",

      smooth: true,

      symbol: "none",

      sampling: "lttb",

      lineStyle: {

        color: "#E6A23C",

        width: 3

      },


      areaStyle: {

        color: {

          type: "linear",

          x: 0,

          y: 0,

          x2: 0,

          y2: 1,

          colorStops: [

            {

              offset: 0,

              color:
                "rgba(230,162,60,0.45)"

            },

            {

              offset: 1,

              color:
                "rgba(230,162,60,0.02)"

            }

          ]

        }

      },


        data: periodData.value.map(

          item =>
            Number(item.balance)

        )

    }

  ]

}))

const periodData = computed(() => {

  if (!props.data.length) {
    return []
  }

  const now =
    Math.floor(Date.now() / 1000)

  let seconds = 86400

  switch (period.value) {

    case "1D":
      seconds = 86400
      break

    case "7D":
      seconds = 86400 * 7
      break

    case "30D":
      seconds = 86400 * 30
      break

    case "90D":
      seconds = 86400 * 90
      break
  }

  return props.data.filter(
    item =>
      now - item.time <= seconds
  )

})

const visibleData = computed(() => {

  const total =
    periodData.value.length

  if (!total) {
    return []
  }

  const start =
    Math.floor(
      total * zoomStart.value / 100
    )

  const end =
    Math.ceil(
      total * zoomEnd.value / 100
    )

  return periodData.value.slice(
    start,
    end
  )

})

import {
  onMounted
} from "vue"

onMounted(() => {

  const chart =
    chartRef.value?.chart

  if (!chart) {
    return
  }

  chart.on(
    "datazoom",
    params => {

      const batch =
        params.batch?.[0]

      if (!batch) {
        return
      }

      zoomStart.value =
        batch.start

      zoomEnd.value =
        batch.end

    }
  )
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