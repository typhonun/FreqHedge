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
    >
        <template #default="scope">

            <el-link
                type="primary"
                :underline="false"
                @click="goToChart(scope.row)"
            >
                {{ scope.row.pair }}
            </el-link>

        </template>
    </el-table-column>

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
        label="开仓价"
        :formatter="formatPrice"
    />

    <el-table-column
        prop="current_rate"
        label="当前价"
        :formatter="formatPrice"
    />

    <el-table-column
        prop="profit_pct"
        label="收益%"
        :formatter="formatPercent"
    />

    <el-table-column
        prop="tp_roi"
        label="目标止盈%"
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
        label="开仓時間"
        :formatter="formatDate"
    />

    <el-table-column
        prop="holding_minutes"
        label="持仓时间"
    >
        <template #default="scope">

            {{ formatDuration(
                scope.row.holding_minutes
            ) }}

        </template>
    </el-table-column>

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
    width="520px"
    align-center
>

    <el-form>

        <el-form-item label="操作">

            <div class="form-center">

                <el-select
                    v-model="actionForm.action"
                    style="width:220px"
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

            </div>

        </el-form-item>

        <el-form-item
            v-if="actionForm.action==='limit_exit'"
            label="限价"
            :formatter="formatPrice"
        >

            <div class="form-center">

                <el-input-number
                    v-model="actionForm.price"
                    style="width:220px"
                />

            </div>

        </el-form-item>

        <el-form-item label="数量">

            <div class="amount-box">

                <el-input-number

                    v-model="actionForm.amount"

                    :min="0"

                    :step="amountStep"

                    controls-position=""

                    @change="updatePercentByAmount"

                />

                <el-slider

                    v-model="actionForm.percent"

                    :min="0"

                    :max="100"

                    @input="updateAmountByPercent"

                />

            </div>

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

import { watch } from "vue"

import { useRouter } from "vue-router"

const API =
    "http://localhost:9000"

const dialogVisible =
    ref(false)

const router = useRouter()

const currentTrade =
    ref(null)

const submitting = ref(false)

const fullAmount = ref(0)

const actionForm = ref({

    action: "market_exit",

    amount: 0,

    percent: 100,

    price: null
})
const props = defineProps({

    positions: {

        type: [Array, Object],

        default: () => []
    }
})

const normalizedPositions = computed(() => {

    let result = []

    if (Array.isArray(props.positions)) {

        result = [...props.positions]

    } else {

        const longs =
            props.positions?.long || []

        const shorts =
            props.positions?.short || []

        result = [

            ...longs.map(item => ({
                ...item,
                side: "LONG"
            })),

            ...shorts.map(item => ({
                ...item,
                side: "SHORT"
            }))
        ]
    }

    return result.sort(
        (a, b) =>
            Number(b.total_profit_abs  || 0) -
            Number(a.total_profit_abs  || 0)
    )
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

const formatPrice = (
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

    return Number(
        Number(value).toFixed(4)
    )
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

    fullAmount.value = Number(
        row.amount ||
        row.base_amount ||
        0
    )

    actionForm.value = {

        action: "market_exit",

        percent: 100,

        amount: fullAmount.value,

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

const updateAmountByPercent = () => {

    actionForm.value.amount = Number(

        (
            fullAmount.value *
            actionForm.value.percent /
            100
        ).toFixed(6)

    )
}

const updatePercentByAmount = () => {

    if (!fullAmount.value)
        return

    actionForm.value.percent = Number(

        (
            actionForm.value.amount /
            fullAmount.value *
            100
        ).toFixed(2)

    )
}

const amountStep = computed(() => {

    if (!fullAmount.value)
        return 1

    return Number(

        (
            fullAmount.value / 100
        ).toFixed(6)

    )
})

const emit = defineEmits([
    "selectPair"
])

const goToChart = (row) => {

    const strategy =
        row.side === "SHORT"
            ? "DcaTpShort"
            : "DcaTpLong"


    emit(
        "selectPair",
        {
            pair: row.pair,
            strategy
        }
    )


    router.push({

        path:"/charts",

        query:{
            pair:row.pair,
            strategy
        }
    })
}

const formatDuration = minutes => {

    if (!minutes)
        return "-"

    const d =
        Math.floor(
            minutes / 1440
        )

    const h =
        Math.floor(
            (minutes % 1440) / 60
        )

    const m =
        minutes % 60

    if (d > 0)
        return `${d}天 ${h}小时`

    if (h > 0)
        return `${h}小时 ${m}分`

    return `${m}分`
}

const formatDate = (row, column, value) => {

    const ts = row.open_timestamp || row.open_fill_timestamp

    if (ts) {
        const date = new Date(Number(ts))

        if (!isNaN(date.getTime())) {

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
    }

    if (!value) {
        return "-"
    }

    const parsed = new Date(String(value).replace(" ", "T"))

    if (!isNaN(parsed.getTime())) {

        const pad = (n) => String(n).padStart(2, "0")

        return (
            `${parsed.getFullYear()}-` +
            `${pad(parsed.getMonth() + 1)}-` +
            `${pad(parsed.getDate())} ` +
            `${pad(parsed.getHours())}:` +
            `${pad(parsed.getMinutes())}:` +
            `${pad(parsed.getSeconds())}`
        )
    }

    return value
}

watch(

    () => actionForm.value.action,

    (newAction) => {

        if (
            newAction === "limit_exit" &&
            !actionForm.value.price
        ) {

            actionForm.value.price =
                +currentTrade.value.current_rate.toFixed(4)
        }
    }

)

</script>

<style scoped>

.amount-box{

    width:100%;

    display:flex;

    flex-direction:column;

    align-items:center;

    gap:12px;
}

.amount-box{

    width:100%;

    display:flex;

    flex-direction:column;

    align-items:center;

    gap:10px;
}

.amount-box{

    width:100%;

    display:flex;

    flex-direction:column;

    align-items:center;

    gap:14px;
}

.amount-box .el-input-number{

    width:220px;

    margin:0 auto;
}

.amount-box :deep(.el-slider){

    width:85%;

    margin:0 auto;
}

.slider-label{

    width:100%;

    display:flex;

    justify-content:space-between;

    font-size:13px;

    color:#909399;
}

.form-center{

    width:100%;

    display:flex;

    justify-content:center;
}

:deep(.el-dialog){

    border-radius:12px;
}

:deep(.el-dialog__header){

    text-align:center;

    font-size:18px;

    font-weight:600;
}

:deep(.el-dialog__footer){

    text-align:center;
}

</style>