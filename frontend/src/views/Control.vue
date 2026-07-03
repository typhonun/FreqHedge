<template>

<div>

    <!-- 第一行 -->
    <el-row
        :gutter="20"
        style="margin-top:20px"
    >

        <!-- 运行控制 -->
        <el-col :span="12">

            <el-card>

                <template #header>
                    运行控制
                </template>

                <div class="checkbox-group">

                    <el-checkbox
                        v-model="enableLong"
                    >
                        多头
                    </el-checkbox>

                    <el-checkbox
                        v-model="enableShort"
                    >
                        空头
                    </el-checkbox>

                    <el-checkbox
                        v-model="dryRun"
                    >
                        Dry Run
                    </el-checkbox>

                </div>

                <div class="button-group">

                    <el-button
                        type="primary"
                        @click="confirmStart"
                    >
                        开始运行
                    </el-button>

                    <el-button
                        type="danger"
                        @click="confirmStop"
                    >
                        停止运行
                    </el-button>

                    <el-button
                        type="success"
                        @click="confirmReload"
                    >
                        加载配置
                    </el-button>

                    <el-button
                        type="warning"
                        @click="confirmDeleteTrade"
                    >
                        删除数据库
                    </el-button>

                </div>

                <el-divider />

                <el-checkbox
                    v-model="stopLongEntry"
                    @change="updateStopEntry"
                >
                    停止多头加仓
                </el-checkbox>

                <br><br>

                <el-checkbox
                    v-model="stopShortEntry"
                    @change="updateStopEntry"
                >
                    停止空头加仓
                </el-checkbox>

                <el-divider />

                <div class="status-panel">

                    <div class="status-item">

                        <span
                            class="status-light"
                            :class="longRunning ? 'running' : 'stopped'"
                        />

                        <span>
                            多头：
                            {{ longRunning ? "运行中" : "已停止" }}
                        </span>

                    </div>

                    <div class="status-item">

                        <span
                            class="status-light"
                            :class="shortRunning ? 'running' : 'stopped'"
                        />

                        <span>
                            空头：
                            {{ shortRunning ? "运行中" : "已停止" }}
                        </span>

                    </div>

                </div>

            </el-card>

        </el-col>

    </el-row>

    <el-row
        :gutter="20"
        style="margin-top:20px"
    >

        <!-- 多头 -->

        <el-col :span="12">

            <el-card>

                <template #header>
                    多头配置
                </template>

                <el-form
                    label-width="120px"
                >

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
                        @click="saveLongConfig"
                    >
                        保存多头配置
                    </el-button>

                </el-form>

            </el-card>

        </el-col>


        <!-- 空头 -->

        <el-col :span="12">

            <el-card>

                <template #header>
                    空头配置
                </template>

                <el-form
                    label-width="120px"
                >

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
                        @click="saveShortConfig"
                    >
                        保存空头配置
                    </el-button>

                </el-form>

            </el-card>

        </el-col>

    </el-row>

</div>

</template>


<script setup>

import axios from "axios"

import {
    ElMessage,
    ElMessageBox
} from "element-plus"

import {
    ref,
    onMounted,
    onUnmounted
} from "vue"

const API =
    "http://localhost:9000"

const enableLong =
    ref(true)

const enableShort =
    ref(true)

const dryRun =
    ref(false)

const stopLongEntry =
    ref(false)

const stopShortEntry =
    ref(false)

const startTime =
    ref("")

const uptime =
    ref("")

let statusTimer = null

const longConfig = ref({})
const shortConfig = ref({})

const longWhitelist = ref("")
const longBlacklist = ref("")

const shortWhitelist = ref("")
const shortBlacklist = ref("")

const longRunning =
    ref(false)

const shortRunning =
    ref(false)

const loadConfig = async () => {

    const res =
        await axios.get(
            `${API}/control/config/all`
        )

    longConfig.value =
        res.data.long

    shortConfig.value =
        res.data.short

    longWhitelist.value =
        res.data.long.pair_whitelist.join("\n")

    longBlacklist.value =
        res.data.long.pair_blacklist.join("\n")

    shortWhitelist.value =
        res.data.short.pair_whitelist.join("\n")

    shortBlacklist.value =
        res.data.short.pair_blacklist.join("\n")
}


const startBot =
    async () => {

        await axios.post(
            `${API}/control/start`,
            {
                long:
                    enableLong.value,

                short:
                    enableShort.value,

                dry_run:
                    dryRun.value
            }
        )
    }


const stopBot =
    async () => {

        await axios.post(
            `${API}/control/stop`
        )
    }


const reloadConfig =
    async () => {

        await axios.post(
            `${API}/control/reload`
        )

        await loadConfig()

        ElMessage.success(
            "配置已重新加载"
        )
    }


const updateStopEntry =
    async () => {

        await axios.post(
            `${API}/control/stopentry`,
            {
                long:
                    stopLongEntry.value,

                short:
                    stopShortEntry.value
            }
        )
    }


const confirmStart = async () => {

    try {

        await ElMessageBox.confirm(
            "确认启动策略？",
            "启动确认",
            {
                type: "success"
            }
        )

        const res =
            await axios.post(
                `${API}/control/start`,
                {
                    long:
                        enableLong.value,

                    short:
                        enableShort.value,

                    dry_run:
                        dryRun.value
                }
            )

        await loadStatus()

        ElMessage.success(
            res.data.mode === "launch"
                ? "Freqtrade已启动"
                : "策略已恢复运行"
        )

    } catch {}
}


const confirmStop = async () => {

    try {

        await ElMessageBox.confirm(
            "确认停止策略？",
            "停止确认",
            {
                type: "warning"
            }
        )

        await axios.post(
            `${API}/control/stop`,
            {
                long: enableLong.value,
                short: enableShort.value
            }
        )

        await loadStatus()

        ElMessage.success(
            "策略已停止"
        )

    } catch {}
}


const confirmReload = async () => {

    try {

        await ElMessageBox.confirm(
            "确认重新加载配置？",
            "加载配置",
            {
                type: "info"
            }
        )

        await reloadConfig()

    } catch {}
}


const confirmDeleteTrade = async () => {

    try {

        await ElMessageBox.confirm(
            "将删除全部交易记录并停止策略，是否继续？",
            "危险操作",
            {
                type: "error"
            }
        )

        await axios.post(
            `${API}/control/delete_trade`
        )

        ElMessage.success(
            "交易记录已清空"
        )

    } catch {}
}


const loadStatus =
async () => {

    const res =
        await axios.get(
            `${API}/control/status`
        )

    longRunning.value =
        res.data.long

    shortRunning.value =
        res.data.short
}


const saveLongConfig =
async () => {

    try {

        await axios.post(
            `${API}/control/config`,
            {
                side: "long",

                ...longConfig.value,

                pair_whitelist:
                    longWhitelist.value
                        .split("\n")
                        .filter(Boolean),

                pair_blacklist:
                    longBlacklist.value
                        .split("\n")
                        .filter(Boolean)
            }
        )

        ElMessage.success(
            "多头配置已保存"
        )

    } catch {

        ElMessage.error(
            "多头保存失败"
        )
    }
}


const saveShortConfig =
async () => {

    try {

        await axios.post(
            `${API}/control/config`,
            {
                side: "short",

                ...shortConfig.value,

                pair_whitelist:
                    shortWhitelist.value
                        .split("\n")
                        .filter(Boolean),

                pair_blacklist:
                    shortBlacklist.value
                        .split("\n")
                        .filter(Boolean)
            }
        )

        ElMessage.success(
            "空头配置已保存"
        )

    } catch {

        ElMessage.error(
            "空头保存失败"
        )
    }
}


onMounted(
    async () => {

        await loadStatus()

        await loadConfig()

        statusTimer = setInterval(
            loadStatus,
            5000
        )
    }
)


onUnmounted(() => {

    if (statusTimer) {

        clearInterval(
            statusTimer
        )
    }
})


</script>


<style scoped>

.checkbox-group{

    display:flex;
    gap:20px;

    margin-bottom:20px;
}

.button-group{

    display:flex;
    gap:10px;
}

.status-panel{

    display:flex;
    flex-direction:column;
    gap:12px;
}

.status-item{

    display:flex;
    align-items:center;
    gap:10px;

    font-size:15px;
}

.status-light{

    width:14px;
    height:14px;

    border-radius:50%;
}

.running{

    background:#67c23a;

    box-shadow:
        0 0 6px #67c23a,
        0 0 12px #67c23a;
}

.stopped{

    background:#f56c6c;

    box-shadow:
        0 0 6px #f56c6c;
}

</style>