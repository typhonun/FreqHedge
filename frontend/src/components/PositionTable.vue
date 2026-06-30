<template>

<el-card>

    <h2>目前持倉</h2>

        <el-table
            :data="tableData"
            row-key="trade_id"
            border
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
        />

        <el-table-column
            prop="hold_hours"
            label="持倉時間"
        />

    </el-table>

</el-card>

</template>

<script setup>

import { computed } from "vue"

const props = defineProps({
    positions: {
        type: Object,
        default: () => ({
            long: [],
            short: []
        })
    }
})

const calcHours = (dateStr) => {

    const diff =
        Date.now() -
        new Date(dateStr).getTime()

    return (diff / 3600000).toFixed(1)
}

const tableData = computed(() => {

    const longs =
        props.positions?.long || []

    const shorts =
        props.positions?.short || []

    return [
        ...longs.map(item => ({
            ...item,
            side: "LONG",
            hold_hours: calcHours(item.open_date)
        })),

        ...shorts.map(item => ({
            ...item,
            side: "SHORT",
            hold_hours: calcHours(item.open_date)
        }))
    ]
})

const formatNumber = (row, column, value) => {

    if (value === null || value === undefined)
        return "-"

    return Number(value).toFixed(4)
}

const formatPercent = (row, column, value) => {

    if (value === null || value === undefined)
        return "-"

    return `${Number(value).toFixed(2)}%`
}

</script>