<template>
  <el-card>

    <h2>本轮收益</h2>

    <el-row :gutter="20">

      <el-col :span="8">
        <el-statistic
          title="总收益"
          :value="Number(profit.total_profit || 0)"
          :precision="2"
        />
      </el-col>

      <!-- 新增 -->
      <el-col :span="6">
        <el-statistic
          title="全局止盈次数"
          :value="Number(profit.global_tp_count || 0)"
          :precision="0"
        />
      </el-col>

      <el-col :span="6">
        <el-statistic
          title="全局止损次数"
          :value="Number(profit.global_sl_count || 0)"
          :precision="0"
        />
      </el-col>

      <el-col :span="8">
        <el-statistic
          title="多单收益"
          :value="Number(profit.long_profit || 0)"
          :precision="2"
        />
      </el-col>

      <el-col :span="6">
        <el-statistic
            title="多单已平仓"
            :value="Number(profit.long_closed || 0)"
            :precision="2"
        />
      </el-col>

      <el-col :span="6">
        <el-statistic
            title="多单浮盈"
            :value="Number(profit.long_float || 0)"
            :precision="2"
        />
      </el-col>

      <el-col :span="8">
        <el-statistic
          title="空单收益"
          :value="Number(profit.short_profit || 0)"
          :precision="2"
        />
      </el-col>

      <el-col :span="6">
        <el-statistic
            title="空单已平仓"
            :value="Number(profit.short_closed || 0)"
            :precision="2"
        />
      </el-col>

      <el-col :span="6">
        <el-statistic
            title="空单浮盈"
            :value="Number(profit.short_float || 0)"
            :precision="2"
        />
      </el-col>

    </el-row>

  </el-card>
</template>

<script setup>

defineProps({
  profit: {
    type: Object,
    default: () => ({})
  }
})

</script>