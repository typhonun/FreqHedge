<template>

<el-card>

    <el-row :gutter="20">

        <el-col :span="6">

            <el-select
                v-model="strategy"
                placeholder="选择策略"
                @change="loadPairs"
            >

                <el-option
                    v-for="item in strategies"
                    :key="item"
                    :label="item"
                    :value="item"
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

        当前持仓

    </template>

    <PositionTableCommon
        :positions="strategyPositions"
    />

</el-card>

</template>

<script setup>

import axios from "axios"

import {
    ref,
    onMounted,
    onUnmounted
}
from "vue"

import { createChart, CandlestickSeries } from "lightweight-charts"

import PositionTableCommon
from "@/components/PositionTableCommon.vue"

const API = "http://localhost:9000"

import { useRoute } from "vue-router"

const route = useRoute()

const chartRef = ref(null)

const strategies = ref([])

const pairs = ref([])

const strategyPositions = ref([])

const strategy = ref("")

const pair = ref("")

const timeframe = ref("30m")

const chartCache = new Map()

const timeframes = [
    "1m",
    "5m",
    "15m",
    "30m",
    "1h",
    "4h",
    "1d"
]

const REFRESH_INTERVAL = 2000

let chart = null

let candleSeries = null

let refreshTimer = null

const loadStrategies = async () => {

    const res =
        await axios.get(
            `${API}/chart/strategies`
        )

    strategies.value = res.data

    if (res.data.length) {

        const queryStrategy =
            route.query.strategy

        if (
            queryStrategy &&
            res.data.includes(queryStrategy)
        ) {

            strategy.value =
                queryStrategy

        } else {

            strategy.value =
                res.data[0]
        }

        await loadPairs()
    }
}

const loadPairs = async () => {

    await loadCurrentPositions()

    const res =
        await axios.get(
            `${API}/chart/pairs/${strategy.value}`
        )

    pairs.value = res.data

    if (res.data.length) {

        const queryPair =
            route.query.pair

        if (
            queryPair &&
            res.data.includes(queryPair)
        ) {

            pair.value =
                queryPair

        } else {

            pair.value =
                res.data[0]
        }

        await loadChart()
    }
}

const startAutoRefresh = () => {

    if (refreshTimer) {
        clearInterval(refreshTimer)
    }

    refreshTimer = setInterval(
        updateLastCandle,
        REFRESH_INTERVAL
    )
}

const loadChart = async () => {

    const key =
        `${pair.value}_${timeframe.value}`

    if(chartCache.has(key)){

        candleSeries.setData(
            chartCache.get(key)
        )

        startAutoRefresh()

        return
    }

    const res =
        await axios.get(
            `${API}/chart/candles`,
            {
                params:{
                    pair: pair.value,
                    timeframe: timeframe.value
                }
            }
        )

    const data =
        res.data.map(c => ({

            time: Math.floor(c.time / 1000),
            open: c.open,
            high: c.high,
            low: c.low,
            close: c.close

        }))

    candleSeries.setData(data)

    const visibleBars = 200

    const totalBars = data.length

    const rightSpace = 50

    chart.timeScale().setVisibleLogicalRange({
        from: Math.max(
            totalBars - visibleBars,
            0
        ),

        to:
            totalBars + rightSpace
    })

    chart.applyOptions({
        handleScroll: true,
        handleScale: true
    })

    chartCache.set(
        key,
        data
    )

    candleSeries.setData(data)

    startAutoRefresh()
}

const updateLastCandle = async () => {

    if (!pair.value) return

    try {

        const res =
            await axios.get(
                `${API}/chart/latest`,
                {
                    params: {
                        pair: pair.value,
                        timeframe: timeframe.value
                    }
                }
            )

        candleSeries.update({

            time: Math.floor(
                res.data.time / 1000
            ),
            open: res.data.open,
            high: res.data.high,
            low: res.data.low,
            close: res.data.close

        })

    } catch (e) {

        console.error(
            "update candle error",
            e
        )
    }
}

const loadCurrentPositions = async () => {

    const res =
        await axios.get(
            `${API}/chart/strategy-positions/${strategy.value}`
        )

    strategyPositions.value = res.data
}

onMounted(async () => {

    chart = createChart(
        chartRef.value,
        {
            width: chartRef.value.clientWidth,
            height: 700,

            layout: {
                background: {
                    color: "#ffffff"
                },
                textColor: "#333"
            },

            grid: {
                vertLines: {
                    color: "#f0f0f0"
                },
                horzLines: {
                    color: "#f0f0f0"
                }
            },

            timeScale: {

                timeVisible: true,

                secondsVisible: false,

                tickMarkFormatter: (time) => {

                    const d =
                        new Date(time * 1000)

                    return d.toLocaleString(
                        "zh-CN",
                        {
                            month: "2-digit",
                            day: "2-digit",
                            hour: "2-digit",
                            minute: "2-digit"
                        }
                    )
                },

                rightOffset: 0,

                shiftVisibleRangeOnNewBar: false,

                fixRightEdge: false,

                lockVisibleTimeRangeOnResize: true
            }
        }
    )

    candleSeries =
        chart.addSeries(
            CandlestickSeries
        )

    await loadStrategies()
})

onUnmounted(() => {

    if (refreshTimer) {
        clearInterval(refreshTimer)
    }
})

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

.profit{

    color:#67c23a;
    font-weight:700;
}

.loss{

    color:#f56c6c;
    font-weight:700;
}

</style>