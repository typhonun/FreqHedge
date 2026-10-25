<template>
  <div class="positions-page">
    <!-- 顶部筛选 -->
    <el-card class="filter-card" shadow="never">
      <div class="filter-row">
        <span class="filter-label">机器人</span>
        <el-select
          v-model="filterBotId"
          clearable
          placeholder="全部"
          style="width: 220px"
        >
          <el-option
            v-for="b in bots"
            :key="b.id"
            :label="`${b.name} (#${b.id})`"
            :value="b.id"
          />
        </el-select>

        <el-radio-group v-model="viewMode" size="small">
          <el-radio-button value="grouped">按机器人分组</el-radio-button>
          <el-radio-button value="flat">平铺</el-radio-button>
        </el-radio-group>

      </div>
    </el-card>

    <!-- 目前持仓 -->
    <el-card>
      <template #header>
        <div class="card-header">
          <span>目前持仓</span>
          <el-tag size="small" type="info">
            {{ positionCount }} 条
          </el-tag>
        </div>
      </template>
      <GroupedPositionTable
        :positions="store.positions"
        :bots="bots"
        :grouped="viewMode === 'grouped' && filterBotId == null"
      />
    </el-card>

    <!-- 已平仓交易 -->
    <el-card>
      <template #header>
        <div class="card-header">
          <span>已平仓交易</span>
          <el-tag size="small" type="info">
            {{ closedCount }} 条
          </el-tag>
        </div>
      </template>
      <GroupedClosedTradeTable
        :positions="store.closedPositions"
        :bots="bots"
        :grouped="viewMode === 'grouped' && filterBotId == null"
      />
    </el-card>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, onActivated, onDeactivated, watch } from 'vue'
import { useTradeStore } from '@/stores/tradeStore'
import { useBotStore } from '@/stores/botStore'
import GroupedPositionTable from '@features/dashboard/components/GroupedPositionTable.vue'
import GroupedClosedTradeTable from '@features/dashboard/components/GroupedClosedTradeTable.vue'

const store = useTradeStore()
const botStore = useBotStore()

const bots = computed(() => botStore.state.bots)

const filterBotId = ref(null)
const viewMode = ref('grouped')

let timer = null
let historyTimer = null

const positionCount = computed(() => {
  const p = store.positions || {}
  return (p.long?.length || 0) + (p.short?.length || 0)
})

const closedCount = computed(() => {
  const p = store.closedPositions || {}
  return (p.long?.length || 0) + (p.short?.length || 0)
})

const loadBots = async () => {
  try {
    await botStore.fetchBots()
  } catch (e) {
    console.error('[Positions] loadBots failed', e)
  }
}

const reload = async () => {
  await store.refresh(filterBotId.value)
  await store.refreshHistory(filterBotId.value)
}

watch(filterBotId, async () => {
  await reload()
})

// =========================================================
// 定时器优化：拉长轮询时间
// =========================================================
const startTimers = () => {
  stopTimers()

  // 1) 当前持仓：改为 30 秒刷新一次
  timer = setInterval(() => store.refresh(filterBotId.value), 30000)

  // 2) 已平仓交易：改为 5 分钟刷新一次
  historyTimer = setInterval(() => store.refreshHistory(filterBotId.value), 300000)
}

const stopTimers = () => {
  // ★ 移除无用的 console.log
  if (timer) { clearInterval(timer); timer = null }
  if (historyTimer) { clearInterval(historyTimer); historyTimer = null }
}

onMounted(async () => {
  // ★ 移除无用的 console.log
  await loadBots()
  await reload()
  startTimers()
})

onUnmounted(() => {
  stopTimers()
})

onActivated(async () => {
  await loadBots()
  await reload()
  startTimers()
})

onDeactivated(() => {
  stopTimers()
})
</script>

<style scoped>
.positions-page {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.filter-card { border-radius: 12px; }

.filter-row {
  display: flex;
  align-items: center;
  gap: 16px;
}

.filter-label {
  color: var(--el-text-color-secondary);
  font-size: 14px;
}

.refresh-tip {
  margin-left: auto;
  color: var(--el-text-color-placeholder);
  font-size: 12px;
}

.card-header {
  display: flex;
  align-items: center;
  gap: 10px;
}
</style>