<template>
<el-row :gutter="20" style="margin-top:20px">

    <!-- 多头配置 -->
    <el-col :span="12">
        <el-card>

            <template #header>
                多头配置
            </template>

            <el-form label-width="120px">

                <el-form-item label="初始资金">
                    <el-input-number
                        v-model="longConfig.dry_run_wallet"
                    />
                </el-form-item>

                <el-form-item label="下单金额">
                    <el-input-number
                        v-model="longConfig.stake_amount"
                    />
                </el-form-item>

                <el-form-item label="最大持仓">
                    <el-input-number
                        v-model="longConfig.max_open_trades"
                    />
                </el-form-item>

                <el-form-item label="资金利用率">
                    <el-input-number
                        v-model="longConfig.max_usage"
                    />
                </el-form-item>

                <el-form-item label="白名单">
                    <el-input
                        v-model="longWhitelist"
                        type="textarea"
                        :rows="8"
                    />
                </el-form-item>

                <el-form-item label="黑名单">
                    <el-input
                        v-model="longBlacklist"
                        type="textarea"
                        :rows="4"
                    />
                </el-form-item>

                <el-button
                    type="primary"
                    @click="saveLong"
                >
                    保存多头配置
                </el-button>

            </el-form>

        </el-card>
    </el-col>

    <!-- 空头配置 -->
    <el-col :span="12">

        <el-card>

            <template #header>
                空头配置
            </template>

            <el-form label-width="120px">

                <el-form-item label="初始资金">
                    <el-input-number
                        v-model="shortConfig.dry_run_wallet"
                    />
                </el-form-item>

                <el-form-item label="下单金额">
                    <el-input-number
                        v-model="shortConfig.stake_amount"
                    />
                </el-form-item>

                <el-form-item label="最大持仓">
                    <el-input-number
                        v-model="shortConfig.max_open_trades"
                    />
                </el-form-item>

                <el-form-item label="资金利用率">
                    <el-input-number
                        v-model="shortConfig.max_usage"
                    />
                </el-form-item>

                <el-form-item label="白名单">
                    <el-input
                        v-model="shortWhitelist"
                        type="textarea"
                        :rows="8"
                    />
                </el-form-item>

                <el-form-item label="黑名单">
                    <el-input
                        v-model="shortBlacklist"
                        type="textarea"
                        :rows="4"
                    />
                </el-form-item>

                <el-button
                    type="success"
                    @click="saveShort"
                >
                    保存空头配置
                </el-button>

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