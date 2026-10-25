<template>
  <div class="dashboard-page">
    <el-row :gutter="20">
      <el-col :span="16">
        <AccountCard
          v-model="accountSelected"
          :summary="store.summary"
          :floating="store.floating"
          :balanceCurve="store.balanceCurve"
          :botList="botList"
          @change="onAccountChange"
        />
      </el-col>
      <el-col :span="8">
        <ExposureCard :summary="store.summary" />
      </el-col>
    </el-row>

    <ProfitCurve
      v-model="profitSelected"
      :data="store.profitCurve"
      :botList="botList"
      @change="onProfitChange"
    />

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
import { computed, onMounted, onUnmounted, onActivated, onDeactivated, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ArrowRight } from '@element-plus/icons-vue'

import AccountCard from '@features/dashboard/components/AccountCard.vue'
import ExposureCard from '@features/dashboard/components/ExposureCard.vue'
import ProfitCurve from '@features/dashboard/components/ProfitCurve.vue'

import { useTradeStore } from '@/stores/tradeStore'
import axios from 'axios'

const API = 'http://localhost:9000'
const router = useRouter()
const store = useTradeStore()

// 两个独立的下拉框
const accountSelected = ref('__total__')
const profitSelected = ref('__total__')

const botList = ref([])

const toBotId = (v) => (v === '__total__' ? null : v)

// 快速跳转卡片
const positionCount = computed(() => {
  const p = store.positions || {}
  return (p.long?.length || 0) + (p.short?.length || 0)
})
const closedCount = computed(() => {
  const p = store.closedPositions || {}
  return (p.long?.length || 0) + (p.short?.length || 0)
})
const goPositions = () => router.push({ name: 'Positions' })

// 定时器
let timer = null
let historyTimer = null

const refreshAccount = () =>
  store.refreshAccount(toBotId(accountSelected.value))

const refreshProfitCurve = () =>
  store.refreshProfitCurve(toBotId(profitSelected.value))

// =========================================================
// 定时器优化：降低轮询频率
// =========================================================
const startTimers = () => {
  stopTimers()

  // 1) 账户盈亏、收益曲线：改为 15 秒刷新一次
  timer = setInterval(async () => {
    await refreshAccount()
    await refreshProfitCurve()
  }, 15000)

  // 2) 持仓数量、平仓数量：这些数据不需要高频看，改为 5 分钟刷新一次
  historyTimer = setInterval(async () => {
    await store.refresh(null)
    await store.refreshHistory(null)
  }, 300000)
}

const stopTimers = () => {
  if (timer) { clearInterval(timer); timer = null }
  if (historyTimer) { clearInterval(historyTimer); historyTimer = null }
}

const loadBotList = async () => {
  try {
    const { data } = await axios.get(`${API}/bots`)
    botList.value = data.map(b => ({ id: b.id, name: b.name }))
  } catch (e) {
    console.error('load bot list failed', e)
  }
}

// 两个下拉框各自的 change 回调
const onAccountChange = async () => {
  await refreshAccount()
}

const onProfitChange = async () => {
  await refreshProfitCurve()
}

onMounted(async () => {
  await loadBotList()
  await refreshAccount()
  await refreshProfitCurve()
  await store.refresh(null)
  await store.refreshHistory(null)
  startTimers()
})

onUnmounted(stopTimers)
onDeactivated(stopTimers)

onActivated(async () => {
  await loadBotList()
  await refreshAccount()
  await refreshProfitCurve()
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