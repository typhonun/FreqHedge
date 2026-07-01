<template>

<el-card>

    <h2>已平倉交易</h2>

    <el-table
        :data="tableData"
        border
        row-key="trade_id"
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
            label="平仓金额"
            :formatter="formatNumber"
        />

        <el-table-column
            prop="open_date"
            label="開倉時間"
        />

        <el-table-column
            prop="close_date"
            label="平倉時間"
        />

        <el-table-column label="收益%">
            <template #default="{ row }">

                <span
                    :style="{
                        color: row.profit_pct >= 0
                            ? '#67C23A'
                            : '#F56C6C'
                    }"
                >
                    {{ Number(row.profit_pct || 0).toFixed(2) }}%
                </span>

            </template>
        </el-table-column>

        <el-table-column
            prop="profit_abs"
            label="收益USDT"
            :formatter="formatNumber"
        />

        <el-table-column
            prop="exit_reason"
            label="平倉原因"
        />

    </el-table>

</el-card>

</template>

<script setup>

import { computed } from "vue"

const props = defineProps({
    positions: Object
})

const tableData = computed(() => {

    const longs =
        props.positions?.long || []

    const shorts =
        props.positions?.short || []

    return [
        ...longs,
        ...shorts
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
    ) {
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
    ) {
        return "-"
    }

    return `${Number(value).toFixed(2)}%`
}

</script>