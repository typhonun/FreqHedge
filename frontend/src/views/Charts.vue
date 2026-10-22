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

const API = "http://localhost:9000"
const route = useRoute()

const botStore = useBotStore()
const botList = computed(() => botStore.state.bots)

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

    await loadPairs()
}

const onBotChange = async () => {
    // 清空旧数据
    pairs.value = []
    pair.value = ""
    strategyPositions.value = []
    if (candleSeries) candleSeries.setData([])
    if (markerApi) markerApi.setMarkers([])

    await loadPairs()
}

// =========================================================
// 交易对 + 当前持仓
// =========================================================

const loadPairs = async () => {
    if (!botId.value) return

    await loadBotPositions()

    const res = await axios.get(`${API}/chart/pairs/${botId.value}`)
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
        const res = await axios.get(`${API}/chart/bot-positions/${botId.value}`)
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

const startAutoRefresh = () => {
    if (refreshTimer) clearInterval(refreshTimer)
    refreshTimer = setInterval(updateLastCandle, REFRESH_INTERVAL)
}

const updateLastCandle = async () => {
    if (!pair.value || !candleSeries) return
    try {
        const res = await axios.get(`${API}/chart/latest`, {
            params: { pair: pair.value, timeframe: timeframe.value }
        })
        candleSeries.update({
            time: Number(Math.floor(res.data.time / 1000)),
            open: Number(res.data.open),
            high: Number(res.data.high),
            low: Number(res.data.low),
            close: Number(res.data.close)
        })
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

    const res = await axios.get(`${API}/chart/candles`, {
        params: { pair: pair.value, timeframe: timeframe.value }
    })

    // 强制类型转换，防止图表卡死
    const data = res.data.map(c => ({
        time: Number(Math.floor(c.time / 1000)),
        open: Number(c.open),
        high: Number(c.high),
        low: Number(c.low),
        close: Number(c.close)
    }))

    candleSeries.setData(data)

    // 加载交易事件
    const eventRes = await axios.get(`${API}/chart/events`, {
        params: {
            bot_id: botId.value,
            pair: pair.value
        }
    })

    const eventMarkers = buildMarkers(eventRes.data || [], data)
    markerApi.setMarkers(eventMarkers)

    startAutoRefresh()
}

// =========================================================
// 事件 → marker
// =========================================================

function parseEventTime(time) {
    if (!time) return null
    const date = new Date(time)
    const t = Math.floor(date.getTime() / 1000)
    return Number.isFinite(t) ? t : null
}

// 辅助函数：从排好序的 K 线中，二分查找/或直接遍历找最近的 K 线时间戳
function findNearestCandleTime(targetTime, candleData) {
    if (!candleData.length) return null;
    let left = 0;
    let right = candleData.length - 1;

    // 如果超出了范围，直接返回首尾
    if (targetTime <= candleData[left].time) return candleData[left].time;
    if (targetTime >= candleData[right].time) return candleData[right].time;

    // 二分查找
    while (left <= right) {
        const mid = Math.floor((left + right) / 2);
        if (candleData[mid].time === targetTime) return targetTime;
        if (candleData[mid].time < targetTime) {
            left = mid + 1;
        } else {
            right = mid - 1;
        }
    }
    // 比较 left 和 right 哪个离 target 更近
    const timeLeft = candleData[right].time;
    const timeRight = candleData[left].time;
    return (targetTime - timeLeft) < (timeRight - targetTime) ? timeLeft : timeRight;
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
        let markerTime = parseEventTime(e.candle_time) ?? parseEventTime(e.time)
        if (markerTime === null) return

        // 2. 找到最接近的 K 线时间
        const nearestCandleTime = findNearestCandleTime(markerTime, candleData)
        if (!nearestCandleTime) return

        // 3. 过滤中间信号
        // 我们只关心真实的成交（entry/add/sell），不画触发信号
        if (e.event_type === 'grid_entry_signal') return;

        const isGridEvent = ['grid_entry', 'grid_add', 'grid_sell'].includes(e.event_type)

        if (!isGridEvent) {
            const config = buildMarkerConfig(e)
            if (config) {
                normalMarkers.push({ ...config, time: Number(nearestCandleTime) })
            }
            return
        }

        // 4. 统一归类：把 grid_entry 也并入 grid_add 桶，确保同一根 K 线只有一根向上的箭头
        let aggType = e.event_type === 'grid_entry' ? 'grid_add' : e.event_type;

        // 5. 聚合 Key 改为：K线时间 + 方向（买入/卖出）
        // 这样无论加了几格、是不是首仓，同一根 K 线只有一个向上的箭头
        const bucketKey = `${nearestCandleTime}_${aggType}`

        if (!gridBuckets[bucketKey]) {
            gridBuckets[bucketKey] = {
                event_type: aggType,
                time: Number(nearestCandleTime),
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
        const aggEvent = {
            event_type: b.event_type,
            time: b.time,
            price: avgPrice,
            amount: b.amount.toFixed(2),
            message: b.prices.length > 1 ? `网格加仓 (共${b.prices.length}笔)` : b.message,
            count: b.prices.length,
            candle_time: b.candle_time,
            created_at: b.created_at
        }

        const config = buildMarkerConfig(aggEvent)
        if (config) {
            normalMarkers.push({ ...config, time: Number(b.time) })
        }
    })

    return normalMarkers
}

function buildMarkerConfig(e) {
    const countSuffix = e.count && e.count > 1 ? ` x${e.count}` : ''
    const priceStr = e.price ? e.price : ''

    switch (e.event_type) {
        case "signal":
            return { position: "belowBar", color: "#673ab7", shape: "arrowUp", text: `信号开仓 ${priceStr}`, size: 2 }
        case "manual_entry":
            return { position: "belowBar", color: "#9c27b0", shape: "arrowUp", text: `手动开仓 ${priceStr}`, size: 2,
                title: `价格:${priceStr || '-'}\n数量:${e.amount ?? '-'}` }
        case "dca":
            return { position: "belowBar", color: "#2196f3", shape: "arrowUp", text: `DCA加仓 ${priceStr}`, size: 1,
                title: `价格:${priceStr}\n数量:${e.amount}` }
        case "trend_add":
            return { position: "belowBar", color: "#00bcd4", shape: "arrowUp", text: `趋势加仓 ${priceStr}`,
                title: `价格:${priceStr}\n数量:${e.amount}` }
        case "kdj_reduce":
            return { position: "aboveBar", color: "#9c27b0", shape: "arrowDown", text: `KDJ减仓 ${priceStr}`,
                title: `价格:${priceStr}\n数量:${e.amount}` }
        case "grid_entry":  // ★ 新增的首仓标记
            return {
                position: "belowBar",
                color: "#e91e63",  // 用粉红色或醒目颜色区分加仓的绿色
                shape: "arrowUp",
                text: e.message || `网格首仓 ${priceStr}`,
                size: 3, // 稍微放大一点
                title: `首仓成交价:${priceStr}\n数量:${e.amount}`
            }
        case "grid_add":
            return {
                position: "belowBar",
                // 如果你想完全统一颜色，可以全用 "#2196f3"
                // 如果首仓要突出，可以根据 e.message 里的关键字判断，但由于上面聚合了，建议统一用蓝色，带上 xN 后缀即可
                color: "#2196f3",
                shape: "arrowUp",
                text: `网格加仓${countSuffix} ${priceStr}`,
                title: `均价:${priceStr}\n总量:${e.amount}`,
                size: 2
            }
        case "grid_sell":
            return {
                position: "aboveBar",
                color: "#ff9800", // 减仓用橙色
                shape: "arrowDown",
                text: `网格减仓${countSuffix} ${priceStr}`,
                title: `价格:${priceStr}\n数量:${e.amount}`
            }
        case "tp":
            return { position: "aboveBar", color: "#ff9800", shape: "arrowDown", text: `${e.message || "TP"} ${priceStr}` }
        case "sl":
            return { position: "aboveBar", color: "#f44336", shape: "arrowDown", text: `SL ${priceStr}` }
        case "stop_loss":
            return { position: "aboveBar", color: "#f44336", shape: "arrowDown", text: `止损平仓 ${priceStr}`,
                title: `价格:${priceStr}\n数量:${e.amount}`, size: 2 }
        case "global_tp":
            return { position: "aboveBar", color: "#00c853", shape: "arrowDown", text: `全局止盈 ${priceStr}`,
                title: `价格:${priceStr}\n数量:${e.amount}\n${e.message || ""}`, size: 3 }
        case "global_sl":
            return { position: "aboveBar", color: "#d50000", shape: "arrowDown", text: `全局止损 ${priceStr}`,
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