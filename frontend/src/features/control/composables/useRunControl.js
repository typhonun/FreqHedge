import axios from "axios"
import { ref } from "vue"
import { ElMessage, ElMessageBox } from "element-plus"

const API = "http://localhost:9000"

export function useRunControl() {

    const dryRun = ref(false)

    const forceEnterVisible = ref(false)

    const pairList = ref([])

    const selectedPair = ref("")

    const stakeAmount = ref(20)

    const forceSide = ref("long")

    const globalTpEnabled = ref(false)
    const globalSlEnabled = ref(false)

    const globalTpAmount = ref(0)
    const globalSlAmount = ref(0)

    const globalTpMode = ref("amount")
    const globalSlMode = ref("amount")
    const globalTpRatio = ref(0)
    const globalSlRatio = ref(0)

    const globalTrailEnabled = ref(false)
    const globalTrailMode = ref("ratio")

    const globalTrailActivateAmount = ref(10)
    const globalTrailActivateRatio = ref(1)

    const globalTrailDrawdownAmount = ref(5)
    const globalTrailDrawdownRatio = ref(0.5)

    const configCache = ref({
        longStake: 20,
        shortStake: 20
    })

    const reload = () =>
        post("/control/reload")

    const deleteTrade = async () => {

        return await post(
            "/control/delete_trade"
        )

    }

    const stopLongEntry = ref(false)
    const stopShortEntry = ref(false)

    const post = (url, data = {}) =>
        axios.post(`${API}${url}`, data)

    // ========== 多空运行状态 ==========
    const longRunning = ref(false)
    const shortRunning = ref(false)

    // 从后端拉真实状态
    const loadRunningStatus = async () => {
        try {
            const { data } = await axios.get(`${API}/control/status`)
            longRunning.value = data.long === "RUNNING"
            shortRunning.value = data.short === "RUNNING"
        } catch (e) {
            console.error("loadRunningStatus failed:", e)
        }
    }

    // 单 side 启停
    const toggleSide = async (side) => {
        const isLong = side === "long"
        const runningRef = isLong ? longRunning : shortRunning

        const nextRunning = !runningRef.value
        const actionName = nextRunning ? "启动" : "停止"
        const sideName = isLong ? "多头" : "空头"

        try {
            await ElMessageBox.confirm(
                `确认${actionName}${sideName}交易？`,
                `${actionName}确认`
            )
        } catch {
            return  // 用户取消
        }

        try {
            if (nextRunning) {
                // 只启动这一侧；另一侧保持原状
                const otherRunning = isLong
                    ? shortRunning.value
                    : longRunning.value

                await post("/control/start", {
                    long: isLong ? true : otherRunning,
                    short: isLong ? otherRunning : true,
                    dry_run: dryRun.value
                })
            } else {
                await post("/control/stop", {
                    long: isLong,
                    short: !isLong
                })
            }

            // 重新从后端同步（比本地猜测更可靠）
            await loadRunningStatus()

            ElMessage.success(`${sideName}已${actionName}`)
        } catch (e) {
            ElMessage.error(`${sideName}${actionName}失败`)
            await loadRunningStatus()
        }
    }

    const stopEntryLoading = ref(false)

    const updateStopEntry = async () => {

        if (stopEntryLoading.value) {
            return
        }

        stopEntryLoading.value = true

        try {

            const { data } = await post(
                "/control/stopentry",
                {
                    long: stopLongEntry.value,
                    short: stopShortEntry.value
                }
            )

            if (!data.success) {

                ElMessage.error(
                    data.error || "更新失败"
                )

                await loadStopEntryStatus()

                return
            }

            stopLongEntry.value = data.long
            stopShortEntry.value = data.short

        } catch (e) {

            ElMessage.error("更新失败")

            await loadStopEntryStatus()

        } finally {

            stopEntryLoading.value = false
        }
    }

    const confirmReload = async () => {

        try{

            await ElMessageBox.confirm(
                "确认重新加载配置？",
                "加载配置"
            )

            await reload()

            ElMessage.success(
                "配置已重新加载"
            )

        }catch{}
    }

    const confirmDeleteTrade = async () => {

        try{

            await ElMessageBox.confirm(
                "删除数据库会清空全部交易记录，是否继续？",
                "危险操作",
                {
                    confirmButtonText:"确认删除",
                    cancelButtonText:"取消",
                    type:"warning"
                }
            )


            ElMessage.info(
                "正在删除数据库，请稍候..."
            )


            const res = await axios.post(
                `${API}/control/delete_trade`
            )


            console.log(
                "DELETE RESULT:",
                res.data
            )


            if(res.data.success){

                ElMessage.success({
                    message:
                        res.data.message ||
                        "已成功删除数据库",
                    duration:3000
                })

            }
            else{

                ElMessage.warning({
                    message:
                        res.data.error ||
                        "删除失败",
                    duration:3000
                })

            }


        }
        catch(e){


            if(e !== "cancel"){

                console.error(
                    "DELETE ERROR:",
                    e
                )


                ElMessage.error({
                    message:
                        "删除失败",
                    duration:3000
                })

            }

        }
    }

    const openForceEnter = async (side) => {

        forceSide.value = side

        // 读取配置
        const configRes = await axios.get(
            `${API}/control/config`
        )

        if (side === "long") {

            stakeAmount.value =
                configRes.data.long.stake_amount

        } else {

            stakeAmount.value =
                configRes.data.short.stake_amount
        }

        const { data } = await axios.get(
            `${API}/control/available_pairs/${side}`
        )

        pairList.value = data

        selectedPair.value = ""

        forceEnterVisible.value = true
    }

    const submitForceEnter = async () => {

        if (!selectedPair.value) {

            ElMessage.warning(
                "请选择交易对"
            )

            return
        }

        // 判断是否已停止加仓
        if (
            forceSide.value === "long"
            && stopLongEntry.value
        ) {
            ElMessage.warning(
                "多头加仓已停止，请先恢复加仓后再开仓"
            )
            return
        }

        if (
            forceSide.value === "short"
            && stopShortEntry.value
        ) {
            ElMessage.warning(
                "空头加仓已停止，请先恢复加仓后再开仓"
            )
            return
        }

        await axios.post(
            `${API}/control/force_enter`,
            {
                side: forceSide.value,
                pair: selectedPair.value,
                stakeamount: stakeAmount.value
            }
        )

        ElMessage.success("开仓成功")

        forceEnterVisible.value = false
    }


    const loadStopEntryStatus = async () => {

        try {

            const { data } =
                await axios.get(
                    `${API}/control/stopentry`
                )

            stopLongEntry.value =
                data.long

            stopShortEntry.value =
                data.short

        } catch (e) {

            console.error(e)
        }
    }

    const confirmCloseAll = async(side)=>{


        const name =
            side === "long"
            ? "多头"
            : "空头"


        try{


            await ElMessageBox.confirm(

                `是否平仓${name}全部仓位？`,

                "确认平仓",

                {
                    confirmButtonText:"确认",
                    cancelButtonText:"取消",
                    type:"warning"
                }

            )


            const res = await axios.post(

                `${API}/control/close_all`,

                {
                    side:side
                }

            )


            if(res.data.success){

                if(res.data.closed_count > 0){

                    const msg =
                        `${name}已全部平仓，共${res.data.closed_count}个仓位`

                    ElMessage.success(msg)

                    systemNotify(msg)

                }
                else{

                    ElMessage.info(
                        `${name}当前没有持仓`
                    )

                }

            }
            else{

                ElMessage.error(
                    "平仓失败"
                )

            }



        }
        catch(e){


            if(e !== "cancel"){

                console.error(e)

                ElMessage.error(
                    "请求失败"
                )

            }

        }


    }

    const loadRiskConfig = async () => {

        const { data } =
            await axios.get(
                `${API}/control/risk-config`
            )

        globalTpEnabled.value =
            data.global_tp_enabled

        globalSlEnabled.value =
            data.global_sl_enabled

        globalTpAmount.value =
            data.global_tp_amount

        globalSlAmount.value =
            data.global_sl_amount

        globalTpMode.value =
            data.global_tp_mode || "amount"

        globalSlMode.value =
            data.global_sl_mode || "amount"

        globalTpRatio.value =
            Number(data.global_tp_ratio || 0)

        globalSlRatio.value =
            Number(data.global_sl_ratio || 0)

        globalTrailEnabled.value =
            data.global_trail_enabled || false

        globalTrailMode.value =
            data.global_trail_mode || "ratio"

        globalTrailActivateAmount.value =
            Number(data.global_trail_activate_amount || 0)

        globalTrailActivateRatio.value =
            Number(data.global_trail_activate_ratio || 0)

        globalTrailDrawdownAmount.value =
            Number(data.global_trail_drawdown_amount || 0)

        globalTrailDrawdownRatio.value =
            Number(data.global_trail_drawdown_ratio || 0)
    }

    const saveRiskConfig = async () => {
        await axios.post(
            `${API}/control/risk-config`,
            {
                global_tp_enabled: globalTpEnabled.value,
                global_tp_amount: globalTpAmount.value,
                global_tp_mode: globalTpMode.value,
                global_tp_ratio: globalTpRatio.value,

                global_sl_enabled: globalSlEnabled.value,
                global_sl_amount: globalSlAmount.value,
                global_sl_mode: globalSlMode.value,
                global_sl_ratio: globalSlRatio.value,

                global_trail_enabled: globalTrailEnabled.value,
                global_trail_mode: globalTrailMode.value,

                global_trail_activate_amount: globalTrailActivateAmount.value,
                global_trail_activate_ratio: globalTrailActivateRatio.value,

                global_trail_drawdown_amount: globalTrailDrawdownAmount.value,
                global_trail_drawdown_ratio: globalTrailDrawdownRatio.value,
            }
        )

        ElMessage.success("已保存")
    }

    return {

        dryRun,

        longRunning,
        shortRunning,
        toggleSide,
        loadRunningStatus,

        stopLongEntry,
        stopShortEntry,

        confirmCloseAll,

        confirmDeleteTrade,

        updateStopEntry,

        forceEnterVisible,
        pairList,
        selectedPair,
        stakeAmount,

        openForceEnter,
        submitForceEnter,
        loadStopEntryStatus,
        
        globalTpEnabled,
        globalSlEnabled,

        globalTpAmount,
        globalSlAmount,

        globalTpMode,
        globalSlMode,
        globalTpRatio,
        globalSlRatio,

        globalTrailEnabled,
        globalTrailMode,
        globalTrailActivateAmount,
        globalTrailActivateRatio,
        globalTrailDrawdownAmount,
        globalTrailDrawdownRatio,

        loadRiskConfig,
        saveRiskConfig
    }

}