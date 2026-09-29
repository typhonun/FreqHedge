<template>
  <el-card>
    <template #header>
      <div class="header">
        <h2>收益曲线</h2>

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
    </template>

    <VChart class="chart" :option="option" autoresize />
  </el-card>
</template>

<script setup>
import { computed, ref, watch } from "vue"
import VChart from "vue-echarts"

const props = defineProps({
  data: { type: Array, default: () => [] },
  botList: { type: Array, default: () => [] },
  modelValue: { type: [String, Number], default: '__total__' }
})

const emit = defineEmits(['update:modelValue', 'change'])

const selected = ref(props.modelValue)

watch(() => props.modelValue, v => { selected.value = v })

const handleChange = (val) => {
  emit('update:modelValue', val)
  emit('change', val)
}

const curveData = computed(() => props.data.map(i => i.total_profit))

const currentProfit = computed(() => {
  if (curveData.value.length === 0) return 0
  return curveData.value[curveData.value.length - 1]
})

const lineColor = computed(() =>
  currentProfit.value >= 0 ? "#16c784" : "#ea3943"
)

const option = computed(() => ({
  tooltip: { trigger: "axis" },
  grid: { left: 40, right: 20, top: 20, bottom: 40 },
  xAxis: {
    type: "category",
    boundaryGap: false,
    data: props.data.map(item =>
      new Date(item.time * 1000).toLocaleTimeString()
    )
  },
  yAxis: { type: "value" },
  series: [
    {
      type: "line",
      smooth: true,
      symbol: "none",
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
      data: curveData.value
    }
  ]
}))
</script>

<style scoped>
.chart { height: 400px; }
.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
</style>