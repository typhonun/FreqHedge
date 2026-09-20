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
// ============ 组件 ============
import AccountCard from '@features/dashboard/components/AccountCard.vue'
import ProfitCard from '@features/dashboard/components/ProfitCard.vue'
import ExposureCard from '@features/dashboard/components/ExposureCard.vue'
import PositionTableCommon from '@features/dashboard/components/PositionTableCommon.vue'
import ClosedTradeTable from '@features/dashboard/components/ClosedTradeTable.vue'
import ClosedProfitCard from '@features/dashboard/components/ClosedProfitCard.vue'
import ProfitCurve from '@features/dashboard/components/ProfitCurve.vue'

// ============ Store ============
import { useTradeStore } from '@/stores/tradeStore'

// ============ Vue ============
import { onMounted, onUnmounted } from 'vue'

const store = useTradeStore()

let timer = null
let historyTimer = null

onMounted(async () => {
  await store.refresh()
  await store.refreshHistory()

  timer = setInterval(() => {
    store.refresh()
  }, 5000)

  historyTimer = setInterval(() => {
    store.refreshHistory()
  }, 60000)
})

onUnmounted(() => {
  if (timer) clearInterval(timer)
  if (historyTimer) clearInterval(historyTimer)
})
</script>