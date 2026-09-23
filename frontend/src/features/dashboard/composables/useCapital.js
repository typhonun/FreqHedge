import axios from "axios"
import { ref } from "vue"

const API = "http://localhost:9000"

export function useCapital() {

    const longConfig = ref({})
    const shortConfig = ref({})

    const longWhitelist = ref("")
    const longBlacklist = ref("")

    const shortWhitelist = ref("")
    const shortBlacklist = ref("")

    const loadConfig = async () => {
        const res = await axios.get(`${API}/control/config`)

        const longData = res.data.long || {}
        const shortData = res.data.short || {}

        longConfig.value = {
            leverage: 10,
            // 多头失衡控制默认值
            imbalance_long_enable: false,
            imbalance_long_count: 2,
            ...longData
        }

        shortConfig.value = {
            leverage: 10,
            // 空头失衡控制默认值
            imbalance_short_enable: false,
            imbalance_short_count: 2,
            ...shortData
        }

        longWhitelist.value = (longData.pair_whitelist || []).join("\n")
        longBlacklist.value = (longData.pair_blacklist || []).join("\n")

        shortWhitelist.value = (shortData.pair_whitelist || []).join("\n")
        shortBlacklist.value = (shortData.pair_blacklist || []).join("\n")
    }

    const saveConfig = async (side) => {
        const isLong = side === "long"

        const payload = {
            side,
            ...(isLong ? longConfig.value : shortConfig.value),

            pair_whitelist: (isLong ? longWhitelist.value : shortWhitelist.value)
                .split("\n").filter(Boolean),

            pair_blacklist: (isLong ? longBlacklist.value : shortBlacklist.value)
                .split("\n").filter(Boolean)
        }

        return axios.post(`${API}/control/config`, payload)
    }

    return {
        longConfig,
        shortConfig,
        longWhitelist,
        longBlacklist,
        shortWhitelist,
        shortBlacklist,
        loadConfig,
        saveConfig
    }
}