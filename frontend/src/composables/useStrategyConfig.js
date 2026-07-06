import axios from "axios"
import { ref } from "vue"
import merge from "lodash.merge"

const API = "http://localhost:9000"

export function useStrategyConfig() {

const defaultLongConfig = () => ({
    side: "long",

    entry: {
        rsi: {
            enable: true,
            period: 14,
            value: 30
        },

        macd: {
            enable: true,
            fast: 12,
            slow: 26,
            signal: 9
        },

        bb: {
            enable: false,
            period: 20,
            std: 2
        },

        volume: {
            enable: true
        }
    },

    tp: {
        enable: true,
        roi_levels: [
            { minutes: 0, roi: 3 },
            { minutes: 60, roi: 2 },
            { minutes: 240, roi: 1 }
        ],
        reduce_percent: 30,
        rebuy_enable: true,
        target_wallet_percent: 5
    },

    sl: {
        enable: true,
        stoploss: -15
    },

    trend_add: {
        enable: true,
        max_count: 3,

        levels: [
            {
                profit: 2,
                rsi: 60,
                amount: 0.5
            },
            {
                profit: 4,
                rsi: 65,
                amount: 0.8
            }
        ]
    },

    dca: {
        enable: true,
        max_count: 8,
        condition: "or",

        levels: [
            {
                drawdown: -3,
                rsi_limit: 25,
                j_limit: 10,
                amount: 1
            },
            {
                drawdown: -6,
                rsi_limit: 20,
                j_limit: 0,
                amount: 1.5
            }
        ]
    },
    loss_tp: {
        enable: true,
        target_wallet_percent: 5
    },
    grid: {
        enable: true,
        upper_percent: 2,
        lower_percent: 2,
        buy_percent: 2,
        sell_percent: 2,
        cooldown_minutes: 30
    }
})


const defaultShortConfig = () => ({
    side: "short",

    entry: {
        rsi: {
            enable: true,
            period: 14,
            value: 80
        },

        macd: {
            enable: true,
            fast: 12,
            slow: 26,
            signal: 9
        },

        bb: {
            enable: false,
            period: 20,
            std: 2
        },

        volume: {
            enable: true
        }
    },

    tp: {
        enable: true,
        roi_levels: [
            { minutes: 0, roi: 3 },
            { minutes: 60, roi: 2 },
            { minutes: 240, roi: 1 }
        ],
        reduce_percent: 30,
        rebuy_enable: true,
        target_wallet_percent: 5
    },

    sl: {
        enable: true,
        stoploss: -15
    },

    trend_add: {
        enable: true,
        max_count: 3,

        levels: [
            {
                profit: 2,
                rsi: 40,
                amount: 0.5
            },
            {
                profit: 4,
                rsi: 35,
                amount: 0.8
            }
        ]
    },

    dca: {
        enable: true,
        max_count: 8,
        condition: "or",
        dca_pct: 1.0,
        cooldown_minutes: 60,
        levels: [
            {
                drawdown: -3,
                rsi_limit: 75,
                j_limit: 90,
                amount: 1
            },
            {
                drawdown: -6,
                rsi_limit: 80,
                j_limit: 100,
                amount: 1.5
            }
        ]
    },
    loss_tp: {
        enable: true,
        target_wallet_percent: 5
    },

    grid: {
        enable: true,
        upper_percent: 2,
        lower_percent: 2,
        buy_percent: 2,
        sell_percent: 2,
        cooldown_minutes: 30
    }
})

const longConfig = ref(defaultLongConfig())
const shortConfig = ref(defaultShortConfig())

    const loadConfig = async () => {

        const res =
            await axios.get(
                `${API}/strategy`
            )

        longConfig.value = merge(
            defaultLongConfig(),
            res.data.long
        )

        shortConfig.value = merge(
            defaultShortConfig(),
            res.data.short
        )
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