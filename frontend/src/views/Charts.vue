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
        @selectPair="changePair"
    />

</el-card>

</template>

<script setup>

import axios from "axios"

import {
    ref,
    onMounted,
    onUnmounted,
    watch
}
from "vue"

import {
    createChart,
    CandlestickSeries,
    createSeriesMarkers
} from "lightweight-charts"

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

let markerApi = null

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

const changePair = async(data)=>{


    // 如果策略变化
    if(strategy.value !== data.strategy){

        strategy.value =
            data.strategy

        await loadPairs()

    }


    // 切换交易对
    if(pair.value !== data.pair){

        pair.value =
            data.pair

        await loadChart()

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

    if(markerApi){

        markerApi.setMarkers([])

    }

    const key =
    `${strategy.value}_${pair.value}_${timeframe.value}`



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
        res.data.map(c=>({

            time:
            Math.floor(
                c.time / 1000
            ),

            open:c.open,
            high:c.high,
            low:c.low,
            close:c.close

        }))



    candleSeries.setData(data)



    /*
    =========================
    加载交易事件
    =========================
    */


    const eventRes =
        await axios.get(
            `${API}/chart/events`,
            {
                params:{
                    strategy:
                    strategy.value,

                    pair:
                    pair.value
                }
            }
        )

    function parseEventTime(time){

        if(!time)
            return null


        let date = new Date(time)


        return Math.floor(
            date.getTime()/1000
        )

    }

    const eventMarkers =
        eventRes.data.map(e=>{


            let config={}


            switch(e.event_type){

                case "filled_entry":

                    config={

                        position:"belowBar",

                        color:"#0066ff",

                        shape:"arrowUp",

                        text:
                        `BUY ${e.price}`

                    }

                break

                case "confirm":

                    config={

                        position:"belowBar",

                        color:"#00c853",

                        shape:"arrowUp",

                        text:
                        `信号开仓 ${e.price}`

                    }

                break

                case "manual_entry":

                    config={

                        position:"belowBar",

                        color:"#9c27b0",

                        shape:"arrowUp",

                        text:"手动开仓",

                        size:2,

                        title:
                        `价格:${e.price ?? '-'}
                        数量:${e.amount ?? '-'}`

                    }

                break

                case "dca":

                    config={

                        position:"belowBar",

                        color:"#2196f3",

                        shape:"arrowUp",

                        text:"DCA加仓",

                        size:1,

                        title:
                            `价格:${e.price}
                            数量:${e.amount}`

                    }

                break

                case "trend_add":

                    config={

                        position:"belowBar",

                        color:"#00bcd4",

                        shape:"arrowUp",

                        text:
                        `趋势加仓 ${e.price}`,

                        title:
                        `价格:${e.price}
                        数量:${e.amount}`

                    }

                break

                case "kdj_reduce":

                    config={

                        position:"aboveBar",

                        color:"#9c27b0",

                        shape:"arrowDown",

                        text:
                        `KDJ减仓 ${e.price}`,

                        title:
                        `价格:${e.price}
                        数量:${e.amount}`

                    }

                break

                case "grid_add":

                    config={

                        position:"belowBar",

                        color:"#4caf50",

                        shape:"arrowUp",

                        text:
                        `网格加仓 ${e.price}`,

                        title:
                        `价格:${e.price}
                        数量:${e.amount}`

                    }

                break


                case "grid_sell":

                    config={

                        position:"aboveBar",

                        color:"#e91e63",

                        shape:"arrowDown",

                        text:
                        `网格减仓 ${e.price}`,

                        title:
                        `价格:${e.price}
                        数量:${e.amount}`

                    }

                break

                case "tp":

                    config={

                        position:
                        "aboveBar",

                        color:
                        "#ff9800",

                        shape:
                        "arrowDown",

                        text:
                        `${e.message || "TP"} ${e.price}`

                    }

                break



                case "sl":

                    config={

                        position:
                        "aboveBar",

                        color:
                        "#f44336",

                        shape:
                        "arrowDown",

                        text:
                        `SL ${e.price}`

                    }

                break

            }

            let markerTime;

            if(e.candle_time){

                markerTime =
                    parseEventTime(
                        e.candle_time
                    )

            }
            else if(e.time){

                markerTime =
                    parseEventTime(
                        e.time
                    )

            }
            else{

                console.warn(
                    "事件没有时间",
                    e
                )

                return null
            }

            const nearest =
                data.reduce(
                    (prev, curr)=>{

                        return Math.abs(curr.time-markerTime)
                            <
                            Math.abs(prev.time-markerTime)
                            ?
                            curr
                            :
                            prev

                    }
                )


            return {

                time:
                nearest.time,

                ...config

            }
        }).filter(Boolean)



    /*
    ======================
    设置标记
    ======================
    */

    console.log(
        "events:",
        eventRes.data
    )

    console.log(
        "markers:",
        eventMarkers
    )

    console.log(
        "candle range:",
        data[0].time,
        data[data.length-1].time
    )

    console.log(
        "marker time:",
        eventMarkers[0]?.time
    )

    if(eventMarkers.length){

        markerApi.setMarkers(
            eventMarkers
        )

    }else{

        console.warn(
            "没有交易事件"
        )

    }



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
            localization:{
                timeFormatter:(time)=>{

                    return new Date(
                        time*1000
                    ).toLocaleString(
                        "zh-CN",
                        {
                            timeZone:"Asia/Shanghai"
                        }
                    )

                }
            },
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
                        new Date(
                            time * 1000
                        )

                    return d.toLocaleString(
                        "zh-CN",
                        {
                            timeZone:"Asia/Shanghai",
                            month:"2-digit",
                            day:"2-digit",
                            hour:"2-digit",
                            minute:"2-digit"
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


    markerApi =
        createSeriesMarkers(
            candleSeries,
            []
        )

    await loadStrategies()
})

onUnmounted(() => {

    if (refreshTimer) {
        clearInterval(refreshTimer)
    }
})

watch(
    ()=>route.query,
    async(query)=>{


        if(query.strategy){

            strategy.value =
                query.strategy

        }


        if(query.pair){

            pair.value =
                query.pair


            await loadChart()

        }

    },
    {
        deep:true
    }
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

.profit{

    color:#67c23a;
    font-weight:700;
}

.loss{

    color:#f56c6c;
    font-weight:700;
}

</style>