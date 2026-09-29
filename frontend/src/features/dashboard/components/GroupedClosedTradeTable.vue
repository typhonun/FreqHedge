<template>
  <div class="grouped-closed-trade">
    <ClosedTradeTable v-if="!grouped" :positions="positions" />

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

          <el-tag size="small" type="info">{{ group.items.length }} 条</el-tag>

          <span
            class="group-profit"
            :class="group.totalProfit >= 0 ? 'profit' : 'loss'"
          >
            {{ group.totalProfit >= 0 ? '+' : '' }}{{ group.totalProfit.toFixed(2) }} USDT
          </span>
        </div>

        <transition name="expand">
          <div v-show="isExpanded(group.botId)" class="group-body">
            <ClosedTradeTable :positions="group.wrapped" />
          </div>
        </transition>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { ArrowRight, ArrowDown } from '@element-plus/icons-vue'
import ClosedTradeTable from './ClosedTradeTable.vue'   // ★ 是 ClosedTradeTable

const props = defineProps({
  positions: { type: [Array, Object], default: () => [] },
  bots:      { type: Array, default: () => [] },
  grouped:   { type: Boolean, default: true },
})

const expandedIds = ref([])

const flat = computed(() => {
  const longs  = props.positions?.long  || []
  const shorts = props.positions?.short || []
  return [
    ...longs.map(t => ({ ...t, side: 'LONG' })),
    ...shorts.map(t => ({ ...t, side: 'SHORT' })),
  ]
})

const botMap = computed(() => {
  const m = {}
  for (const b of props.bots) m[b.id] = b
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
        long: [],
        short: [],
        items: [],
        totalProfit: 0,
      })
    }
    const g = map.get(bid)
    if (t.side === 'LONG') g.long.push(t)
    else g.short.push(t)
    g.items.push(t)
    g.totalProfit += Number(t.profit_abs || 0)
  }
  const arr = [...map.values()].sort((a, b) => a.botId - b.botId)
  for (const grp of arr) grp.wrapped = { long: grp.long, short: grp.short }
  return arr
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