<template>

  <div style="padding:20px">

    <AccountCard
            :summary="store.summary"
            :floating="store.floating"
        />

    <el-row :gutter="20">

      <el-col :span="24">

        <ProfitCard
          :profit="store.profit"
        />

      </el-col>

    </el-row>

    <br>

    <el-row :gutter="20">

      <el-col :span="24">

        <PositionTable
         :positions="store.positions"
      />

      </el-col>

    </el-row>

    <br>

    <el-button
      type="success"
      @click="refresh"
    >
      刷新
    </el-button>

  </div>

</template>

<script setup>

import { onMounted } from "vue"

import ProfitCard from "../components/ProfitCard.vue"
import PositionTable from "../components/PositionTable.vue"
import AccountCard from "../components/AccountCard.vue"
import { useTradeStore } from "../stores/tradeStore"

const store =
    useTradeStore()

const refresh = () => {
    store.refresh()
}

onMounted(() => {
    refresh()
})

</script>