<template>

  <el-card>

    <template #header>

      <div class="header">

        <h2>收益曲线</h2>

        <el-select
          v-model="curveType"
          style="width:140px"
        >
          <el-option
            label="总收益"
            value="total"
          />

          <el-option
            label="多头收益"
            value="long"
          />

          <el-option
            label="空头收益"
            value="short"
          />

        </el-select>

      </div>

    </template>

    <VChart
      class="chart"
      :option="option"
      autoresize
    />

  </el-card>

</template>

<script setup>

import { computed, ref } from "vue"
import VChart from "vue-echarts"

const curveType = ref("total")

const props = defineProps({

  data: {
    type: Array,
    default: () => []
  }

})


// 当前显示的数据

const curveData = computed(() => {

  switch(curveType.value){

    case "long":
      return props.data.map(
        i => i.long_profit
      )

    case "short":
      return props.data.map(
        i => i.short_profit
      )

    default:
      return props.data.map(
        i => i.total_profit
      )
  }

})


// 当前收益值

const currentProfit = computed(() => {

  if(curveData.value.length === 0){

    return 0

  }

  return curveData.value[
    curveData.value.length - 1
  ]

})


// 红绿颜色

const lineColor = computed(() => {

  return currentProfit.value >= 0
    ? "#16c784"
    : "#ea3943"

})


const option = computed(() => ({

  tooltip: {
    trigger: "axis"
  },

  grid: {
    left: 40,
    right: 20,
    top: 20,
    bottom: 40
  },

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

  yAxis: {
    type: "value"
  },

  series: [

    {

      type: "line",

      smooth: true,

      symbol: "none",

      lineStyle: {

        width: 3,

        color: lineColor.value

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
                lineColor.value

            },

            {

              offset: 1,

              color:
                "rgba(0,0,0,0)"

            }

          ]
        }
      },

      data:
        curveData.value

    }

  ]

}))
</script>

<style scoped>

.chart{

  height:400px;

}

.header{

  display:flex;

  justify-content:space-between;

  align-items:center;

}
</style>