<template>

<el-table
    :data="normalizedPositions"
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
        label="本金USDT"
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
        prop="round_minutes"
        label="本轮时间"
    >
        <template #default="scope">
            {{ formatDuration(scope.row.round_minutes) }}
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

    <!-- 移除 label-width，改用 CSS 控制整体居中 -->
    <el-form class="action-form">
        <el-form-item label="操作">
            <el-select v-model="actionForm.action" style="width:220px">
                <el-option label="市价退出" value="market_exit" />
                <el-option label="限价退出" value="limit_exit" />
                <el-option label="立即加仓" value="increase" />
            </el-select>
        </el-form-item>

        <el-form-item v-if="actionForm.action==='limit_exit'" label="限价">
            <el-input-number v-model="actionForm.price" style="width:220px" />
        </el-form-item>

        <el-form-item label="数量(USDT)">
            <el-input-number
                v-model="actionForm.amount_usdt"
                :min="Number(actionMinAmount) || 0"
                :max="Number(actionMaxAmount) || 0"
                :step="Number(amountStep) || 1"
                controls-position=""
                @change="updatePercentByAmount"
                style="width: 220px"
            />
        </el-form-item>

        <div class="extra-controls">
            <el-slider
                v-model="displayPercent"
                :min="0"
                :max="100"
                :disabled="actionMaxAmount <= actionMinAmount"
            />
        </div>
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

import { computed, ref, watch } from "vue"
import axios from "axios"
import { ElMessage } from "element-plus"
import { useRouter } from "vue-router"

const API = "http://localhost:9000"
const router = useRouter()

const dialogVisible = ref(false)
const currentTrade = ref(null)
const submitting = ref(false)

const fullAmount = ref(0)
const increaseMinNotional = ref(10)
const increaseMaxNotional = ref(0)

const actionForm = ref({
    action: "market_exit",
    amount_usdt: 0,
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
        const longs = props.positions?.long || []
        const shorts = props.positions?.short || []
        result = [
            ...longs.map(item => ({ ...item, side: "LONG" })),
            ...shorts.map(item => ({ ...item, side: "SHORT" }))
        ]
    }
    return result.sort(
        (a, b) => Number(b.total_profit_abs || 0) - Number(a.total_profit_abs || 0)
    )
})

const formatNumber = (row, column, value) => {
    if (value === null || value === undefined) return "-"
    return Number(value).toFixed(2)
}

const formatPrice = (row, column, value) => {
    if (value === null || value === undefined) return "-"
    return Number(Number(value).toFixed(4))
}

const formatPercent = (row, column, value) => {
    if (value === null || value === undefined) return "-"
    return `${Number(value).toFixed(2)}%`
}

const openActionDialog = (row) => {
    currentTrade.value = row
    const baseAmount = Number(row.amount || row.base_amount || 0)
    const currentRate = Number(row.current_rate || row.open_rate || 0)
    fullAmount.value = Number((baseAmount * currentRate).toFixed(2)) || 0 // ★ 兜底 0

    actionForm.value = {
        action: "market_exit",
        amount_usdt: fullAmount.value || 0, // ★ 兜底 0
        price: null
    }
    dialogVisible.value = true
    loadIncreaseLimits(row)
}

const loadIncreaseLimits = async row => {
    increaseMinNotional.value = 10
    increaseMaxNotional.value = 0
    if (!row?.bot_id || !row?.pair) return
    try {
        const { data } = await axios.get(`${API}/position/action_limits`, {
            params: { bot_id: row.bot_id, side: row.side, pair: row.pair }
        })
        increaseMinNotional.value = Number(data?.min_notional) || 10
        increaseMaxNotional.value = Number(data?.max_notional) || 0
    } catch (e) {
        ElMessage.error("获取加仓金额限制失败")
    }
}

const submitAction = async () => {
    if (submitting.value) return
    if (!currentTrade.value) return
    if (!actionForm.value.amount_usdt || actionForm.value.amount_usdt <= 0) {
        ElMessage.warning("请输入大于 0 的 USDT 数量"); return
    }
    if (actionForm.value.action === "increase") {
        if (actionForm.value.amount_usdt < increaseMinNotional.value) {
            ElMessage.warning(`加仓金额不能低于 ${increaseMinNotional.value.toFixed(2)} USDT`); return
        }
        if (actionForm.value.amount_usdt > increaseMaxNotional.value) {
            ElMessage.warning(`可用保证金不足，最多可加仓 ${increaseMaxNotional.value.toFixed(2)} USDT`); return
        }
    } else if (actionForm.value.amount_usdt > fullAmount.value) {
        ElMessage.warning("操作数量不能超过当前持仓价值"); return
    }

    if (actionForm.value.action === "limit_exit" && (!actionForm.value.price || actionForm.value.price <= 0)) {
        ElMessage.warning("请输入有效的限价"); return
    }

    submitting.value = true
    try {
        await axios.post(`${API}/position/action`, {
            trade_id: currentTrade.value.trade_id,
            side: currentTrade.value.side,
            action: actionForm.value.action,
            amount_usdt: actionForm.value.amount_usdt,
            price: actionForm.value.price,
            bot_id: currentTrade.value.bot_id,
        })
        ElMessage.success("提交成功")
        dialogVisible.value = false
    } catch (e) {
        ElMessage.error(e.response?.data?.detail || "操作失败")
    } finally {
        submitting.value = false
    }
}

// ★ 动态计算金额的上下限（保留这个版本）
const actionMinAmount = computed(() => {
    const val = actionForm.value.action === "increase" ? increaseMinNotional.value : 0
    return Number(val) || 0
})

const actionMaxAmount = computed(() => {
    const min = actionMinAmount.value // 这里是 10 或者 0
    let max = 0

    if (actionForm.value.action === "increase") {
        max = Number(increaseMaxNotional.value) || 0
    } else {
        max = Number(fullAmount.value) || 0
    }

    // ★ 终极防崩：如果最大值小于最小值，强制让最大值等于最小值。
    // 这样 InputNumber 就不会报错。滑杆也会因为 max === min 而被禁用。
    if (max < min) {
        return min
    }
    return max
})

// ★ 受控滑杆的核心逻辑
const displayPercent = computed({
    get() {
        const val = Number(actionForm.value.amount_usdt) || 0
        const min = actionMinAmount.value
        const max = actionMaxAmount.value

        // 如果 max <= min，或者 max 是无效值，直接返回 0，防止 NaN 传给滑杆
        if (max <= min) return 0;

        let pct = ((val - min) / (max - min)) * 100;
        if (isNaN(pct)) return 0; // 终极防崩
        return Math.min(100, Math.max(0, pct));
    },
    set(percent) {
        const min = actionMinAmount.value
        const max = actionMaxAmount.value
        if (max <= min) return;

        let amount = min + (percent / 100) * (max - min);
        if (isNaN(amount)) return; // 终极防崩
        actionForm.value.amount_usdt = Number(amount.toFixed(2));
    }
})

const updatePercentByAmount = () => {
    if (!actionForm.value.amount_usdt) {
        actionForm.value.amount_usdt = actionMinAmount.value;
    }
}

const amountStep = computed(() => {
    if (actionForm.value.action === "increase") return 1;
    if (!fullAmount.value) return 1;
    return Number((fullAmount.value / 100).toFixed(2));
})

const emit = defineEmits(["selectPair"])

const goToChart = (row) => {
    const strategy = row.side === "SHORT" ? "DcaTpShort" : "DcaTpLong"
    emit("selectPair", { pair: row.pair, strategy })
    router.push({ path: "/charts", query: { pair: row.pair, strategy } })
}

const formatDuration = minutes => {
    if (!minutes) return "-"
    const d = Math.floor(minutes / 1440)
    const h = Math.floor((minutes % 1440) / 60)
    const m = minutes % 60
    if (d > 0) return `${d}天 ${h}小时`
    if (h > 0) return `${h}小时 ${m}分`
    return `${m}分`
}

const formatDate = (row, column, value) => {
    const ts = row.open_timestamp || row.open_fill_timestamp
    if (ts) {
        const date = new Date(Number(ts))
        if (!isNaN(date.getTime())) {
            const pad = (n) => String(n).padStart(2, "0")
            return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${pad(date.getHours())}:${pad(date.getMinutes())}:${pad(date.getSeconds())}`
        }
    }
    if (!value) return "-"
    const parsed = new Date(String(value).replace(" ", "T"))
    if (!isNaN(parsed.getTime())) {
        const pad = (n) => String(n).padStart(2, "0")
        return `${parsed.getFullYear()}-${pad(parsed.getMonth() + 1)}-${pad(parsed.getDate())} ${pad(parsed.getHours())}:${pad(parsed.getMinutes())}:${pad(parsed.getSeconds())}`
    }
    return value
}

// 切换操作类型时的联动
watch(
    () => actionForm.value.action,
    (newAction) => {
        if (newAction === "increase") {
            // 切到加仓：金额变更为最小值
            actionForm.value.amount_usdt = Number(increaseMinNotional.value) || 0
        } else {
            // 切到退出（市价/限价）：金额恢复为持仓总价值
            actionForm.value.amount_usdt = Number(fullAmount.value) || 0

            // 额外处理限价退出的默认价格
            if (newAction === "limit_exit" && !actionForm.value.price) {
                const rate = Number(currentTrade.value?.current_rate || currentTrade.value?.open_rate || 0)
                actionForm.value.price = rate > 0 ? Number(rate.toFixed(4)) : null
            }
        }
    }
)

</script>

<style scoped>
/* 核心：让表单项作为一个整体水平居中 */
.action-form :deep(.el-form-item) {
    display: flex;
    justify-content: center; /* 水平居中 */
    align-items: center;
    margin-bottom: 22px;
}

/* 固定 label 宽度并右对齐，保证输入框对齐 */
.action-form :deep(.el-form-item__label) {
    width: 90px !important;
    justify-content: flex-end;
    padding-right: 12px;
}

/* 移除 el-form-item 默认的右侧 margin，配合 Flex 实现绝对居中 */
.action-form :deep(.el-form-item__content) {
    margin-left: 0 !important;
    flex: none;
}

/* 滑杆容器，和输入框同宽 */
.extra-controls {
    width: 300px;
    margin: -10px auto 15px auto; /* 居中 */
}

.amount-tip {
    font-size: 12px;
    color: var(--el-text-color-secondary);
    text-align: center;
    margin-bottom: 8px;
    line-height: 1.4;
}

/* 去除滑杆默认的左右内边距，让它和上方输入框绝对等宽 */
.extra-controls :deep(.el-slider) {
    padding: 0;
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