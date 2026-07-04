import axios from "axios"
import { ref } from "vue"
import { ElMessage, ElMessageBox } from "element-plus"

const API = "http://localhost:9000"

export function useRunControl() {

    const enableLong = ref(true)
    const enableShort = ref(true)
    const dryRun = ref(false)

    const reload = () =>
        post("/control/reload")

    const deleteTrade = () =>
        post("/control/delete_trade")

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
        await post("/control/stopentry", {
            long: stopLongEntry.value,
            short: stopShortEntry.value
        })
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
                "将删除全部交易记录并停止策略，是否继续？",
                "危险操作"
            )

            await deleteTrade()

            ElMessage.success(
                "交易记录已清空"
            )

        }catch{}
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
        confirmDeleteTrade,

        updateStopEntry
    }
}