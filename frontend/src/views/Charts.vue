<template>

<el-card>

    <el-row :gutter="20">

        <el-col :span="6">
          <el-select
            v-model="botId"
            placeholder="选择机器人"
            @change="onBotChange"
          >
            <el-option
              v-for="b in botList"
              :key="b.id"
              :label="b.name"
              :value="b.id"
            />
          </el-select>
        </el-col>

        <el-col :span="6">

            <el-select
                v-model="pair"
                placeholder="选择交易对"
                @change="loadChart"
            >

                <el-option
                    v-for="item in pairs"
                    :key="item"
                    :label="item"
                    :value="item"
                />

            </el-select>

        </el-col>

        <el-col :span="4">

            <el-select
                v-model="timeframe"
                @change="loadChart"
            >

                <el-option
                    v-for="item in timeframes"
                    :key="item"
                    :label="item"
                    :value="item"
                />

            </el-select>

        </el-col>

    </el-row>

</el-card>

<div
    ref="chartRef"
    class="chart"
></div>

<el-card
    v-if="strategyPositions.length"
    class="position-card"
>

    <template #header>
      <div class="position-card-header">
        <span>当前持仓</span>
        <PositionActions
          :bot-id="botId"
          :positions="{ long: strategyPositions.filter(t => t.side === 'LONG'), short: strategyPositions.filter(t => t.side === 'SHORT') }"
          @success="loadBotPositions"
        />
      </div>
    </template>

    <PositionTableCommon
        :positions="strategyPositions"
        @selectPair="changePair"
    />

</el-card>

</template>

<script setup>

import axios from "axios"
import { ref, computed, onMounted, onUnmounted, watch } from "vue"
import { useRoute } from "vue-router"
import {
    createChart,
    CandlestickSeries,
    createSeriesMarkers
} from "lightweight-charts"
import PositionActions from '@features/dashboard/components/PositionActions.vue'
import PositionTableCommon from '@features/dashboard/components/PositionTableCommon.vue'
import { useBotStore } from '@/stores/botStore.js'
import { useModeStore } from '@/stores/modeStore'

const API = "http://localhost:9000"
const route = useRoute()

const botStore = useBotStore()
const modeStore = useModeStore()
const botList = computed(() => botStore.state.bots.filter(b => Boolean(b.dryRun) === modeStore.isSimulation.value))

const chartRef = ref(null)

const botId = ref(null)
const pairs = ref([])
const pair = ref("")
const timeframe = ref("30m")
const strategyPositions = ref([])

const timeframes = [
    "1m", "5m", "15m", "30m", "1h", "4h", "1d"
]

const REFRESH_INTERVAL = 5000

let chart = null
let candleSeries = null
let markerApi = null
let refreshTimer = null
let loadingHistory = false // ★ 防止并发请求
let hasMoreHistory = true  // ★ 是否还有更早的数据
let allCandleData = []     // ★ 存储当前图表的所有数据

// =========================================================
// 机器人列表
// =========================================================

const loadBots = async () => {
    await botStore.fetchBots()

    if (!botList.value.length) {
        botId.value = null
        return
    }

    const queryBotId = Number(route.query.botId)
    if (queryBotId && botList.value.find(b => b.id === queryBotId)) {
        botId.value = queryBotId
    } else {
        botId.value = botList.value[0].id
    }

    const selectedBot = botList.value.find(b => b.id === (queryBotId || botList.value[0].id))

    if (selectedBot) {
        // 直接判断 type
        const isGrid = String(selectedBot.strategyType || '').toLowerCase().includes('grid')
        timeframe.value = isGrid ? '1m' : '30m'
    }

    await loadPairs()
}

const onBotChange = async () => {
    // 清空旧数据
    pairs.value = []
    pair.value = ""
    strategyPositions.value = []
    if (candleSeries) candleSeries.setData([])
    if (markerApi) markerApi.setMarkers([])

    // ★ 新增：解绑滚动监听
    if (chart) {
        chart.timeScale().unsubscribeVisibleLogicalRangeChange(handleScroll)
    }

    await loadPairs()
}

// =========================================================
// 交易对 + 当前持仓
// =========================================================

const loadPairs = async () => {
    if (!botId.value) return

    await loadBotPositions()

    const res = await axios.get(`${API}/chart/pairs/${botId.value}`, {
        params: { dry_run: modeStore.isSimulation.value }
    })
    pairs.value = res.data || []

    if (pairs.value.length) {
        const queryPair = route.query.pair
        if (queryPair && pairs.value.includes(queryPair)) {
            pair.value = queryPair
        } else {
            pair.value = pairs.value[0]
        }
        await loadChart()
    } else {
        pair.value = ""
        if (candleSeries) candleSeries.setData([])
        if (markerApi) markerApi.setMarkers([])
    }
}

const loadBotPositions = async () => {
    if (!botId.value) return
    try {
        const res = await axios.get(`${API}/chart/bot-positions/${botId.value}`, {
            params: { dry_run: modeStore.isSimulation.value }
        })
        strategyPositions.value = res.data || []
    } catch (e) {
        console.error("loadBotPositions failed", e)
        strategyPositions.value = []
    }
}

const changePair = async (data) => {
    if (pair.value !== data.pair) {
        pair.value = data.pair
        await loadChart()
    }
}

// =========================================================
// 自动刷新最后一根 K 线
// =========================================================
let lastCandleData = null // 记录上一次的数据用于去重

const startAutoRefresh = () => {
    if (refreshTimer) clearInterval(refreshTimer)

    // ★ 动态计算刷新频率
    let interval = 15000; // 默认 15 秒
    if (timeframe.value === '1m') interval = 3000;
    else if (timeframe.value === '5m') interval = 5000;
    else if (timeframe.value === '15m') interval = 10000;

    refreshTimer = setInterval(updateLastCandle, interval)
}

const updateLastCandle = async () => {
    if (!pair.value || !candleSeries) return
    try {
        const res = await axios.get(`${API}/chart/latest`, {
            params: { pair: pair.value, timeframe: timeframe.value }
        })

        // ★ 核心优化 1：如果后端返回空（无缓存），直接忽略本次刷新，防止报错
        if (!res.data || !res.data.time) return;

        const newCandle = {
            time: Number(Math.floor(res.data.time / 1000)),
            open: Number(res.data.open),
            high: Number(res.data.high),
            low: Number(res.data.low),
            close: Number(res.data.close)
        }

        // ★ 核心优化 2：前端数据去重。如果价格没变，不触发重绘
        if (lastCandleData &&
            lastCandleData.time === newCandle.time &&
            lastCandleData.close === newCandle.close &&
            lastCandleData.high === newCandle.high &&
            lastCandleData.low === newCandle.low) {
            return;
        }

        lastCandleData = newCandle;
        candleSeries.update(newCandle)

    } catch (e) {
        console.error("update candle error", e)
    }
}

// =========================================================
// 加载 K 线 + 事件标记
// =========================================================

const loadChart = async () => {
    if (!pair.value) return
    if (markerApi) markerApi.setMarkers([])

    // 重置状态
    loadingHistory = false
    hasMoreHistory = true
    allCandleData = []

    const res = await axios.get(`${API}/chart/candles`, {
        params: { pair: pair.value, timeframe: timeframe.value }
    })

    const data = res.data.map(c => ({
        time: Number(Math.floor(c.time / 1000)),
        open: Number(c.open),
        high: Number(c.high),
        low: Number(c.low),
        close: Number(c.close)
    }))

    allCandleData = [...data] // ★ 核心修复：赋值给全局变量
    candleSeries.setData(allCandleData)
    lastCandleData = allCandleData[allCandleData.length - 1] || null;

    const eventRes = await axios.get(`${API}/chart/events`, {
        params: {
            bot_id: botId.value,
            pair: pair.value,
            dry_run: modeStore.isSimulation.value
        }
    })

    const eventMarkers = buildMarkers(eventRes.data || [], allCandleData)
    markerApi.setMarkers(eventMarkers)

    startAutoRefresh()

    // ★ 必须先解绑，再绑定，防止切周期时重复触发
    chart.timeScale().unsubscribeVisibleLogicalRangeChange(handleScroll)
    chart.timeScale().subscribeVisibleLogicalRangeChange(handleScroll)
}

const handleScroll = async (logicalRange) => {
    if (!logicalRange || loadingHistory || !hasMoreHistory) return

    if (logicalRange.from < 5) {
        loadingHistory = true

        try {
            const oldestCandle = allCandleData[0]
            if (!oldestCandle) return

            const res = await axios.get(`${API}/chart/candles`, {
                params: {
                    pair: pair.value,
                    timeframe: timeframe.value,
                    end_time: oldestCandle.time * 1000
                }
            })

            if (!res.data || res.data.length === 0) {
                hasMoreHistory = false
                return
            }

            const olderData = res.data.map(c => ({
                time: Number(Math.floor(c.time / 1000)),
                open: Number(c.open),
                high: Number(c.high),
                low: Number(c.low),
                close: Number(c.close)
            }))

            // 过滤掉重叠的数据，只保留全新的老数据
            const newData = olderData.filter(od =>
                !allCandleData.some(ad => ad.time === od.time)
            )

            if (newData.length > 0) {
                // 记录当前可视范围，防止 setData 后图表跳回最右边
                const currentRange = chart.timeScale().getVisibleLogicalRange()

                allCandleData = [...newData, ...allCandleData]
                candleSeries.setData(allCandleData)

                // 补全参数并重绘事件
                const eventRes = await axios.get(`${API}/chart/events`, {
                    params: {
                        bot_id: botId.value,
                        pair: pair.value,
                        dry_run: modeStore.isSimulation.value
                    }
                })
                const eventMarkers = buildMarkers(eventRes.data || [], allCandleData)
                markerApi.setMarkers(eventMarkers)

                // ★ 恢复视口位置（加上新加载的 K 线数量，让它停留在刚才看的地方）
                if (currentRange) {
                    // 加上 try-catch 防止设置越界导致的图表崩溃
                    try {
                        chart.timeScale().setVisibleLogicalRange({
                            from: Math.max(0, currentRange.from + newData.length),
                            to: currentRange.to + newData.length
                        })
                    } catch (e) {
                        console.warn("恢复视口失败:", e)
                    }
                }
            }

        } catch (e) {
            console.error("加载历史数据失败", e)
        } finally {
            loadingHistory = false
        }
    }
}

watch(modeStore.mode, async () => {
    botId.value = null
    pairs.value = []
    pair.value = ""
    strategyPositions.value = []
    await loadBots()
})

// =========================================================
// 事件 → marker
// =========================================================

function parseEventTime(time) {
    if (!time) return null
    // API timestamps are UTC. Explicitly mark naive values as UTC instead of
    // letting the browser interpret them in the user's local timezone.
    const normalized = typeof time === "string" &&
        !/[zZ]|[+-]\d{2}:?\d{2}$/.test(time)
        ? `${time}Z`
        : time
    const date = new Date(normalized)
    const t = Math.floor(date.getTime() / 1000)
    return Number.isFinite(t) ? t : null
}

// Return the candle containing the event, never the nearest candle.
function findCandleTime(targetTime, candleData) {
    if (!candleData.length) return null;
    const first = candleData[0].time
    const last = candleData[candleData.length - 1].time
    if (targetTime < first) return null
    if (targetTime >= last) return last

    let left = 0
    let right = candleData.length - 1
    while (left <= right) {
        const mid = Math.floor((left + right) / 2)
        if (candleData[mid].time <= targetTime) {
            left = mid + 1
        } else {
            right = mid - 1
        }
    }
    return right >= 0 ? candleData[right].time : null
}

function buildMarkers(rawEvents, candleData) {
    if (!candleData.length) return []

    // 手动开仓时间桶（30m）
    const manualEntryTimes = rawEvents
        .filter(e => e.event_type === "manual_entry")
        .map(e => parseEventTime(e.candle_time || e.time))
        .filter(t => t !== null)

    const isSignalFromManualEntry = (e) => {
        if (e.event_type !== "signal") return false
        const sigTime = parseEventTime(e.candle_time || e.time || e.created_at)
        if (sigTime === null) return false
        const sigBucket = Math.floor(sigTime / 1800)
        return manualEntryTimes.some(mt => Math.floor(mt / 1800) === sigBucket)
    }

    const filteredEvents = rawEvents.filter(e => !isSignalFromManualEntry(e))

    const normalMarkers = []
    const gridBuckets = {}

    filteredEvents.forEach(e => {
        // 1. 获取事件时间
        const isFillEvent = [
            'grid_entry', 'grid_add', 'grid_sell', 'grid_reduce',
            'manual_entry', 'manual_add', 'manual_reduce', 'manual_exit',
            'dca', 'trend_add', 'kdj_reduce'
        ].includes(e.event_type)
        // Fill callbacks carry the actual execution time in `time`. The
        // candle_time field is retained for legacy events only.
        let markerTime = isFillEvent
            ? (parseEventTime(e.time) ?? parseEventTime(e.candle_time))
            : (parseEventTime(e.candle_time) ?? parseEventTime(e.time))
        if (markerTime === null) return

        // 2. Assign the event to the candle that contains the fill time.
        const candleTime = findCandleTime(markerTime, candleData)
        if (candleTime === null) return

        // 3. 过滤中间信号
        // 我们只关心真实的成交（entry/add/sell），不画触发信号
        if (e.event_type === 'grid_entry_signal') return;

        const isGridEvent = ['grid_entry', 'grid_add', 'grid_sell', 'grid_reduce'].includes(e.event_type)

        if (!isGridEvent) {
            const config = buildMarkerConfig(e)
            if (config) {
                normalMarkers.push({ ...config, time: Number(candleTime) })
            }
            return
        }

        // 4. 不再合并：保持首仓（grid_entry）和加仓（grid_add）独立
        // 这样首仓会画一个单独的粉红色箭头，加仓画蓝色箭头
        const aggType = e.event_type;

        // 5. 聚合 Key 改为：K线时间 + 类型
        // 同一根 K 线内，无论是首仓还是加仓，各自独立聚合
        const bucketKey = `${candleTime}_${aggType}`

        if (!gridBuckets[bucketKey]) {
            gridBuckets[bucketKey] = {
                event_type: aggType, // 保留原始类型
                time: Number(candleTime),
                prices: [],
                amount: 0,
                message: e.message,
                candle_time: e.candle_time,
                created_at: e.created_at
            }
        }

        gridBuckets[bucketKey].prices.push(Number(e.price || 0))
        gridBuckets[bucketKey].amount += Number(e.amount || 0)
    })

    // 处理聚合后的网格事件
    Object.values(gridBuckets).forEach(b => {
        const avgPrice = (b.prices.reduce((sum, p) => sum + p, 0) / b.prices.length).toFixed(4)

        // ★ 修复：不再强制改写 message，如果数量 > 1，附加在后缀上
        let msgText = b.message
        if (b.prices.length > 1 && b.event_type === 'grid_add') {
            msgText = `网格加仓 (共${b.prices.length}笔)`
        } else if (b.prices.length > 1 && b.event_type === 'grid_entry') {
            msgText = `网格首仓 (共${b.prices.length}笔)`
        } else if (b.prices.length > 1 && (b.event_type === 'grid_reduce' || b.event_type === 'grid_sell')) { // ★ 新增这里
            msgText = `网格减仓 (共${b.prices.length}笔)`
        }

        const aggEvent = {
            event_type: b.event_type,
            time: b.time,
            price: avgPrice,
            amount: b.amount.toFixed(2),
            message: msgText, // 使用修正后的文案
            count: b.prices.length,
            candle_time: b.candle_time,
            created_at: b.created_at
        }

        const config = buildMarkerConfig(aggEvent)
        if (config) {
            normalMarkers.push({ ...config, time: Number(b.time) })
        }
    })

    // 同一根 K 线上的不同成交都保留，避免漏掉真实订单标记。
    const finalMarkers = []
    const timeMap = new Map()

    normalMarkers.forEach(m => {
        const key = `${m.time}`
        if (!timeMap.has(key)) {
            timeMap.set(key, [])
        }
        timeMap.get(key).push(m)
    })

    timeMap.forEach((markers, time) => {
        markers.forEach(m => {
            finalMarkers.push(m)
        })
    })

    // 按时间排序返回
    return finalMarkers.sort((a, b) => a.time - b.time)

}

function buildMarkerConfig(e) {
    const countSuffix = e.count && e.count > 1 ? ` x${e.count}` : ''
    const priceStr = e.price ? e.price : ''

    switch (e.event_type) {
        case "signal":
            return { position: "belowBar", color: "#673ab7", shape: "arrowUp", text: `信号开仓 ${priceStr}`, size: 2 }
        case "manual_entry":
        case "manual_add":
            return { position: "belowBar", color: "#f44336", shape: "arrowUp", text: `${e.message || "手动开仓/加仓成交"} ${priceStr}`, size: 2,
                title: `价格:${priceStr || '-'}\n数量:${e.amount ?? '-'}` }
        case "dca":
            return { position: "belowBar", color: "#f44336", shape: "arrowUp", text: `DCA加仓 ${priceStr}`, size: 1,
                title: `价格:${priceStr}\n数量:${e.amount}` }
        case "trend_add":
            return { position: "belowBar", color: "#f44336", shape: "arrowUp", text: `趋势加仓 ${priceStr}`,
                title: `价格:${priceStr}\n数量:${e.amount}` }
        case "kdj_reduce":
            return { position: "aboveBar", color: "#00c853", shape: "arrowDown", text: `KDJ减仓 ${priceStr}`,
                title: `价格:${priceStr}\n数量:${e.amount}` }
        case "grid_entry":  // ★ 首仓标记
            return {
                position: "belowBar",
                color: "#f44336",
                shape: "arrowUp",
                text: e.message || `网格首仓 ${priceStr}`, // 显示“网格首仓”
                size: 3, // 稍微放大一点
                title: `首仓成交价:${priceStr}\n数量:${e.amount}`
            }
        case "grid_add":
            return {
                position: "belowBar",
                // 如果你想完全统一颜色，可以全用 "#2196f3"
                // 如果首仓要突出，可以根据 e.message 里的关键字判断，但由于上面聚合了，建议统一用蓝色，带上 xN 后缀即可
                color: "#f44336",
                shape: "arrowUp",
                text: `网格加仓 ${priceStr}`,
                title: `均价:${priceStr}\n总量:${e.amount}`,
                size: 2
            }
        case "grid_reduce":
            return {
                position: "aboveBar",
                color: "#00c853",
                shape: "arrowDown",
                text: `网格减仓 ${priceStr}`,
                title: `价格:${priceStr}\n数量:${e.amount}`
            }
        case "grid_sell":
        case "manual_reduce":
        case "manual_exit":
            return {
                position: "aboveBar",
                color: "#00c853",
                shape: "arrowDown",
                text: `${e.message || "手动减仓/平仓成交"} ${priceStr}`,
                title: `价格:${priceStr}\n数量:${e.amount}`,
                size: 2
            }
        case "tp":
            return { position: "aboveBar", color: "#00c853", shape: "arrowDown", text: `${e.message || "TP"} ${priceStr}` }
        case "sl":
            return { position: "aboveBar", color: "#00c853", shape: "arrowDown", text: `SL ${priceStr}` }
        case "stop_loss":
            return { position: "aboveBar", color: "#00c853", shape: "arrowDown", text: `止损平仓 ${priceStr}`,
                title: `价格:${priceStr}\n数量:${e.amount}`, size: 2 }
        case "global_tp":
            return { position: "aboveBar", color: "#00c853", shape: "arrowDown", text: `全局止盈 ${priceStr}`,
                title: `价格:${priceStr}\n数量:${e.amount}\n${e.message || ""}`, size: 3 }
        case "global_sl":
            return { position: "aboveBar", color: "#00c853", shape: "arrowDown", text: `全局止损 ${priceStr}`,
                title: `价格:${priceStr}\n数量:${e.amount}\n${e.message || ""}`, size: 3 }
        default:
            return null
    }
}

// =========================================================
// 生命周期
// =========================================================

onMounted(async () => {
    chart = createChart(chartRef.value, {
        localization: {
            timeFormatter: (time) => new Date(time * 1000).toLocaleString("zh-CN", { timeZone: "Asia/Shanghai" })
        },
        width: chartRef.value.clientWidth,
        height: 700,
        layout: { background: { color: "#ffffff" }, textColor: "#333" },
        grid: { vertLines: { color: "#f0f0f0" }, horzLines: { color: "#f0f0f0" } },
        timeScale: {
            timeVisible: true,
            secondsVisible: false,
            tickMarkFormatter: (time) => {
                const d = new Date(time * 1000)
                return d.toLocaleString("zh-CN", {
                    timeZone: "Asia/Shanghai",
                    month: "2-digit", day: "2-digit",
                    hour: "2-digit", minute: "2-digit"
                })
            },
            rightOffset: 0,
            shiftVisibleRangeOnNewBar: false,
            fixRightEdge: false,
            lockVisibleTimeRangeOnResize: true
        }
    })

    candleSeries = chart.addSeries(CandlestickSeries)
    markerApi = createSeriesMarkers(candleSeries, [])

    await loadBots()
})

onUnmounted(() => {
    if (refreshTimer) clearInterval(refreshTimer)
    // ★ 新增：解绑
    if (chart) {
        chart.timeScale().unsubscribeVisibleLogicalRangeChange(handleScroll)
        chart.remove()
    }
})

// 支持 ?botId=1&pair=BTC/USDT:USDT 这种深链
watch(
    () => route.query,
    async (query) => {
        if (query.botId && Number(query.botId) !== botId.value) {
            botId.value = Number(query.botId)
            await loadPairs()
            return
        }
        if (query.pair && query.pair !== pair.value) {
            pair.value = query.pair
            await loadChart()
        }
    },
    { deep: true }
)

</script>

<style scoped>

.chart {

    margin-top: 20px;

    width: 100%;

    height: 700px;

    border: 1px solid #ddd;
}

.position-card{

    margin-top:20px;
}

.position-list{

    display:flex;

    flex-wrap:wrap;

    gap:12px;
}

.position-card{

    margin-top:20px;
}

.position-card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}


.profit{

    color:#67c23a;
    font-weight:700;
}

.loss{

    color:#f56c6c;
    font-weight:700;
}

</style>