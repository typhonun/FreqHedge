<template>

<el-table
    :data="normalizedPositions"
    row-key="trade_id"
    border
    stripe
>

    <el-table-column
        prop="pair"
        label="交易對"
    />

    <el-table-column
        prop="side"
        label="方向"
    />

    <el-table-column
        prop="stake_amount"
        label="本金"
        :formatter="formatNumber"
    />

    <el-table-column
        prop="leverage"
        label="杠杆"
    />

    <el-table-column
        prop="open_rate"
        label="開倉價"
    />

    <el-table-column
        prop="current_rate"
        label="当前价"
    />

    <el-table-column
        prop="profit_pct"
        label="收益%"
        :formatter="formatPercent"
    />

    <el-table-column
        prop="total_profit_abs"
        label="收益USDT"
        :formatter="formatNumber"
    />

    <el-table-column
        prop="profit_abs"
        label="浮盈USDT"
        :formatter="formatNumber"
    />

    <el-table-column
        prop="open_date"
        label="開倉時間"
    />

</el-table>

</template>

<script setup>

import { computed } from "vue"

const props = defineProps({

    positions: {

        type: [Array, Object],

        default: () => []
    }
})

const normalizedPositions = computed(() => {

    /*
        Charts.vue:
        [
            {...},
            {...}
        ]

        Dashboard:
        {
            long:[...],
            short:[...]
        }
    */

    if (Array.isArray(props.positions)) {

        return props.positions
    }

    const longs =
        props.positions?.long || []

    const shorts =
        props.positions?.short || []

    return [

        ...longs.map(item => ({
            ...item,
            side: "LONG"
        })),

        ...shorts.map(item => ({
            ...item,
            side: "SHORT"
        }))
    ]
})

const formatNumber = (
    row,
    column,
    value
) => {

    if (
        value === null ||
        value === undefined
    ){
        return "-"
    }

    return Number(value)
        .toFixed(2)
}

const formatPercent = (
    row,
    column,
    value
) => {

    if (
        value === null ||
        value === undefined
    ){
        return "-"
    }

    return `${Number(value).toFixed(2)}%`
}

</script>