<template>
  <el-card>
    <h2>資金總覽</h2>

    <el-row :gutter="20">
      <el-col :span="6">
        總資金
        <h3>
          {{ Number(summary.total_balance || 0).toFixed(2) }}
        </h3>
      </el-col>

      <el-col :span="6">
        多單可用
        <h3>
          {{ Number(summary.long_available || 0).toFixed(2) }}
        </h3>
      </el-col>

      <el-col :span="6">
        空單可用
        <h3>
          {{ Number(summary?.short_available || 0).toFixed(2) }}
        </h3>
      </el-col>

      <el-col :span="6">
        總浮盈
        <h3>
          {{ Number(floating.total_float || 0).toFixed(2) }}
        </h3>
      </el-col>
    </el-row>
  </el-card>
</template>

<script setup>
const props = defineProps({
  summary: {
    type: Object,
    default: () => ({})
  },
  floating: {
    type: Object,
    default: () => ({})
  }
})
</script>