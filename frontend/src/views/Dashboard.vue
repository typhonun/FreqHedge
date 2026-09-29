<template>
  <div class="dashboard-page">
    <el-row :gutter="20">
      <el-col :span="16">
        <AccountCard
          :summary="store.summary"
          :floating="store.floating"
          :balanceCurve="store.balanceCurve"
        />
      </el-col>
      <el-col :span="8">
        <ExposureCard :summary="store.summary" />
      </el-col>
    </el-row>

    <br />
    <ProfitCard :profit="store.profit" />
    <br />
    <ClosedProfitCard :profit="store.closedProfit" />
    <br /><br />
    <ProfitCurve :data="store.profitCurve" />

    <!-- ★ 快速跳转卡片 -->
    <el-row :gutter="20">
      <el-col :span="12">
        <el-card class="jump-card" shadow="hover" @click="goPositions">
          <div class="jump-inner">
            <div>
              <div class="jump-title">当前持仓</div>
              <div class="jump-value">{{ positionCount }}</div>
            </div>
            <el-icon class="jump-arrow"><ArrowRight /></el-icon>
          </div>
        </el-card>
      </el-col>
      <el-col :span="12">
        <el-card class="jump-card" shadow="hover" @click="goPositions">
          <div class="jump-inner">
            <div>
              <div class="jump-title">已平仓交易</div>
              <div class="jump-value">{{ closedCount }}</div>
            </div>
            <el-icon class="jump-arrow"><ArrowRight /></el-icon>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, onActivated, onDeactivated } from 'vue'
import { useRouter } from 'vue-router'
import { ArrowRight } from '@element-plus/icons-vue'

import AccountCard from '@features/dashboard/components/AccountCard.vue'
import ProfitCard from '@features/dashboard/components/ProfitCard.vue'
import ExposureCard from '@features/dashboard/components/ExposureCard.vue'
import ClosedProfitCard from '@features/dashboard/components/ClosedProfitCard.vue'
import ProfitCurve from '@features/dashboard/components/ProfitCurve.vue'

import { useTradeStore } from '@/stores/tradeStore'

const router = useRouter()
const store = useTradeStore()

const positionCount = computed(() => {
  const p = store.positions || {}
  return (p.long?.length || 0) + (p.short?.length || 0)
})

const closedCount = computed(() => {
  const p = store.closedPositions || {}
  return (p.long?.length || 0) + (p.short?.length || 0)
})

const goPositions = () => router.push({ name: 'Positions' })

let timer = null
let historyTimer = null

const startTimers = () => {
  stopTimers()
  timer = setInterval(() => store.refresh(null), 5000)
  historyTimer = setInterval(() => store.refreshHistory(null), 60000)
}

const stopTimers = () => {
  if (timer) { clearInterval(timer); timer = null }
  if (historyTimer) { clearInterval(historyTimer); historyTimer = null }
}

onMounted(async () => {
  store.setBotId(null)
  await store.refresh(null)
  await store.refreshHistory(null)
  startTimers()
})

onUnmounted(stopTimers)
onDeactivated(stopTimers)
onActivated(async () => {
  await store.refresh(null)
  await store.refreshHistory(null)
  startTimers()
})
</script>

<style scoped>
.dashboard-page {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.jump-card {
  cursor: pointer;
  border-radius: 12px;
  transition: transform 0.2s;
}
.jump-card:hover {
  transform: translateY(-2px);
}

.jump-inner {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.jump-title {
  color: var(--el-text-color-secondary);
  font-size: 13px;
  margin-bottom: 6px;
}

.jump-value {
  font-size: 24px;
  font-weight: 700;
  color: var(--text-main, #303133);
}

.jump-arrow {
  font-size: 20px;
  color: var(--el-text-color-placeholder);
}
</style>