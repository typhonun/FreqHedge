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
            time: Math.floor(res.data.time / 1000),
            open: res.data.open,
            high: res.data.high,
            low: res.data.low,
            close: res.data.close
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

    const data = res.data.map(c => ({
        time: Math.floor(c.time / 1000),
        open: c.open,
        high: c.high,
        low: c.low,
        close: c.close
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

    return filteredEvents.map(e => {
        const config = buildMarkerConfig(e)
        if (!config) return null

        let markerTime =
            parseEventTime(e.candle_time) ??
            parseEventTime(e.time) ??
            parseEventTime(e.created_at) ??
            parseEventTime(e.current_time)

        if (markerTime === null) {
            console.warn("事件无时间", e)
            return null
        }

        // 找最接近的 K 线
        const nearest = candleData.reduce((prev, curr) =>
            Math.abs(curr.time - markerTime) < Math.abs(prev.time - markerTime)
                ? curr : prev
        )

        return { time: nearest.time, ...config }
    }).filter(Boolean)
}

function buildMarkerConfig(e) {
    switch (e.event_type) {
        case "signal":
            return { position: "belowBar", color: "#673ab7", shape: "arrowUp", text: `信号开仓 ${e.price}`, size: 2 }
        case "manual_entry":
            return { position: "belowBar", color: "#9c27b0", shape: "arrowUp", text: `手动开仓 ${e.price}`, size: 2,
                title: `价格:${e.price ?? '-'}\n数量:${e.amount ?? '-'}` }
        case "dca":
            return { position: "belowBar", color: "#2196f3", shape: "arrowUp", text: `DCA加仓 ${e.price}`, size: 1,
                title: `价格:${e.price}\n数量:${e.amount}` }
        case "trend_add":
            return { position: "belowBar", color: "#00bcd4", shape: "arrowUp", text: `趋势加仓 ${e.price}`,
                title: `价格:${e.price}\n数量:${e.amount}` }
        case "kdj_reduce":
            return { position: "aboveBar", color: "#9c27b0", shape: "arrowDown", text: `KDJ减仓 ${e.price}`,
                title: `价格:${e.price}\n数量:${e.amount}` }
        case "grid_add":
            return { position: "belowBar", color: "#4caf50", shape: "arrowUp", text: `网格加仓 ${e.price}`,
                title: `价格:${e.price}\n数量:${e.amount}` }
        case "grid_sell":
            return { position: "aboveBar", color: "#e91e63", shape: "arrowDown", text: `网格减仓 ${e.price}`,
                title: `价格:${e.price}\n数量:${e.amount}` }
        case "tp":
            return { position: "aboveBar", color: "#ff9800", shape: "arrowDown", text: `${e.message || "TP"} ${e.price}` }
        case "sl":
            return { position: "aboveBar", color: "#f44336", shape: "arrowDown", text: `SL ${e.price}` }
        case "stop_loss":
            return { position: "aboveBar", color: "#f44336", shape: "arrowDown", text: `止损平仓 ${e.price}`,
                title: `价格:${e.price}\n数量:${e.amount}`, size: 2 }
        case "global_tp":
            return { position: "aboveBar", color: "#00c853", shape: "arrowDown", text: `全局止盈 ${e.price}`,
                title: `价格:${e.price}\n数量:${e.amount}\n${e.message || ""}`, size: 3 }
        case "global_sl":
            return { position: "aboveBar", color: "#d50000", shape: "arrowDown", text: `全局止损 ${e.price}`,
                title: `价格:${e.price}\n数量:${e.amount}\n${e.message || ""}`, size: 3 }
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