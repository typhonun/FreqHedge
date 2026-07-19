import axios from "axios"
import { ref } from "vue"
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

const buildTradeInfo = (side) => {
    const isLong = side === "long"

    return {
        side,
        label: isLong ? "多头" : "空头",
        direction: isLong ? "仅做多" : "仅做空",
        timeframe: "30m",
        leverage: "10x",
        stoploss: "-9%",
        exitSignal: "关闭",
        trailingStop: "关闭",
        positionAdjustment: "开启",
        entrySignal: isLong
            ? "收盘价跌破布林下轨且 RSI < 35"
            : "收盘价突破布林上轨且 RSI > 65",
        trendSignal: isLong
            ? "MACD > Signal 且 K > D，ADX > 25，EMA9 > EMA21 > EMA99"
            : "MACD < Signal 且 K < D，ADX > 25，EMA9 < EMA21 < EMA99",
        dcaSignal: isLong
            ? "按 DCA 表格逐层触发（低位回撤 + RSI/J 条件，最多 7 次，冷却 60 分钟）"
            : "按 DCA 表格逐层触发（高位回撤 + RSI/J 条件，最多 7 次，冷却 60 分钟）",
        tpSignal: "达到阶梯 ROI 后分批止盈，随后回补至 5% 目标仓位",
        gridSignal: isLong
            ? "跌破网格下沿补仓，突破网格上沿减仓"
            : "突破网格上沿补仓，跌破网格下沿减仓",
        notes: [
            "主开仓仅使用 BB + RSI + Volume；MACD / KDJ / ADX / EMA 主要用于趋势加仓。",
            "趋势加仓、ROI、止损、TP 回补、DCA 和网格阈值都会同步到后端 JSON 配置。",
            "Loss TP 会在触发亏损后等待反弹再减仓。"
        ],
        roiLevels: roiLevels.map((level) => ({
            minutes: level.minutes,
            roi: `${level.roi}%`,
            label: `${level.minutes}m / ${level.roi}%`
        }))
    }
}

export function useStrategyConfig() {

const defaultLongConfig = () => ({
    side: "long",

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

        max_count:3,

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

        enable:true,

        max_count:7,

        condition:"or",

        cooldown_minutes:60,


        // 第一次DCA价格距离均价
        price_offset:1.0,


        // 每层价格偏差倍率
        price_multiplier:1.5,


        // 每层订单金额倍率
        amount_multiplier:1.5,


        levels:[
            {
                amount:100,
                rsi_limit:25,
                j_limit:10
            }
        ]
    },
    loss_tp: {
        enable: true,
        trigger_loss: -10,
        trigger_rebound: 2,
        target_wallet_percent: 5
    },
    grid: {
        enable: true,
        grid_lower: -2,
        grid_upper: 2,
        buy_percent: 2,
        sell_percent: 2,
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

        max_count:3,

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

        enable:true,

        max_count:7,

        condition:"or",

        cooldown_minutes:60,


        // 第一次DCA价格距离均价
        price_offset:1.0,


        // 每层价格偏差倍率
        price_multiplier:1.5,


        // 每层订单金额倍率
        amount_multiplier:1.5,


        levels:[
            {
                amount:100,
                rsi_limit:25,
                j_limit:10
            }
        ]
    },
    loss_tp: {
        enable: true,
        trigger_loss: -10,
        trigger_rebound: 2,
        target_wallet_percent: 5
    },

    grid: {
        enable: true,
        grid_lower: -2,
        grid_upper: 2,
        buy_percent: 2,
        sell_percent: 2,
        cooldown_minutes: 30
    }
})

const longConfig = ref(defaultLongConfig())
const shortConfig = ref(defaultShortConfig())
const longTradeInfo = buildTradeInfo("long")
const shortTradeInfo = buildTradeInfo("short")

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
        longTradeInfo,
        shortTradeInfo,

        loadConfig,
        saveConfig
    }
}