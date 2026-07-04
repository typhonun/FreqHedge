<template>
  <div>

    <el-row :gutter="20">

      <el-col :span="12">
        <RunControl />
      </el-col>

      <el-col :span="12">
        <StatusPanel />
      </el-col>

    </el-row>

    <Capital />

  </div>
</template>

<script setup>
import RunControl from "../components/RunControl.vue"
import StatusPanel from "../components/StatusPanel.vue"
import Capital from "../components/Capital.vue"
</script>