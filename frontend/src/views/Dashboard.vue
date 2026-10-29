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
          @periodChange="onPeriodChange"
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
import { computed, onMounted, onUnmounted, onActivated, onDeactivated, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ArrowRight } from '@element-plus/icons-vue'

import AccountCard from '@features/dashboard/components/AccountCard.vue'
import ExposureCard from '@features/dashboard/components/ExposureCard.vue'
import ProfitCurve from '@features/dashboard/components/ProfitCurve.vue'

import { useTradeStore } from '@/stores/tradeStore'
import axios from 'axios'
import { useModeStore } from '@/stores/modeStore'

const API = 'http://localhost:9000'
const router = useRouter()
const store = useTradeStore()
const modeStore = useModeStore()

// 两个独立的下拉框
const accountSelected = ref('__total__')
const profitSelected = ref('__total__')

// 新增：记录当前曲线选择的周期
const currentPeriod = ref('1D')

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

// 1. 单独封装请求曲线的函数（直接调用 API）
const fetchBalanceCurve = async (botId, period) => {
  try {
    let url = `${API}/position/balance_curve?period=${period}&dry_run=${modeStore.isSimulation.value}`
    if (botId) {
      url += `&bot_id=${botId}`
    }
    const { data } = await axios.get(url)
    // 将数据存入 store
    store.balanceCurve = data
  } catch (e) {
    console.error('获取曲线失败', e)
  }
}

// 2. 周期切换事件（由 AccountCard -> BalanceCurve 触发）
const onPeriodChange = async (newPeriod) => {
  currentPeriod.value = newPeriod
  await fetchBalanceCurve(toBotId(accountSelected.value), newPeriod)
}

// 3. 刷新账户数据（保留你原有的 refreshAccount）
const refreshAccount = () =>
  store.refreshAccount(toBotId(accountSelected.value), currentPeriod.value)

// 4. 完整刷新账户；refreshAccount 已同时更新余额曲线
const refreshAccountAll = async () => {
  await refreshAccount()
}

const refreshProfitCurve = () =>
  store.refreshProfitCurve(toBotId(profitSelected.value))

// =========================================================
// 定时器优化：降低轮询频率
// =========================================================
const startTimers = () => {
  stopTimers()

  // 1) 账户盈亏、收益曲线、权益曲线：改为 15 秒刷新一次
  timer = setInterval(async () => {
    await refreshAccountAll() // 包含曲线刷新
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
    const { data } = await axios.get(`${API}/bots?dry_run=${modeStore.isSimulation.value}`)
    botList.value = data.map(b => ({ id: b.id, name: b.name }))
  } catch (e) {
    console.error('load bot list failed', e)
  }
}

// 两个下拉框各自的 change 回调
const onAccountChange = async () => {
  // 切换机器人时，重新拉取数据（使用当前选中的周期）
  await refreshAccountAll()
}

const onProfitChange = async () => {
  await refreshProfitCurve()
}

onMounted(async () => {
  await loadBotList()
  await refreshAccountAll() // 初始化时加载账户和曲线
  await refreshProfitCurve()
  await store.refresh(null)
  await store.refreshHistory(null)
  startTimers()
})

onUnmounted(stopTimers)
onDeactivated(stopTimers)

onActivated(async () => {
  await loadBotList()
  await refreshAccountAll() // 重新激活时加载账户和曲线
  await refreshProfitCurve()
  await store.refresh(null)
  await store.refreshHistory(null)
  startTimers()
})

watch(modeStore.mode, async () => {
  accountSelected.value = '__total__'
  profitSelected.value = '__total__'
  await loadBotList()
  await refreshAccountAll()
  await refreshProfitCurve()
  await store.refresh(null)
  await store.refreshHistory(null)
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