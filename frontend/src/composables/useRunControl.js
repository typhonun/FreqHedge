import axios from "axios"
import { ref } from "vue"
import { ElMessage, ElMessageBox } from "element-plus"

const API = "http://localhost:9000"

export function useRunControl() {

    const enableLong = ref(true)
    const enableShort = ref(true)
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

    const confirmStart = async () => {
        try {
            await ElMessageBox.confirm("确认启动策略？", "启动确认")

            await post("/control/start", {
                long: enableLong.value,
                short: enableShort.value,
                dry_run: dryRun.value
            })

            ElMessage.success("已启动")
        } catch {}
    }

    const confirmStop = async () => {
        try {
            await ElMessageBox.confirm("确认停止策略？", "停止确认")

            await post("/control/stop", {
                long: enableLong.value,
                short: enableShort.value
            })

            ElMessage.success("已停止")
        } catch {}
    }

    const updateStopEntry = async () => {

        try {

            await post(
                "/control/stopentry",
                {
                    long: stopLongEntry.value,
                    short: stopShortEntry.value
                }
            )

            await loadStopEntryStatus()

            ElMessage.success(
                "状态已更新"
            )

        } catch (e) {

            await loadStopEntryStatus()

            ElMessage.error(
                "更新失败"
            )
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
    }

    const saveRiskConfig = async () => {

        await axios.post(
            `${API}/control/risk-config`,
            {

                global_tp_enabled:
                    globalTpEnabled.value,

                global_sl_enabled:
                    globalSlEnabled.value,
                global_tp_amount:
                    globalTpAmount.value,

                global_sl_amount:
                    globalSlAmount.value
            }
        )

        ElMessage.success(
            "已保存"
        )
    }

    return {

        enableLong,
        enableShort,
        dryRun,

        stopLongEntry,
        stopShortEntry,

        confirmStart,
        confirmStop,
        confirmReload,

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

        loadRiskConfig,
        saveRiskConfig
    }

}