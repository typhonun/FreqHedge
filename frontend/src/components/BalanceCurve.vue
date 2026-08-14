<template>

  <VChart
    ref="chartRef"
    class="chart"
    :option="option"
    autoresize
  />

</template>

<script setup>

import {
  computed,
  ref
} from "vue"

import VChart from "vue-echarts"

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

  if (!props.data.length) {

    return {
      min: 0,
      max: 100
    }

  }

  const values = props.data

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
        ).toLocaleString()}

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

    data: props.data.map(

      item =>
        new Date(
          item.time * 1000
        ).toLocaleTimeString()

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
        type: "inside",

        yAxisIndex: 0,

        filterMode: "none",

        zoomOnMouseWheel: true,

        moveOnMouseMove: true,

        moveOnMouseWheel: true
      },

      {
        type: "slider",

        xAxisIndex: 0,

        height: 18,

        bottom: 5,

        start: 0,

        end: 100,

        showDetail: false
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


      data: props.data.map(

        item =>
          Number(item.balance)

      )

    }

  ]

}))

</script>


<style scoped>

.chart {

  height: 320px;

  width: 100%;

}

</style>