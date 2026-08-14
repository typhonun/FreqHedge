<template>

    <el-row :gutter="20">

        <el-col :span="16">
            <AccountCard
                :summary="store.summary"
                :floating="store.floating"
                :balanceCurve="store.balanceCurve"
            />
        </el-col>

    </el-row>

    <br />
        <el-col :span="8">
            <ExposureCard
                :summary="store.summary"
            />
        </el-col>

    <br />

    <ProfitCard
        :profit="store.profit"
    />

    <br />

    <ClosedProfitCard
        :profit="store.closedProfit"
    />

    <br />

    <br/>

    <ProfitCurve
      :data="store.profitCurve"
    />

    <el-card>

        <h2>目前持仓</h2>

        <PositionTableCommon
            :positions="store.positions"
        />

    </el-card>

    <br />

    <ClosedTradeTable
        :positions="store.closedPositions"
    />

</template>

<script setup>

import AccountCard from "../components/AccountCard.vue"
import ProfitCard from "../components/ProfitCard.vue"
import ExposureCard from "../components/ExposureCard.vue"
import PositionTableCommon from "@/components/PositionTableCommon.vue"
import ClosedTradeTable from "../components/ClosedTradeTable.vue"
import ClosedProfitCard from "../components/ClosedProfitCard.vue"
import ProfitCurve from "../components/ProfitCurve.vue"

import { useTradeStore } from "../stores/tradeStore"
import {
    onMounted,
    onUnmounted
} from "vue"

const store = useTradeStore()

let timer = null

let historyTimer = null



onMounted(async()=>{


    // 初始化数据

    await store.refresh()

    await store.refreshHistory()



    // 高频数据

    timer = setInterval(()=>{


        store.refresh()


    },5000)



    // 历史数据

    historyTimer = setInterval(()=>{


        store.refreshHistory()


    },60000)



})


onUnmounted(()=>{


    if(timer){

        clearInterval(timer)

    }


    if(historyTimer){

        clearInterval(historyTimer)

    }


})

</script>