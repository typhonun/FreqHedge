<template>
<el-row :gutter="20" style="margin-top:20px">

    <!-- 多头配置 -->
    <el-col :span="12">
        <el-card>

            <template #header>
                <div class="card-title">
                    📈 多头配置
                </div>
            </template>

            <el-form label-width="120px">

                <el-row :gutter="20">

                    <el-col :span="12">
                        <el-form-item label="初始资金">
                            <el-input-number
                                v-model="longConfig.dry_run_wallet"
                                style="width:100%"
                                :min="10"
                                :max="1000000"
                                :step="10"
                                :precision="2"
                            />
                        </el-form-item>
                    </el-col>

                    <el-col :span="12">
                        <el-form-item label="开仓金额">
                            <el-input-number
                                v-model="longConfig.stake_amount"
                                style="width:100%"
                                :min="1"
                                :max="10000"
                                :step="1"
                                :precision="2"
                            />
                            <!-- ★ 实时上限提示 -->
                            <div
                                class="form-tip"
                                :class="{ 'form-tip--error': longStakeExceeded }"
                            >
                                上限 {{ maxStakeLong.toFixed(2) }} USDT（初始资金 × 资金利用率）
                            </div>
                        </el-form-item>
                    </el-col>

                </el-row>

                <el-row :gutter="20">

                    <el-col :span="12">
                        <el-form-item label="资金利用率">
                            <!-- ★ 改为小数口径 0.01 ~ 1.00 -->
                            <el-input-number
                                v-model="longConfig.max_usage"
                                style="width:100%"
                                :min="0.01"
                                :max="1"
                                :step="0.05"
                                :precision="2"
                            />
                        </el-form-item>
                    </el-col>

                    <el-col :span="12">
                        <el-form-item label="持仓杠杆">
                            <el-input-number
                                v-model="longConfig.leverage"
                                style="width:100%"
                                :min="1"
                                :max="100"
                                :step="1"
                                :precision="0"
                            />
                        </el-form-item>
                    </el-col>

                    <el-col :span="12">
                        <el-form-item label="最大持仓">
                            <el-input-number
                                v-model="longConfig.max_open_trades"
                                style="width:100%"
                                :min="1"
                                :max="50"
                                :step="1"
                                :precision="0"
                            />
                        </el-form-item>
                    </el-col>


                    <el-divider content-position="left">多空失衡控制</el-divider>

                    <el-form-item label="启用持仓差限制">
                        <el-switch v-model="longConfig.imbalance_long_enable" />
                    </el-form-item>

                    <el-form-item
                        label="持仓差上限"
                        v-if="longConfig.imbalance_long_enable"
                    >
                        <el-input-number
                            v-model="longConfig.imbalance_long_count"
                            style="width:100%"
                            :min="1"
                            :max="20"
                            :step="1"
                            :precision="0"
                        />
                        <div class="form-tip">多单比空单多 {{ longConfig.imbalance_long_count }} 个时，暂停开多</div>
                    </el-form-item>

                </el-row>

                <el-form-item label="白名单">
                    <el-input
                        v-model="longWhitelist"
                        type="textarea"
                        :rows="6"
                        resize="none"
                    />
                </el-form-item>

                <el-form-item label="黑名单">
                    <el-input
                        v-model="longBlacklist"
                        type="textarea"
                        :rows="3"
                        resize="none"
                    />
                </el-form-item>

                <div class="save-area">
                    <el-button
                        type="primary"
                        size="large"
                        @click="saveLong"
                    >
                        保存多头配置
                    </el-button>
                </div>

            </el-form>

        </el-card>
    </el-col>

    <!-- 空头配置 -->
    <el-col :span="12">

        <el-card>

            <template #header>
                <div class="card-title">
                    📉 空头配置
                </div>
            </template>

            <el-form label-width="120px">

                <el-row :gutter="20">

                    <el-col :span="12">
                        <el-form-item label="初始资金">
                            <el-input-number
                                v-model="shortConfig.dry_run_wallet"
                                style="width:100%"
                                :min="10"
                                :max="1000000"
                                :step="100"
                                :precision="2"
                            />
                        </el-form-item>
                    </el-col>

                    <el-col :span="12">
                        <el-form-item label="开仓金额">
                            <el-input-number
                                v-model="shortConfig.stake_amount"
                                style="width:100%"
                                :min="1"
                                :max="10000"
                                :step="1"
                                :precision="2"
                            />
                            <!-- ★ 实时上限提示 -->
                            <div
                                class="form-tip"
                                :class="{ 'form-tip--error': shortStakeExceeded }"
                            >
                                上限 {{ maxStakeShort.toFixed(2) }} USDT（初始资金 × 资金利用率）
                            </div>
                        </el-form-item>
                    </el-col>

                </el-row>

                <el-row :gutter="20">

                    <el-col :span="12">
                        <el-form-item label="资金利用率">
                            <!-- ★ 改为小数口径 0.01 ~ 1.00 -->
                            <el-input-number
                                v-model="shortConfig.max_usage"
                                style="width:100%"
                                :min="0.01"
                                :max="1"
                                :step="0.05"
                                :precision="2"
                            />
                        </el-form-item>
                    </el-col>

                    <el-col :span="12">
                        <el-form-item label="持仓杠杆">
                            <el-input-number
                                v-model="shortConfig.leverage"
                                style="width:100%"
                                :min="1"
                                :max="100"
                                :step="1"
                                :precision="0"
                            />
                        </el-form-item>
                    </el-col>

                    <el-col :span="12">
                        <el-form-item label="最大持仓">
                            <el-input-number
                                v-model="shortConfig.max_open_trades"
                                style="width:100%"
                                :min="1"
                                :max="50"
                                :step="1"
                                :precision="0"
                            />
                        </el-form-item>
                    </el-col>


                    <el-divider content-position="left">多空失衡控制</el-divider>

                    <el-form-item label="启用持仓差限制">
                        <el-switch v-model="shortConfig.imbalance_short_enable" />
                    </el-form-item>

                    <el-form-item
                        label="持仓差上限"
                        v-if="shortConfig.imbalance_short_enable"
                    >
                        <el-input-number
                            v-model="shortConfig.imbalance_short_count"
                            style="width:100%"
                            :min="1"
                            :max="20"
                            :step="1"
                            :precision="0"
                        />
                        <div class="form-tip">空单比多单多 {{ shortConfig.imbalance_short_count }} 个时，暂停开空</div>
                    </el-form-item>

                </el-row>

                <el-form-item label="白名单">
                    <el-input
                        v-model="shortWhitelist"
                        type="textarea"
                        :rows="6"
                        resize="none"
                    />
                </el-form-item>

                <el-form-item label="黑名单">
                    <el-input
                        v-model="shortBlacklist"
                        type="textarea"
                        :rows="3"
                        resize="none"
                    />
                </el-form-item>

                <div class="save-area">
                    <el-button
                        type="primary"
                        size="large"
                        @click="saveShort"
                    >
                        保存空头配置
                    </el-button>
                </div>

            </el-form>

        </el-card>

    </el-col>

</el-row>
</template>

<script setup>

import { onMounted, computed } from "vue"
import { ElMessage } from "element-plus"

import { useCapital } from '@features/dashboard/composables/useCapital.js'

const {
    longConfig,
    shortConfig,
    longWhitelist,
    longBlacklist,
    shortWhitelist,
    shortBlacklist,
    loadConfig,
    saveConfig,
    maxStakeAmount
} = useCapital()

// ★ 实时上限
const maxStakeLong = computed(() => maxStakeAmount("long"))
const maxStakeShort = computed(() => maxStakeAmount("short"))

// ★ 是否超限（用于红字）
const longStakeExceeded = computed(() =>
    Number(longConfig.value.stake_amount ?? 0) > maxStakeLong.value
)
const shortStakeExceeded = computed(() =>
    Number(shortConfig.value.stake_amount ?? 0) > maxStakeShort.value
)

const saveLong = async () => {
    try {
        const res = await saveConfig("long")

        // ★ 校验失败：直接弹错误，不走后续提示
        if (res.error) {
            ElMessage.error(res.error)
            return
        }

        if (res.changed) {
            ElMessage.success("重新加载配置...")
        } else {
            ElMessage.info("已保存")
        }
    } catch {
        ElMessage.error("多头保存失败")
    }
}

const saveShort = async () => {
    try {
        const res = await saveConfig("short")

        if (res.error) {
            ElMessage.error(res.error)
            return
        }

        if (res.changed) {
            ElMessage.success("重新加载配置...")
        } else {
            ElMessage.info("已保存")
        }
    } catch {
        ElMessage.error("空头保存失败")
    }
}

onMounted(() => {
    loadConfig()
})

</script>

<style scoped>

.card-title{
    font-size:16px;
    font-weight:700;
}

.save-area{
    display:flex;
    justify-content:center;
    margin-top:20px;
}

.form-tip {
    font-size: 12px;
    color: #909399;
    margin-top: 4px;
    line-height: 1.4;
}

/* ★ 超限时的红字 */
.form-tip--error {
    color: #f56c6c;
}

</style>