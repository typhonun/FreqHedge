<template>

  <el-card>

    <template #header>
      <h2>收益曲线</h2>
    </template>

    <VChart
      class="chart"
      :option="option"
      autoresize
    />

  </el-card>

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
    trigger: "axis"
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
    type: "value"
  },

  series: [
    {
      type: "line",
      smooth: true,

      areaStyle: {},

      data: props.data.map(
        item => item.profit
      )
    }
  ]
}))
</script>

<style scoped>

.chart{
  height:300px;
}

</style>