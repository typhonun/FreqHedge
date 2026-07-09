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
                            />

                        </el-form-item>

                    </el-col>

                    <el-col :span="12">

                        <el-form-item label="下单金额">

                            <el-input-number
                                v-model="longConfig.stake_amount"
                                style="width:100%"
                            />

                        </el-form-item>

                    </el-col>

                </el-row>

                <el-row :gutter="20">

                    <el-col :span="12">

                        <el-form-item label="最大持仓">

                            <el-input-number
                                v-model="longConfig.max_open_trades"
                                style="width:100%"
                            />

                        </el-form-item>

                    </el-col>

                    <el-col :span="12">

                        <el-form-item label="资金利用率">

                            <el-input-number
                                v-model="longConfig.max_usage"
                                style="width:100%"
                            />

                        </el-form-item>

                    </el-col>

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
                            />

                        </el-form-item>

                    </el-col>

                    <el-col :span="12">

                        <el-form-item label="下单金额">

                            <el-input-number
                                v-model="shortConfig.stake_amount"
                                style="width:100%"
                            />

                        </el-form-item>

                    </el-col>

                </el-row>

                <el-row :gutter="20">

                    <el-col :span="12">

                        <el-form-item label="最大持仓">

                            <el-input-number
                                v-model="shortConfig.max_open_trades"
                                style="width:100%"
                            />

                        </el-form-item>

                    </el-col>

                    <el-col :span="12">

                        <el-form-item label="资金利用率">

                            <el-input-number
                                v-model="shortConfig.max_usage"
                                style="width:100%"
                            />

                        </el-form-item>

                    </el-col>

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

import { onMounted } from "vue"
import { ElMessage } from "element-plus"

import { useCapital }
from "../composables/useCapital"

const {

    longConfig,
    shortConfig,

    longWhitelist,
    longBlacklist,

    shortWhitelist,
    shortBlacklist,

    loadConfig,
    saveConfig

} = useCapital()

const saveLong = async () => {

    try {

        await saveConfig("long")

        ElMessage.success(
            "多头配置已保存"
        )

    } catch {

        ElMessage.error(
            "多头保存失败"
        )
    }
}

const saveShort = async () => {

    try {

        await saveConfig("short")

        ElMessage.success(
            "空头配置已保存"
        )

    } catch {

        ElMessage.error(
            "空头保存失败"
        )
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
</style>