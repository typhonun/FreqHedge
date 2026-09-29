<template>
  <div class="dashboard-page">
    <!-- 顶部 bot 选择器 -->
    <el-card class="bot-selector-card" shadow="never">
      <div class="selector-row">
        <span class="selector-label">数据视图</span>
        <el-select
          v-model="selectedBotId"
          clearable
          placeholder="全部机器人（聚合）"
          style="width: 260px"
        >
          <el-option
            v-for="b in bots"
            :key="b.id"
            :label="`${b.name} (#${b.id})`"
            :value="b.id"
          />
        </el-select>

        <el-tag v-if="selectedBotId == null" type="info" size="small">
          聚合视图
        </el-tag>
        <el-tag v-else type="success" size="small">
          单 bot 视图
        </el-tag>
      </div>
    </el-card>

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
      <ExposureCard :summary="store.summary" />
    </el-col>

    <br />
    <ProfitCard :profit="store.profit" />
    <br />
    <ClosedProfitCard :profit="store.closedProfit" />
    <br /><br />
    <ProfitCurve :data="store.profitCurve" />

    <el-card>
      <h2>目前持仓</h2>
      <PositionTableCommon :positions="store.positions" />
    </el-card>

    <br />
    <ClosedTradeTable :positions="store.closedPositions" />
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch } from 'vue'

import AccountCard from '@features/dashboard/components/AccountCard.vue'
import ProfitCard from '@features/dashboard/components/ProfitCard.vue'
import ExposureCard from '@features/dashboard/components/ExposureCard.vue'
import PositionTableCommon from '@features/dashboard/components/PositionTableCommon.vue'
import ClosedTradeTable from '@features/dashboard/components/ClosedTradeTable.vue'
import ClosedProfitCard from '@features/dashboard/components/ClosedProfitCard.vue'
import ProfitCurve from '@features/dashboard/components/ProfitCurve.vue'

import { useTradeStore } from '@/stores/tradeStore'
import { useBotStore } from '@/stores/botStore'

const store = useTradeStore()
const botStore = useBotStore()

const bots = ref([])
const selectedBotId = ref(null)

let timer = null
let historyTimer = null

const loadBots = async () => {
  await botStore.fetchBots()
  bots.value = botStore.state.bots
}

const reload = async () => {
  await store.refresh(selectedBotId.value)
  await store.refreshHistory(selectedBotId.value)
}

watch(selectedBotId, async (id) => {
  store.setBotId(id)
  await reload()
})

onMounted(async () => {
  await loadBots()
  await reload()

  timer = setInterval(() => {
    store.refresh(selectedBotId.value)
  }, 5000)

  historyTimer = setInterval(() => {
    store.refreshHistory(selectedBotId.value)
  }, 60000)
})

onUnmounted(() => {
  if (timer) clearInterval(timer)
  if (historyTimer) clearInterval(historyTimer)
})
</script>

<style scoped>
.dashboard-page {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.bot-selector-card {
  border-radius: 12px;
}

.selector-row {
  display: flex;
  align-items: center;
  gap: 12px;
}
</style>