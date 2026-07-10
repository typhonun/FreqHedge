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

    <el-table-column
    label="操作"
    width="120"
>

        <template #default="scope">

            <el-button
                size="small"
                type="primary"
                @click="openActionDialog(scope.row)"
            >
                操作
            </el-button>

        </template>

    </el-table-column>

</el-table>


<el-dialog
    v-model="dialogVisible"
    title="持仓操作"
    width="500px"
>

    <el-form>

        <el-form-item label="操作">

            <el-select
                v-model="actionForm.action"
            >

                <el-option
                    label="市价退出"
                    value="market_exit"
                />

                <el-option
                    label="限价退出"
                    value="limit_exit"
                />

                <el-option
                    label="立即加仓"
                    value="increase"
                />

            </el-select>

        </el-form-item>

        <el-form-item
            v-if="actionForm.action==='limit_exit'"
            label="限价"
        >

            <el-input-number
                v-model="actionForm.price"
            />

        </el-form-item>

        <el-form-item
            label="数量(可部分)"
        >

            <el-input-number
                v-model="actionForm.amount"
                :min="0"
            />

        </el-form-item>

    </el-form>

    <template #footer>

        <el-button
            @click="dialogVisible=false"
        >
            取消
        </el-button>

        <el-button
            type="primary"
            :loading="submitting"
            @click="submitAction"
        >
            确定
        </el-button>

    </template>

</el-dialog>

</template>

<script setup>

import { computed } from "vue"

import axios from "axios"

import { ref } from "vue"

import { ElMessage } from "element-plus"

const API =
    "http://localhost:9000"

const dialogVisible =
    ref(false)

const currentTrade =
    ref(null)

const submitting = ref(false)

const actionForm = ref({

    action: "market_exit",

    amount: null,

    price: null
})

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

const openActionDialog = row => {

    currentTrade.value = row

    actionForm.value = {

        action: "market_exit",

        amount: null,

        price: null
    }

    dialogVisible.value = true
}

const submitAction = async () => {

    if (submitting.value) return

    submitting.value = true

    try {

        await axios.post(

            `${API}/position/action`,

            {

                trade_id:
                    currentTrade.value.trade_id,

                side:
                    currentTrade.value.side,

                action:
                    actionForm.value.action,

                amount:
                    actionForm.value.amount,

                price:
                    actionForm.value.price
            }
        )

        ElMessage.success(
            "提交成功"
        )

        dialogVisible.value =
            false

    } catch (e) {

        ElMessage.error(
            e.response?.data?.detail ||
            "操作失败"
        )
    }
    finally {
        submitting.value = false
    }
}

</script>