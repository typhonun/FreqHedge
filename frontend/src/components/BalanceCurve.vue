<template>

  <VChart
    class="chart"
    :option="option"
    autoresize
  />

</template>

<script setup>

import { computed } from "vue"
import VChart from "vue-echarts"

const props = defineProps({
  data: {
    type: Array,
    default: () => []
  }
})

const option = computed(() => ({

    tooltip: {

      trigger: "axis",

      formatter(params){

        const item = props.data[
          params[0].dataIndex
        ]

        return `
          时间：${new Date(
            item.time * 1000
          ).toLocaleTimeString()}
          <br/>
          实时资金：${item.balance}
          <br/>
          账户余额：${item.wallet}
          <br/>
          累计收益：${item.profit}
        `
      }
    },

  grid: {
    left: 20,
    right: 20,
    top: 20,
    bottom: 30,
    containLabel: true
  },

  xAxis: {
    type: "category",

    data: props.data.map(
      item =>
        new Date(
          item.time * 1000
        ).toLocaleTimeString()
    )
  },

    yAxis: {

      type: "value",

      scale: true,

      name: "USDT"
    },

  series: [

    {

      type: "line",

      smooth: true,

      symbol: "none",

        lineStyle: {

          color: "#E6A23C",

          width: 4
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
                color: "rgba(230,162,60,0.45)"
              },
              {
                offset: 1,
                color: "rgba(230,162,60,0.02)"
              }
            ]
          }
        },

      data: props.data.map(
        item => item.balance
      )
    }
  ]
}))
</script>

<style scoped>

.chart{
  height:320px;
}

</style>