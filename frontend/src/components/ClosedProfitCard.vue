<template>
  <el-card>

    <template #header>
      <h2>累计收益</h2>
    </template>

    <el-row :gutter="20">

      <el-col :span="8">
        <el-statistic
          title="多单收益"
          :value="profit.long_total_profit || 0"
          :precision="2"
        />
      </el-col>

      <el-col :span="8">
        <el-statistic
          title="空单收益"
          :value="profit.short_total_profit || 0"
          :precision="2"
        />
      </el-col>

      <el-col :span="8">
        <el-statistic
          title="总收益"
          :value="profit.total_profit || 0"
          :precision="2"
        />
      </el-col>

    </el-row>

  </el-card>
</template>


<script setup>

    defineProps({

        profit:{
        type:Object,
        default:()=>({})
        }

    })

</script>