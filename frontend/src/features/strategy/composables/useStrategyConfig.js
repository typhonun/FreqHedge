import axios from "axios"
import {ref, computed} from "vue"
import merge from "lodash.merge"

const API = "http://localhost:9000"

const roiLevels = [
    { minutes: 1440, roi: 0 },
    { minutes: 720, roi: 2 },
    { minutes: 480, roi: 4 },
    { minutes: 360, roi: 6 },
    { minutes: 300, roi: 8 },
    { minutes: 240, roi: 10 },
    { minutes: 210, roi: 12 },
    { minutes: 180, roi: 14 },
    { minutes: 150, roi: 16 },
    { minutes: 120, roi: 18 },
    { minutes: 100, roi: 20 },
    { minutes: 80, roi: 22 },
    { minutes: 60, roi: 24 },
    { minutes: 40, roi: 26 },
    { minutes: 20, roi: 28 },
    { minutes: 0, roi: 30 }
]

const buildTradeInfo = (side, config) => {

    const isLong = side === "long"

    const roiLevels = config.tp?.enable
        ? config.tp.roi_levels || []
        : []


    return {

        side,

        direction: isLong
            ? "仅做多"
            : "仅做空",


        timeframe:
            config.timeframe || "30m",


        leverage:
            `${config.leverage || 10}x`,


        stoploss:
            config.sl?.enable
                ? `${config.sl.stoploss}%`
                : null,



        // 开仓逻辑
        entrySignal: (()=>{

            const signals=[]


            // Bollinger
            if(config.entry?.bb?.enable){

                signals.push(
                    "Bollinger"
                )

            }


            // RSI
            if(config.entry?.rsi?.enable){

                signals.push(

                    isLong

                    ?
                    `RSI < ${config.entry.rsi.value}`

                    :
                    `RSI > ${config.entry.rsi.value}`

                )

            }


            // MACD
            if(config.entry?.macd?.enable){

                signals.push(
                    "MACD"
                )

            }


            return signals.length
                ?
                signals.join(" + ")
                :
                null


        })(),



        // TP减仓
        tpSignal:

            config.tp?.enable

                ?

                `减仓仓位大小 ${config.tp.reduce_percent}%，加仓总资金 ${config.tp.target_wallet_percent}%`

                :

                null,


        // 浮亏止盈
        lossTpSignal:(()=>{

            if(!config.loss_tp?.enable){
                return null
            }


            return `
            目标仓位 ${config.loss_tp.target_wallet_percent}%,
            反弹止盈 ${config.loss_tp.dca_tp_profit}%
            `


        })(),



        trendSignal:(()=>{

            if(!config.trend_add?.enable){
                return null
            }


            const list=[]


            if(config.trend_add.macd_enable){
                list.push("MACD")
            }

            if(config.trend_add.kdj_enable){
                list.push("KDJ")
            }

            if(config.trend_add.ema_enable){
                list.push("EMA")
            }


            return list.length
                ?
                list.join(" + ")
                :
                null


        })(),




        dcaSignal: (() => {
            if (!config.dca?.enable) return null

            const d = config.dca
            const mode = d.amount_mode || "auto"

            if (mode === "auto") {
                return `最多 ${d.max_count} 次，自动模式 基础 ${d.base_percent}% × ${d.amount_multiplier}^n，
                价格下跌步骤 ${d.price_offset}%，价格偏差 ${d.price_multiplier}`
            }

            return `最多 ${d.max_count} 次，手动分层 ${d.levels?.length || 0} 层，价格下跌步骤 ${d.price_offset}%，价格偏差 ${d.price_multiplier}`
        })(),


        gridSignal:

            config.grid?.enable

                ?

                `网格下沿 ${config.grid.grid_lower}% 加仓总资金 ${config.grid.buy_percent}%，
                 网格上沿 ${config.grid.grid_upper}%，减仓总资金 ${config.grid.sell_percent}%
                 订单规模 ${config.grid.order_scale}`

                :

                null,




        roiLevels:

            roiLevels.map(level=>({

                label:
                    `${level.minutes}m / ${level.roi}%`

            }))


    }
}

export function useStrategyConfig() {

const defaultLongConfig = () => ({
    side: "long",

    timeframe:"30m",

    entry:{

        rsi:{
            enable:true,

            // RSI入场阈值
            value:35
        },


        macd:{
            enable:true
        },


        bb:{
            enable:true
        }

    },

    tp: {
        enable: true,
        roi_levels: roiLevels.map((level) => ({
            minutes: level.minutes,
            roi: level.roi
        })),
        reduce_percent: 30,
        rebuy_enable: true,
        target_wallet_percent: 5
    },

    sl: {
        enable: true,
        stoploss: -9
    },

    indicator:{


        rsi:{
            period:14
        },


        bb:{
            period:20,
            std:2
        },


        macd:{
            fast:12,
            slow:26,
            signal:9
        },


        kdj:{
            fastk:5,
            slowk:3,
            slowd:3
        },


        ema:{
            fast:9,
            mid:21,
            slow:99
        }

    },

    trend_add:{

        enable:false,

        amount_percent:0.5,

        condition:"and",


        macd_enable:true,

        kdj_enable:true,

        ema_enable:true,


        kdj_reduce:{
            enable:false,
            reduce_percent:50
        }

    },

    dca: {
        enable: true,
        max_count: 7,
        condition: "or",
        cooldown_minutes: 60,

        // 新增：金额模式，"auto" 或 "manual"
        amount_mode: "auto",

        // 自动模式用
        base_percent: 2,
        amount_multiplier: 1.5,

        // 价格触发
        price_offset: 1.0,
        price_multiplier: 1.5,

        // 手动模式用
        levels: [
            {
                amount: 100,
                rsi_limit: 25,
                j_limit: 10
            }
        ]
    },
    loss_tp:{
        enable:true,
        dca_tp_profit:3,
        target_wallet_percent:5
    },
    grid: {
        enable: true,
        max_count: 5,
        grid_lower: -2,
        grid_upper: 2,
        buy_percent: 2,
        sell_percent: 2,
        order_scale: 1,
        cooldown_minutes: 30
    }
})


const defaultShortConfig = () => ({
    side: "short",

    entry:{

        rsi:{
            enable:true,

            // RSI入场阈值
            value:65
        },


        macd:{
            enable:true
        },


        bb:{
            enable:true
        }

    },

    tp: {
        enable: true,
        roi_levels: roiLevels.map((level) => ({
            minutes: level.minutes,
            roi: level.roi
        })),
        reduce_percent: 30,
        rebuy_enable: true,
        target_wallet_percent: 5
    },

    sl: {
        enable: true,
        stoploss: -9
    },

    indicator:{


        rsi:{
            period:14
        },


        bb:{
            period:20,
            std:2
        },


        macd:{
            fast:12,
            slow:26,
            signal:9
        },


        kdj:{
            fastk:5,
            slowk:3,
            slowd:3
        },


        ema:{
            fast:9,
            mid:21,
            slow:99
        }

    },


    trend_add:{

        enable:false,

        amount_percent:0.5,

        condition:"and",


        macd_enable:true,

        kdj_enable:true,

        ema_enable:true,


        kdj_reduce:{
            enable:false,
            reduce_percent:50
        }

    },

    dca: {
        enable: true,
        max_count: 7,
        condition: "or",
        cooldown_minutes: 60,

        // 新增：金额模式，"auto" 或 "manual"
        amount_mode: "auto",

        // 自动模式用
        base_percent: 2,
        amount_multiplier: 1.5,

        // 价格触发
        price_offset: 1.0,
        price_multiplier: 1.5,

        // 手动模式用
        levels: [
            {
                amount: 100,
                rsi_limit: 25,
                j_limit: 10
            }
        ]
    },
    loss_tp:{
        enable:true,

        trigger_loss:-10,

        trigger_rebound:1,

        dca_tp_profit:3,

        target_wallet_percent:5
    },

    grid: {
        enable: true,
        max_count: 5,
        grid_lower: -2,
        grid_upper: 2,
        buy_percent: 2,
        sell_percent: 2,
        order_scale: 1,
        cooldown_minutes: 30
    }
})

const longConfig = ref(
    defaultLongConfig()
)

const shortConfig = ref(
    defaultShortConfig()
)


// 保存后的配置快照
const savedLongConfig = ref(
    JSON.parse(
        JSON.stringify(longConfig.value)
    )
)

const savedShortConfig = ref(
    JSON.parse(
        JSON.stringify(shortConfig.value)
    )
)



const longTradeInfo = computed(()=>{

    return buildTradeInfo(
        "long",
        savedLongConfig.value
    )

})


const shortTradeInfo = computed(()=>{

    return buildTradeInfo(
        "short",
        savedShortConfig.value
    )

})

const normalizeDca = (config) => {
    if (!config || !config.dca) return config

    if (!config.dca.amount_mode) {
        config.dca.amount_mode = "auto"
    }

    if (config.dca.base_percent == null) {
        config.dca.base_percent = 2
    }

    if (!config.dca.amount_multiplier) {
        config.dca.amount_multiplier = 1.5
    }

    return config
}

const loadConfig = async () => {

    const res = await axios.get(`${API}/strategy`)

    longConfig.value = normalizeDca(
        merge(defaultLongConfig(), res.data.long)
    )

    shortConfig.value = normalizeDca(
        merge(defaultShortConfig(), res.data.short)
    )

    savedLongConfig.value = JSON.parse(
        JSON.stringify(longConfig.value)
    )

    savedShortConfig.value = JSON.parse(
        JSON.stringify(shortConfig.value)
    )
}

    const saveConfig = async(
        side,
        config
    )=>{


        if(
            !config.entry.rsi.enable &&
            !config.entry.macd.enable &&
            !config.entry.bb.enable
        ){

            ElMessage.error(
                "开仓信号不能为空"
            )

            return
        }



        const res = await axios.post(
            `${API}/strategy`,
            {
                side,
                config
            }
        )


        // 保存成功后更新概览

        if(side==="long"){

            savedLongConfig.value =
                JSON.parse(
                    JSON.stringify(config)
                )

        }


        if(side==="short"){

            savedShortConfig.value =
                JSON.parse(
                    JSON.stringify(config)
                )

        }


        return res

    }

    return {

        longConfig,
        shortConfig,

        savedLongConfig,
        savedShortConfig,

        longTradeInfo,
        shortTradeInfo,

        loadConfig,
        saveConfig
    }
}