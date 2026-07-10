<template>

    <el-row :gutter="20">

        <el-col :span="12">

            <AccountCard
                :summary="store.summary"
                :floating="store.floating"
            />

        </el-col>

        <el-col :span="12">

            <ProfitCard
                :profit="store.profit"
            />

        </el-col>

    </el-row>

    <br />

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

import { onMounted } from "vue"

import AccountCard from "../components/AccountCard.vue"
import ProfitCard from "../components/ProfitCard.vue"
import PositionTableCommon from "@/components/PositionTableCommon.vue"
import ClosedTradeTable from "../components/ClosedTradeTable.vue"

import { useTradeStore } from "../stores/tradeStore"

const store = useTradeStore()

onMounted(async () => {

    await store.refresh()

})

</script>