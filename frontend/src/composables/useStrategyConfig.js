import axios from "axios"
import { ref } from "vue"

const API = "http://localhost:9000"

export function useStrategyConfig() {

const defaultConfig = () => ({
    entry:{
        rsi:{
            enable:true,
            period:14,
            value:30
        },
        macd:{
            enable:true,
            fast:12,
            slow:26,
            signal:9
        },
        bb:{
            enable:false,
            period:20,
            std:2
        },
        volume:{
            enable:true
        }
    },

    tp:{
        enable:true,
        levels:[]
    },

    sl:{
        enable:true,
        stoploss:-15
    },

    dca:{
        enable:true,
        max_count:8,
        levels:[]
    },

    grid:{
        enable:false,
        count:10,
        distance:1.5
    }
})

const longConfig = ref(defaultConfig())
const shortConfig = ref(defaultConfig())

    const loadConfig = async () => {

        const res =
            await axios.get(
                `${API}/strategy`
            )

        longConfig.value =
            res.data.long

        shortConfig.value =
            res.data.short
    }

    const saveConfig = async (
        side,
        config
    ) => {

        return axios.post(
            `${API}/strategy`,
            {
                side,
                config
            }
        )
    }

    return {

        longConfig,
        shortConfig,

        loadConfig,
        saveConfig
    }
}