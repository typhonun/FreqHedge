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

        longConfig.value = res.data.long
        shortConfig.value = res.data.short

        longWhitelist.value = res.data.long.pair_whitelist.join("\n")
        longBlacklist.value = res.data.long.pair_blacklist.join("\n")

        shortWhitelist.value = res.data.short.pair_whitelist.join("\n")
        shortBlacklist.value = res.data.short.pair_blacklist.join("\n")
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