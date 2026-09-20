<template>

<el-card>

    <h2>已平仓交易</h2>

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
            label="平仓金额 (USDT)"
            :formatter="formatNumber"
        />

        <el-table-column
            prop="open_date"
            label="開倉時間"
            :formatter="formatOpenDate"
        />

        <el-table-column
            prop="close_date"
            label="平倉時間"
            :formatter="formatCloseDate"
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
            label="收益 (USDT)"
            :formatter="formatNumber"
        />

        <el-table-column
            prop="exit_reason"
            label="平倉原因"
            :formatter="formatExitReason"
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

    const merged = [
        ...longs,
        ...shorts
    ]

    // 按平仓时间倒序，最近的排最上面
    return merged.sort((a, b) => {

        const ta = Number(
            a.close_timestamp || a.close_fill_timestamp || 0
        )

        const tb = Number(
            b.close_timestamp || b.close_fill_timestamp || 0
        )

        return tb - ta
    })
})

const EXIT_REASON_MAP = {
    force_exit: "强制退出",
    roi: "ROI止盈",
    stop_loss: "止损",
    trailing_stop_loss: "移动止损",
    custom_exit: "自定义退出",
    partial_exit: "部分退出",
    exit_signal: "信号退出",
    emergency_exit: "紧急退出",
    liquidation: "爆仓",
    exit_timeout: "超时退出",
}

const formatExitReason = (row, column, value) => {

    if (!value) {
        return "-"
    }

    const key = String(value).toLowerCase()

    return EXIT_REASON_MAP[key] || value
}

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

const formatTimestamp = (ts, fallbackStr) => {

    if (ts) {
        const date = new Date(Number(ts))

        if (!isNaN(date.getTime())) {
            return formatDateTime(date)
        }
    }

    if (!fallbackStr) {
        return "-"
    }

    const parsed = new Date(String(fallbackStr).replace(" ", "T"))

    if (!isNaN(parsed.getTime())) {
        return formatDateTime(parsed)
    }

    return fallbackStr
}

const formatDateTime = (date) => {

    const pad = (n) => String(n).padStart(2, "0")

    return (
        `${date.getFullYear()}-` +
        `${pad(date.getMonth() + 1)}-` +
        `${pad(date.getDate())} ` +
        `${pad(date.getHours())}:` +
        `${pad(date.getMinutes())}:` +
        `${pad(date.getSeconds())}`
    )
}

const formatOpenDate = (row, column, value) => {
    return formatTimestamp(
        row.open_timestamp || row.open_fill_timestamp,
        value
    )
}

const formatCloseDate = (row, column, value) => {
    return formatTimestamp(
        row.close_timestamp,
        value
    )
}

</script>