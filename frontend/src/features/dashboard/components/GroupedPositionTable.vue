<template>
  <div class="grouped-position-table">
    <PositionTableCommon
      v-if="!grouped"
      :positions="positions"
    />

    <div v-else class="group-list">
      <div
        v-for="group in groups"
        :key="group.botId"
        class="group-block"
      >
        <div
          class="group-header"
          :class="{ expanded: isExpanded(group.botId) }"
          @click="toggleGroup(group.botId)"
        >
          <el-icon class="arrow">
            <ArrowRight v-if="!isExpanded(group.botId)" />
            <ArrowDown  v-else />
          </el-icon>

          <el-tag size="small" type="primary">#{{ group.botId }}</el-tag>
          <span class="group-name">{{ group.botName }}</span>

          <el-tag size="small" type="info">
            {{ group.items.length }} 条
          </el-tag>

          <el-tag
            v-if="group.botDryRun !== undefined"
            size="small"
            :type="group.botDryRun ? 'info' : 'warning'"
          >
            {{ group.botDryRun ? 'Dry Run' : '实盘' }}
          </el-tag>

          <el-tag
            v-if="group.botStatus && group.botStatus !== 'running'"
            size="small"
            type="danger"
          >
            已停止
          </el-tag>

          <span
            class="group-profit"
            :class="group.totalProfit >= 0 ? 'profit' : 'loss'"
          >
            {{ group.totalProfit >= 0 ? '+' : '' }}{{ group.totalProfit.toFixed(2) }} USDT
          </span>
        </div>

        <transition name="expand">
          <div v-show="isExpanded(group.botId)" class="group-body">
            <PositionTableCommon :positions="group.items" />
          </div>
        </transition>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'           // ★ 加 onMounted
import { ArrowRight, ArrowDown } from '@element-plus/icons-vue'
import axios from 'axios'                                        // ★ 加 axios
import PositionTableCommon from './PositionTableCommon.vue'

const API = 'http://localhost:9000'

const props = defineProps({
  positions: { type: [Array, Object], default: () => [] },
  bots:      { type: Array, default: () => [] },
  grouped:   { type: Boolean, default: true },
})

const expandedIds = ref([])

const flat = computed(() => {
  let result = []
  if (Array.isArray(props.positions)) {
    result = [...props.positions]
  } else {
    const longs  = props.positions?.long  || []
    const shorts = props.positions?.short || []
    result = [
      ...longs.map(t => ({ ...t, side: 'LONG' })),
      ...shorts.map(t => ({ ...t, side: 'SHORT' })),
    ]
  }
  return result
})

// ★ 只保留一份 botMap
const internalBots = ref([])

const effectiveBots = computed(() => {
  return (props.bots && props.bots.length) ? props.bots : internalBots.value
})

const botMap = computed(() => {
  const m = {}
  for (const b of effectiveBots.value) m[b.id] = b
  return m
})

const groups = computed(() => {
  const map = new Map()
  for (const t of flat.value) {
    const bid = t.bot_id ?? -1
    if (!map.has(bid)) {
      const bot = botMap.value[bid] || {}
      map.set(bid, {
        botId: bid,
        botName: bot.name || `未知机器人 #${bid}`,
        botDryRun: bot.dryRun,
        botStatus: bot.status,
        items: [],
        totalProfit: 0,
      })
    }
    const g = map.get(bid)
    g.items.push(t)
    g.totalProfit += Number(t.profit_abs || t.total_profit_abs || 0)
  }
  return [...map.values()].sort((a, b) => a.botId - b.botId)
})

watch(
  groups,
  (arr) => {
    if (arr.length === 0) return
    const existing = new Set(expandedIds.value)
    const next = [...expandedIds.value]
    let changed = false
    for (const g of arr) {
      if (!existing.has(g.botId)) {
        next.push(g.botId)
        changed = true
      }
    }
    if (changed) expandedIds.value = next
  },
  { immediate: true }
)

const isExpanded = (bid) => expandedIds.value.includes(bid)
const toggleGroup = (bid) => {
  const arr = [...expandedIds.value]
  const idx = arr.indexOf(bid)
  if (idx >= 0) arr.splice(idx, 1)
  else arr.push(bid)
  expandedIds.value = arr
}

onMounted(async () => {
  if (props.bots && props.bots.length) return
  try {
    const { data } = await axios.get(`${API}/bots`)
    internalBots.value = data
  } catch (e) {
    console.error('[GroupedPositionTable] fetch bots failed', e)
  }
})
</script>

<style scoped>
.group-list { display: flex; flex-direction: column; gap: 10px; }
.group-block {
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 10px;
  overflow: hidden;
  background: #fff;
}
.group-header {
  display: flex; align-items: center; gap: 10px;
  padding: 12px 16px; cursor: pointer;
  background: #fafafa; user-select: none;
  transition: background .2s;
}
.group-header:hover { background: #f2f3f5; }
.group-header.expanded { border-bottom: 1px solid var(--el-border-color-lighter); }
.arrow { font-size: 14px; color: var(--el-text-color-secondary); }
.group-name { font-weight: 600; }
.group-profit { margin-left: auto; font-weight: 600; }
.profit { color: #67c23a; }
.loss   { color: #f56c6c; }
.group-body { padding: 0; }

.expand-enter-active,
.expand-leave-active { transition: all .2s ease; overflow: hidden; }
.expand-enter-from,
.expand-leave-to { opacity: 0; max-height: 0; }
.expand-enter-to,
.expand-leave-from { opacity: 1; max-height: 2000px; }
</style>